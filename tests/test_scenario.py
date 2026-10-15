"""The Northwind scenario reproduces expected.yaml through the REAL queries."""

import networkx as nx
import pytest

from chokepoint import cut
from chokepoint.scenario.generate import build, fixture_sha
from chokepoint.scenario.verify import expected, verify_graph

pytestmark = pytest.mark.db


def test_verify_graph_passes(scenario):
    out = verify_graph(scenario.graph_name)
    assert out["p1"] == ["G-101", "G-106"]


def test_menger_routes_le_cut_and_strict(scenario):
    """SD-1: routes == networkx unit flow into a super-sink, and routes <= |P0| (strictly here)."""
    sub = cut.subgraph(scenario, "F-1")
    r = cut.routes(scenario, sub)
    G = nx.DiGraph()
    for u, v, e, k, cap, unit in sub.edges:
        G.add_edge(u, v, capacity=unit)
    for j in sub.jewels:
        G.add_edge(j, "__SINK__", capacity=10**6)
    assert r == nx.maximum_flow_value(G, sub.source, "__SINK__")
    p0 = cut.plan_cut(scenario, sub)
    assert r <= len(p0.grants)          # never ==: the weighted optimum may revoke more grants
    assert r < len(p0.grants)           # menger-strict fixture


def test_generator_deterministic():
    a, b = build(seed=42), build(seed=42)
    assert sorted(a.nodes) == sorted(b.nodes)
    assert a.attack == b.attack
    assert len(fixture_sha()) == 8


def test_noise_never_reaches_scenario_entries():
    fx = build()
    G = nx.DiGraph([(e["s"], e["d"]) for e in fx.attack])
    jewels = {n for n, v in fx.nodes.items() if v.get("crown_jewel")}
    for f in ("F-1", "F-2"):
        reach = nx.descendants(G, f)
        assert all(not x.startswith(("G-1000", "person:n", "role:n", "group:n", "sa:n")) for x in reach)
        assert reach & jewels


def test_no_context_edge_is_attack(scenario):
    rows = scenario.graph.query("MATCH ()-[r:ATTACK]->() WHERE NOT r.kind IN ['holds','grants','entry','auth_as','session'] RETURN count(r)").result_set
    assert rows[0][0] == 0


def test_dr_grant_facts(scenario):
    ex = expected()["F-1"]["dr_grant"]
    rows = scenario.graph.query("MATCH (g:Grant {id: $id}) OPTIONAL MATCH (s:Service {id: 'svc:dr-failover'})-[:DEPENDS_ON_GRANT]->(g) RETURN g.uses_30d, count(s)", {"id": ex["id"]}).result_set
    assert rows[0][0] == ex["uses_30d"]
    assert (rows[0][1] > 0) == ex["depends_on_grant_from_dr_failover"]
