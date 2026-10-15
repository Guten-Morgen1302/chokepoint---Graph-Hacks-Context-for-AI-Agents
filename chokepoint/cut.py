"""Cut engine: attack subgraph, min-cost revocation cut, counterfactuals, proof.

    finding ──algo.bfs──▶ node set ──induced ATTACK edges──▶ Sub
      │
      ├─ plan_cut : algo.maxFlow(cap)  → residual cut (src + sink side) → Plan P0
      ├─ routes   : algo.maxFlow(unit) → independent routes (Menger)     (SD-1)
      ├─ what_if  : [lock] clear cf → write cf on ALL edges → maxFlow(cf) → clear [unlock]
      └─ verify   : same, with the plan's grants at 0 and everything else BIG;
                    maxFlow == 0  ⇔  every route is severed

FalkorDB returns flows but not the cut set, so the cut is derived from the
residual graph here and checked against maxFlow (cut capacity == maxFlow).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from . import BIG
from . import queries as Q
from .graphdb import GraphUnavailable, TenantCtx, clear_cf_dirty, cf_dirty, mark_cf_dirty

EPS = 1e-6


class CutAssertionError(Exception):
    """cut capacity != maxFlow: never shown to a user as a plan."""


class SeveranceError(Exception):
    def __init__(self, plan_id: str, remaining: float):
        super().__init__(f"plan {plan_id} does not sever: maxFlow = {remaining:g}")
        self.plan_id, self.remaining = plan_id, remaining


class FindingNotFound(Exception):
    pass


# ── data ─────────────────────────────────────────────────────────────────────

@dataclass
class Sub:
    finding: str
    source: int
    nodes: dict[int, dict]
    edges: list[tuple[int, int, int, str, float, float]]  # (u, v, eid, kind, cap, unit)
    jewels: list[int]

    def grant_of_edge(self, u: int, v: int, kind: str) -> str | None:
        if kind == "holds" and self.nodes.get(v, {}).get("label") == "Grant":
            return self.nodes[v]["id"]
        return None

    def holds_edge_ids(self, grant_ids: set[str]) -> set[int]:
        return {e for (u, v, e, k, _, _) in self.edges if self.grant_of_edge(u, v, k) in grant_ids}

    def grant(self, gid: str) -> dict | None:
        return next((n for n in self.nodes.values() if n["label"] == "Grant" and n["id"] == gid), None)


@dataclass
class Plan:
    id: str
    label: str                      # "cheapest" | "what_if" | "fallback"
    grants: list[str]               # chosen candidate (default: source side)
    cost: int
    maxflow: float
    revocable: bool                 # False => no revocable cut (maxflow >= BIG)
    unique: bool = True
    alt_grants: list[str] | None = None   # the sink-side candidate when not unique
    tie_reason: str | None = None
    services_broken: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    blocking: list[str] = field(default_factory=list)  # structural/accepted edges when not revocable
    severed: bool | None = None
    proof: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# ── pure functions (tested against networkx) ─────────────────────────────────

def cost_from_usage(uses_30d: int) -> int:
    """cost = 1 + ceil(log2(1 + uses_30d))   (CEO-7)"""
    return 1 + math.ceil(math.log2(1 + max(0, int(uses_30d))))


def residual_cut(edges: list[tuple[int, int, int, float]], flows: dict[int, float],
                 source: int, sinks: set[int]) -> tuple[list[int], list[int], set[int]]:
    """Source-side and sink-side min cuts from a max flow.

    edges: (u, v, eid, capacity). Residual arcs: forward if cap-flow > 0,
    reverse if flow > 0. S = reachable from source; T* = can reach a sink.
    The min cut is unique iff both sides give the same edge set.
    """
    fwd: dict[int, list[int]] = {}
    rev: dict[int, list[int]] = {}
    for u, v, e, cap in edges:
        f = flows.get(e, 0.0)
        if cap - f > EPS:
            fwd.setdefault(u, []).append(v)
            rev.setdefault(v, []).append(u)
        if f > EPS:
            fwd.setdefault(v, []).append(u)
            rev.setdefault(u, []).append(v)
    S = {source}
    dq = deque([source])
    while dq:
        x = dq.popleft()
        if x in sinks:
            continue
        for y in fwd.get(x, ()):
            if y not in S:
                S.add(y)
                dq.append(y)
    T = set(sinks)
    dq = deque(sinks)
    while dq:
        x = dq.popleft()
        for y in rev.get(x, ()):
            if y not in T:
                T.add(y)
                dq.append(y)
    src_cut = sorted(e for u, v, e, _ in edges if u in S and v not in S)
    sink_cut = sorted(e for u, v, e, _ in edges if u not in T and v in T)
    return src_cut, sink_cut, S


def choose_default(candidates: list[tuple[list[str], list[str]]]) -> int:
    """Tie-break among equal-cost cuts (CEO-8 / CL-1): fewest known services
    broken, then the source-side cut (index 0 = earliest in the kill chain)."""
    best = 0
    for i, (_, broken) in enumerate(candidates):
        if len(broken) < len(candidates[best][1]):
            best = i
    return best


# ── graph-backed ─────────────────────────────────────────────────────────────

def subgraph(ctx: TenantCtx, finding: str) -> Sub:
    g = ctx.graph
    rows = Q.run(g, "BFS_NODES", {"finding": finding}, ro=True, label="reachability")
    if not rows:
        raise FindingNotFound(finding)
    src, ids = rows[0][0], rows[0][1]
    ids = sorted(set(ids) | {src})
    nodes = {}
    for r in Q.run(g, "NODE_INFO", {"ids": ids}, ro=True):
        nodes[r[0]] = {"label": r[1], "id": r[2], "name": r[3] or r[2], "jewel": bool(r[4]),
                       "kind": r[5], "cost": r[6], "uses_30d": r[7], "revocable": r[8],
                       "holder_id": r[9], "target_id": r[10], "owner": r[11]}
    edges = [(r[0], r[1], r[2], r[3], float(r[4]), float(r[5]))
             for r in Q.run(g, "INDUCED_EDGES", {"ids": ids}, ro=True)]
    jewels = sorted(n for n, d in nodes.items() if d["jewel"] and n != src)
    return Sub(finding, src, nodes, edges, jewels)


def _max_flow(g, sub: Sub, prop: str, label: str = "") -> tuple[float, dict[int, float]]:
    rows = Q.run(g, "MAX_FLOW", {"source": sub.source, "sinks": sub.jewels, "prop": prop},
                 ro=(prop != "cf"), label=label)
    if not rows:
        return 0.0, {}
    eids, flows, mf = rows[0]
    return float(mf), {e: float(f) for e, f in zip(eids, flows)}


def edge_caps(sub: Sub, base: str, big: set[int] = frozenset(), zero: set[int] = frozenset()):
    """In-memory capacities matching WRITE_CF exactly (invariant I2)."""
    out = []
    for u, v, e, kind, cap, unit in sub.edges:
        if e in zero:
            c = 0.0
        elif e in big or base == "big":
            c = float(BIG)
        elif base == "unit":
            c = unit
        else:
            c = cap
        out.append((u, v, e, c))
    return out


def with_capacities(ctx: TenantCtx, sub: Sub, base: str, big: set[int] = frozenset(),
                    zero: set[int] = frozenset(), label: str = "") -> tuple[float, dict[int, float]]:
    """The ONLY owner of the temporary `cf` property (ENG2-9, SD-2).

    I1 overwrite-before-read: inside the per-graph lock, cf is written on EVERY
       ATTACK edge before maxFlow reads it, so a stale cf can never be read.
    I2 the cut is computed from this call's flows + in-memory capacities only.
    I3 a failed cleanup marks the graph dirty; the next call must clear first,
       or it raises GraphUnavailable.
    I4 stored `cap` / `unit` are never written here.
    Work runs in a worker thread to completion, so request cancellation cannot
    skip the `finally` cleanup.
    """
    if ctx.readonly:
        raise GraphUnavailable("read-only template: counterfactuals disabled")
    g = ctx.graph
    with ctx.lock:
        try:
            Q.run(g, "CLEAR_CF")
            clear_cf_dirty(ctx.graph_name)
        except Exception as e:
            raise GraphUnavailable(f"cf cleanup failed: {e}") from e
        try:
            Q.run(g, "WRITE_CF", {"zero": sorted(zero), "big": sorted(big), "base": base, "BIG": BIG},
                  label=label)
            return _max_flow(g, sub, "cf", label)
        finally:
            try:
                Q.run(g, "CLEAR_CF")
            except Exception as e:  # connection lost mid-cleanup
                mark_cf_dirty(ctx.graph_name, repr(e))


def _cut_to_plan(ctx: TenantCtx, sub: Sub, caps, mf: float, flows: dict[int, float],
                 plan_id: str, label: str, kept: list[str] | None = None) -> Plan:
    if not sub.jewels:
        return Plan(plan_id, label, [], 0, 0.0, True, severed=True, proof="no crown jewel reachable")
    src_cut, sink_cut, S = residual_cut(caps, flows, sub.source, set(sub.jewels))
    capmap = {e: c for _, _, e, c in caps}
    if mf >= BIG - EPS:
        blocking = []
        for u, v, e, c in caps:
            if e in src_cut and c >= BIG:
                blocking.append(f"{sub.nodes[u]['name']} → {sub.nodes[v]['name']}")
        return Plan(plan_id, label, [], 0, mf, False, kept=kept or [], blocking=blocking)
    total = sum(capmap[e] for e in src_cut)
    if abs(total - mf) > 1e-3:
        raise CutAssertionError(f"cut capacity {total} != maxFlow {mf}")
    by_edge = {e: sub.grant_of_edge(u, v, k) for (u, v, e, k, _, _) in sub.edges}
    src_g = sorted({by_edge[e] for e in src_cut if by_edge.get(e)})
    sink_g = sorted({by_edge[e] for e in sink_cut if by_edge.get(e)})
    unique = src_g == sink_g
    cands = [src_g] if unique else [src_g, sink_g]
    broken = [services_broken(ctx, c) for c in cands]
    pick = choose_default(list(zip(cands, broken)))
    chosen = cands[pick]
    cost = int(round(sum(sub.grant(gid)["cost"] for gid in chosen)))
    tie = None
    if not unique:
        tie = ("breaks fewer known services" if len(broken[pick]) < len(broken[1 - pick])
               else "stops the attacker earlier")
    return Plan(plan_id, label, chosen, cost, mf, True, unique=unique,
                alt_grants=None if unique else cands[1 - pick], tie_reason=tie,
                services_broken=broken[pick], kept=kept or [])


def services_broken(ctx: TenantCtx, grants: list[str]) -> list[str]:
    if not grants:
        return []
    rows = Q.run(ctx.graph, "SERVICES_BROKEN", {"grants": grants}, ro=True)
    return sorted({s for _, names in rows for s in names})


def plan_cut(ctx: TenantCtx, sub: Sub, plan_id: str = "P0") -> Plan:
    """Cheapest revocation plan from stored capacities (no writes)."""
    if not sub.jewels:
        return Plan(plan_id, "cheapest", [], 0, 0.0, True, severed=True, proof="no crown jewel reachable")
    mf, flows = _max_flow(ctx.graph, sub, "cap", "cheapest cut")
    return _cut_to_plan(ctx, sub, edge_caps(sub, "cap"), mf, flows, plan_id, "cheapest")


def routes(ctx: TenantCtx, sub: Sub) -> int | None:
    """Independent attack routes: ONE unit-capacity maxFlow into the built-in
    virtual super-sink over all reachable jewels (SD-1). None = some route has
    no revocable grant at all."""
    if not sub.jewels:
        return 0
    mf, _ = _max_flow(ctx.graph, sub, "unit", "independent routes")
    return None if mf >= BIG - EPS else int(round(mf))


def shortest(ctx: TenantCtx, sub: Sub) -> dict | None:
    best = None
    for j in sub.jewels:
        rows = Q.run(ctx.graph, "SHORTEST_PATH", {"finding": sub.finding, "target": j}, ro=True,
                     label="shortest route")
        if not rows:
            continue
        ids, labels, _w = rows[0]
        grants = [i for i, lab in zip(ids, labels) if lab == "Grant"]
        cand = {"jewel": sub.nodes[j]["id"], "grants": len(grants), "path": ids}
        if best is None or cand["grants"] < best["grants"]:
            best = cand
    return best


def what_if(ctx: TenantCtx, sub: Sub, keep: list[str], plan_id: str) -> Plan:
    """Counterfactual: kept grants become uncuttable; FalkorDB recomputes."""
    big = sub.holds_edge_ids(set(keep))
    mf, flows = with_capacities(ctx, sub, "cap", big=big, label=f"what_if keep={keep}")
    return _cut_to_plan(ctx, sub, edge_caps(sub, "cap", big=big), mf, flows, plan_id, "what_if",
                        kept=list(keep))


def verify(ctx: TenantCtx, sub: Sub, plan: Plan) -> Plan:
    """Prove severance: plan's grants at 0, everything else BIG; maxFlow must be 0."""
    if not sub.jewels:
        plan.severed, plan.proof = True, "no crown jewel reachable"
        return plan
    if ctx.readonly:  # NEW-3: cannot write cf; fall back to the min-cut theorem
        plan.severed = plan.revocable
        plan.proof = "min-cut theorem: cut = maxFlow"
        return plan
    zero = sub.holds_edge_ids(set(plan.grants))
    mf, _ = with_capacities(ctx, sub, "big", zero=zero, label=f"verify {plan.id}")
    plan.severed = mf < EPS
    plan.proof = f"algo.maxFlow = {mf:g}"
    if not plan.severed:
        raise SeveranceError(plan.id, mf)
    return plan


