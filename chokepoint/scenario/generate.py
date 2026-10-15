"""Build the Northwind graph: hand-designed scenario + seeded noise.

Noise rule (ENG-9, OVE-6): noise grants are held by noise principals and
target noise resources only, so noise can never add a route from a scenario
entry to a crown jewel. The generator asserts that with networkx anyway.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
import yaml

from chokepoint import BIG
from chokepoint.cut import cost_from_usage

HERE = Path(__file__).parent
FIXTURES = ["northwind.yaml", "knowledge.yaml", "knowledge_fallback.jsonl", "knowledge_edges.jsonl"]

KIND_TO_TARGET = {
    "MEMBER_OF": "Group", "CAN_ASSUME": "Role",
    "READS": ("Database", "Bucket", "Secret"), "WRITES": ("Database", "Bucket"),
    "ADMIN_TO": ("Database", "Host"),
}


@dataclass
class Fixture:
    nodes: dict[str, dict] = field(default_factory=dict)          # id -> props (incl. label)
    attack: list[dict] = field(default_factory=list)              # {s, d, kind, cap, unit}
    context: list[tuple[str, str, str, dict]] = field(default_factory=list)  # (rel, s, d, props)

    def add(self, nid: str, label: str, **props):
        if nid in self.nodes:
            raise ValueError(f"duplicate id {nid}")
        self.nodes[nid] = {"id": nid, "label": label, **props}

    def attack_edge(self, s: str, d: str, kind: str, cap: float, unit: float):
        self.attack.append({"s": s, "d": d, "kind": kind, "cap": cap, "unit": unit})

    def ctx(self, rel: str, s: str, d: str, **props):
        self.context.append((rel, s, d, props))


def load_yaml(name: str) -> dict:
    return yaml.safe_load((HERE / name).read_text(encoding="utf-8"))


def knowledge_edges() -> tuple[list[dict], str]:
    """Extracted edges if committed (ingest_knowledge), else the hand-written fallback."""
    for fname, src in (("knowledge_edges.jsonl", "extracted"), ("knowledge_fallback.jsonl", "fallback")):
        p = HERE / fname
        if p.exists():
            rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
            return [r for r in rows if not r.get("_header")], src
    return [], "none"


def fixture_sha() -> str:
    h = hashlib.sha256()
    for f in FIXTURES:
        p = HERE / f
        if p.exists():
            h.update(p.read_bytes())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()[:8]


def add_grant(fx: Fixture, g: dict, names: dict[str, str]):
    cost = cost_from_usage(g["uses_30d"])
    revocable = g.get("revocable", True)
    fx.add(g["id"], "Grant", kind=g["kind"], uses_30d=g["uses_30d"], last_used=g.get("last_used"),
           cost=cost, revocable=revocable, holder_id=g["holder"], holder_name=names.get(g["holder"], g["holder"]),
           target_id=g["target"], target_name=names.get(g["target"], g["target"]), owner=g.get("owner"),
           ticket=g.get("ticket"), name=f'{names.get(g["holder"], g["holder"])} {g["kind"]} {names.get(g["target"], g["target"])}')
    fx.attack_edge(g["holder"], g["id"], "holds", cost if revocable else BIG, 1)
    fx.attack_edge(g["id"], g["target"], "grants", BIG, BIG)
    if g.get("owner"):
        fx.ctx("OWNS", g["owner"], g["id"])
    if g.get("granted_by"):
        fx.ctx("GRANTED_BY", g["id"], g["granted_by"])
    if g.get("ticket"):
        fx.ctx("GRANTED_VIA", g["id"], g["ticket"])


def build(seed: int = 42, noise: bool = True) -> Fixture:
    nw = load_yaml("northwind.yaml")
    kn = load_yaml("knowledge.yaml")
    fx = Fixture()
    names: dict[str, str] = {}

    for t in nw["teams"]:
        fx.add(t["id"], "Team", name=t["name"]); names[t["id"]] = t["name"]
    for p in nw["people"]:
        fx.add(p["id"], "Person", name=p["name"], synthetic=True); names[p["id"]] = p["name"]
        fx.ctx("MEMBER_OF_TEAM", p["id"], p["team"])
    for n in nw["nodes"]:
        props = {k: v for k, v in n.items() if k not in ("id", "label", "owner")}
        fx.add(n["id"], n["label"], **props); names[n["id"]] = n["name"]
        if n.get("owner"):
            fx.ctx("OWNS", n["owner"], n["id"])
    for s in nw["services"]:
        fx.add(s["id"], "Service", name=s["name"], criticality=s["criticality"]); names[s["id"]] = s["name"]
    for t in kn["tickets"]:
        fx.add(t["id"], "Ticket", title=t["title"], body=t["body"], status=t["status"], created=t["created"])
        fx.ctx("REQUESTED_BY", t["id"], t["requester"])
        fx.ctx("APPROVED_BY", t["id"], t["approver"])
    for g in nw["grants"]:
        add_grant(fx, g, names)
    for s in nw["services"]:
        for gid in s["depends_on"]:
            fx.ctx("DEPENDS_ON_GRANT", s["id"], gid)
    for st in nw["structural"]:
        fx.attack_edge(st["src"], st["dst"], st["kind"], BIG, BIG)
    for f in nw["findings"]:
        fx.add(f["id"], "Finding", title=f["title"], severity=f["severity"], at=f["at"], name=f["id"])
        for e in f["entry"]:
            fx.attack_edge(f["id"], e, "entry", BIG, BIG)
    for th in kn["threads"]:
        fx.add(th["id"], "Thread", channel=th["channel"], name=th["channel"])
    for m in kn["messages"]:
        fx.add(m["id"], "Message", text=m["text"], at=m["at"], name=m["id"])
        fx.ctx("WROTE", m["author"], m["id"])
        fx.ctx("HAS", m["thread"], m["id"])
    for d in kn["docs"]:
        fx.add(d["id"], "Doc", title=d["title"], section=d["section"], text=d["text"], name=f'{d["title"]} {d["section"]}')

    if noise:
        _noise(fx, names, seed)

    edges, _src = knowledge_edges()
    for e in edges:
        if e["source_id"] in fx.nodes and e["target_id"] in fx.nodes:
            props = {"span": e.get("span", "")}
            if e["rel"] == "GOVERNS":
                props["allows"] = e.get("allows", [])
            fx.ctx(e["rel"], e["source_id"], e["target_id"], **props)

    _check(fx, nw)
    return fx


def _noise(fx: Fixture, names: dict[str, str], seed: int):
    rnd = random.Random(seed)
    words = ["atlas", "birch", "cobalt", "delta", "ember", "fjord", "gale", "harbor", "indigo", "juniper",
             "kestrel", "lumen", "maple", "nimbus", "onyx", "pylon", "quartz", "rook", "sable", "tundra"]
    teams = [f"team:n{i}" for i in range(7)]
    for i, t in enumerate(teams):
        fx.add(t, "Team", name=f"{words[i].title()} Squad"); names[t] = f"{words[i].title()} Squad"
    all_teams = teams + ["team:platform", "team:data", "team:finance", "team:people-ops", "team:security"]
    pools: dict[str, list[str]] = {}

    def mk(prefix: str, label: str, n: int, extra=None):
        out = []
        for i in range(n):
            nid = f"{prefix}:n{i}"
            nm = f"{rnd.choice(words)}-{prefix}-{i}"
            fx.add(nid, label, name=nm, **(extra or {})); names[nid] = nm
            fx.ctx("OWNS", rnd.choice(all_teams), nid)
            out.append(nid)
        pools[label] = out
        return out

    people = []
    for i in range(143):
        nid = f"person:n{i}"
        nm = f"{rnd.choice(words).title()} {chr(65 + i % 26)}{i}"
        fx.add(nid, "Person", name=nm, synthetic=True); names[nid] = nm
        fx.ctx("MEMBER_OF_TEAM", nid, rnd.choice(all_teams))
        people.append(nid)
    pools["Person"] = people
    mk("group", "Group", 38); mk("role", "Role", 21); mk("sa", "ServiceAccount", 27)
    mk("host", "Host", 19); mk("db", "Database", 8); mk("bucket", "Bucket", 14); mk("secret", "Secret", 38)

    holders = pools["Person"] + pools["Group"] + pools["Role"] + pools["ServiceAccount"]
    gid = 1000
    for h in holders:
        for _ in range(rnd.randint(1, 3)):
            kind = rnd.choice(list(KIND_TO_TARGET))
            tl = KIND_TO_TARGET[kind]
            tl = tl if isinstance(tl, tuple) else (tl,)
            target = rnd.choice(pools[rnd.choice(tl)])
            if target == h:
                continue
            uses = rnd.choice([0, 0, 1, 3, 8, 20, 60, 150])
            add_grant(fx, {"id": f"G-{gid}", "holder": h, "kind": kind, "target": target, "uses_30d": uses,
                           "last_used": "2026-09-30", "owner": rnd.choice(all_teams),
                           "granted_by": rnd.choice(people)}, names)
            gid += 1
    # a little chat noise
    fx.add("thread:general", "Thread", channel="#general", name="#general")
    for i in range(24):
        mid = f"msg:gen-{i:02d}"
        g = f"G-{rnd.randint(1000, gid - 1)}"
        fx.add(mid, "Message", text=f"Does anyone still use {fx.nodes[g]['name']}? Cleaning up access this quarter.",
               at=f"2026-09-{(i % 28) + 1:02d}T10:00:00Z", name=mid)
        fx.ctx("WROTE", rnd.choice(people), mid)
        fx.ctx("HAS", "thread:general", mid)
        fx.ctx("MENTIONS", mid, g, span=fx.nodes[g]["name"])


def _check(fx: Fixture, nw: dict):
    """Grant invariant + noise isolation + cost bound."""
    G = nx.DiGraph()
    holds_in: dict[str, int] = {}
    grants_out: dict[str, int] = {}
    for e in fx.attack:
        assert e["s"] in fx.nodes and e["d"] in fx.nodes, f"dangling ATTACK edge {e}"
        G.add_edge(e["s"], e["d"])
        if e["kind"] == "holds":
            holds_in[e["d"]] = holds_in.get(e["d"], 0) + 1
        if e["kind"] == "grants":
            grants_out[e["s"]] = grants_out.get(e["s"], 0) + 1
    finite = 0
    for nid, n in fx.nodes.items():
        if n["label"] == "Grant":
            assert holds_in.get(nid) == 1 and grants_out.get(nid) == 1, f"grant invariant broken: {nid}"
            finite += n["cost"]
    assert finite < BIG / 10, "sum of finite costs must stay below BIG/10"
    for rel, s, d, _ in fx.context:
        assert s in fx.nodes and d in fx.nodes, f"dangling {rel} edge {s}->{d}"
    scenario_ids = {g["id"] for g in nw["grants"]} | {n["id"] for n in nw["nodes"]} | \
        {p["id"] for p in nw["people"]} | {f["id"] for f in nw["findings"]}
    jewels = {n for n, v in fx.nodes.items() if v.get("crown_jewel")}
    for f in nw["findings"]:
        reach = nx.descendants(G, f["id"]) if f["id"] in G else set()
        assert reach <= scenario_ids, f"noise leaked into {f['id']}'s reach: {sorted(reach - scenario_ids)[:5]}"
        assert reach & jewels, f"{f['id']} reaches no crown jewel"
