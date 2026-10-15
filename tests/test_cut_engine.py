"""Real FalkorDB algo.maxFlow + our residual cut vs networkx (reified grants)."""

import networkx as nx
import pytest

from chokepoint import BIG, cut

from .helpers import load, nx_flow, random_grant_graph

pytestmark = pytest.mark.db


def _sub(ctx):
    return cut.subgraph(ctx, "F")


@pytest.mark.parametrize("seed", range(30))
def test_plan_cut_matches_networkx(blank, seed):
    nodes, edges = random_grant_graph(seed)
    load(blank, nodes, edges)
    sub = _sub(blank)
    want = nx_flow(nodes, edges, "cap")
    if not sub.jewels:
        return
    p = cut.plan_cut(blank, sub)
    if want >= BIG:
        assert not p.revocable
        return
    assert abs(p.maxflow - want) < 1e-6
    assert p.cost == round(want)
    # removing the chosen grants severs every route (independent check)
    G = nx.DiGraph([(e["s"], e["d"]) for e in edges if not (e["kind"] == "holds" and e["d"] in p.grants)])
    assert not any(j in G and "F" in G and nx.has_path(G, "F", j) for j in nodes if nodes[j].get("crown_jewel"))


@pytest.mark.parametrize("seed", range(30))
def test_routes_equal_unit_maxflow_into_super_sink(blank, seed):
    """SD-1: ONE unit-capacity maxFlow into the virtual super-sink."""
    nodes, edges = random_grant_graph(seed)
    load(blank, nodes, edges)
    sub = _sub(blank)
    want = nx_flow(nodes, edges, "unit")
    r = cut.routes(blank, sub)
    if want >= BIG:
        assert r is None
    else:
        assert r == round(want)
        if sub.jewels and r:
            assert r <= len(cut.plan_cut(blank, sub).grants)   # Menger: an inequality, never ==


def test_summing_per_jewel_flows_overcounts(blank):
    """Two jewels behind ONE shared grant: summing per jewel gives 2, truth is 1."""
    nodes = {"F": {"id": "F", "label": "Finding", "name": "F"},
             "A": {"id": "A", "label": "Role", "name": "A"}, "B": {"id": "B", "label": "Role", "name": "B"},
             "J0": {"id": "J0", "label": "Database", "name": "J0", "crown_jewel": True},
             "J1": {"id": "J1", "label": "Database", "name": "J1", "crown_jewel": True}}
    edges = [{"s": "F", "d": "A", "kind": "entry", "cap": BIG, "unit": BIG}]
    for gid, h, t in (("G0", "A", "B"), ("G1", "B", "J0"), ("G2", "B", "J1")):
        nodes[gid] = {"id": gid, "label": "Grant", "name": gid, "kind": "X", "cost": 5, "revocable": True,
                      "holder_id": h, "target_id": t, "uses_30d": 0}
        edges += [{"s": h, "d": gid, "kind": "holds", "cap": 5, "unit": 1},
                  {"s": gid, "d": t, "kind": "grants", "cap": BIG, "unit": BIG}]
    load(blank, nodes, edges)
    sub = _sub(blank)
    assert cut.routes(blank, sub) == 1
    per_jewel = sum(nx_flow({k: v for k, v in nodes.items() if not v.get("crown_jewel") or k == j}, edges, "unit")
                    for j in ("J0", "J1"))
    assert per_jewel == 2


def test_no_revocable_cut(blank):
    nodes = {"F": {"id": "F", "label": "Finding", "name": "F"},
             "J": {"id": "J", "label": "Database", "name": "J", "crown_jewel": True}}
    edges = [{"s": "F", "d": "J", "kind": "entry", "cap": BIG, "unit": BIG}]
    load(blank, nodes, edges)
    p = cut.plan_cut(blank, _sub(blank))
    assert not p.revocable


def test_not_reachable(blank):
    nodes = {"F": {"id": "F", "label": "Finding", "name": "F"},
             "A": {"id": "A", "label": "Role", "name": "A"},
             "J": {"id": "J", "label": "Database", "name": "J", "crown_jewel": True}}
    edges = [{"s": "F", "d": "A", "kind": "entry", "cap": BIG, "unit": BIG}]
    load(blank, nodes, edges)
    sub = _sub(blank)
    assert sub.jewels == []
    p = cut.plan_cut(blank, sub)
    assert p.grants == [] and p.severed


def test_cut_assertion_on_corrupted_flows():
    sub = cut.Sub("F", 0, {0: {"label": "Finding", "id": "F"}, 1: {"label": "Database", "id": "J", "jewel": True}},
                  [(0, 1, 7, "holds", 3.0, 1.0)], [1])
    with pytest.raises(cut.CutAssertionError):
        cut._cut_to_plan(None, sub, [(0, 1, 7, 3.0)], 5.0, {7: 3.0}, "P0", "cheapest")