def display_graph(sub: Sub) -> dict:
    """Nodes/edges on some route to a jewel, with grants collapsed into labelled
    edges (holder -grant-> target) for the UI."""
    rev: dict[int, list[int]] = {}
    for u, v, *_ in sub.edges:
        rev.setdefault(v, []).append(u)
    keep = set(sub.jewels)
    dq = deque(sub.jewels)
    while dq:
        x = dq.popleft()
        for y in rev.get(x, ()):
            if y not in keep:
                keep.add(y)
                dq.append(y)
    nodes, edges = [], []
    for nid in keep:
        n = sub.nodes[nid]
        if n["label"] != "Grant":
            nodes.append({"id": n["id"], "name": n["name"], "label": n["label"], "jewel": n["jewel"],
                          "finding": nid == sub.source})
    for u, v, e, k, cap, unit in sub.edges:
        if u not in keep or v not in keep:
            continue
        if k == "holds":
            gr = sub.nodes[v]
            edges.append({"id": gr["id"], "source": sub.nodes[u]["id"], "target": gr["target_id"],
                          "kind": gr["kind"], "grant": gr["id"], "cost": gr["cost"]})
        elif k in ("entry", "auth_as", "session"):
            edges.append({"id": f"s{e}", "source": sub.nodes[u]["id"], "target": sub.nodes[v]["id"], "kind": k})
    return {"nodes": nodes, "edges": edges}


def naive_cost(sub: Sub) -> int:
    """Revoke every revocable grant the compromised identity holds directly."""
    entry_targets = {v for (u, v, e, k, _, _) in sub.edges if u == sub.source}
    principals = set(entry_targets)
    frontier = list(entry_targets)
    while frontier:  # follow structural edges (auth_as / session) to the principals
        x = frontier.pop()
        for (u, v, e, k, _, _) in sub.edges:
            if u == x and k in ("auth_as", "session", "entry") and v not in principals:
                principals.add(v)
                frontier.append(v)
    total = 0
    for (u, v, e, k, cap, _) in sub.edges:
        if u in principals and k == "holds":
            gr = sub.nodes[v]
            if gr.get("revocable", True) is not False:
                total += int(gr["cost"])
    return total
