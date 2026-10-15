"""SD-2: with_capacities never leaves `cf` behind and never reads a stale one."""

import random
import threading

import pytest

from chokepoint import BIG, cut
from chokepoint import queries as Q
from chokepoint.graphdb import GraphUnavailable, cf_dirty

from .helpers import load, nx_flow, random_grant_graph

pytestmark = pytest.mark.db


def _cf_count(ctx):
    return Q.run(ctx.graph, "COUNT_CF")[0][0]


def _setup(blank, seed=3):
    nodes, edges = random_grant_graph(seed, n_grants=20)
    load(blank, nodes, edges)
    return nodes, edges, cut.subgraph(blank, "F")


def test_cf_cleared_after_success(blank):
    _, _, sub = _setup(blank)
    cut.with_capacities(blank, sub, "cap")
    assert _cf_count(blank) == 0


def test_cf_cleared_when_maxflow_raises(blank, monkeypatch):
    _, _, sub = _setup(blank)

    def boom(*a, **k):
        raise RuntimeError("maxFlow exploded")
    monkeypatch.setattr(cut, "_max_flow", boom)
    with pytest.raises(RuntimeError):
        cut.with_capacities(blank, sub, "cap")
    assert _cf_count(blank) == 0


def test_failed_cleanup_marks_dirty_and_heals(blank, monkeypatch):
    _, _, sub = _setup(blank)
    real_run = Q.run
    state = {"calls": 0}

    def flaky(g, name, *a, **k):
        if name == "CLEAR_CF":
            state["calls"] += 1
            if state["calls"] == 2:          # the cleanup inside `finally`
                raise ConnectionError("lost")
        return real_run(g, name, *a, **k)
    monkeypatch.setattr(Q, "run", flaky)
    cut.with_capacities(blank, sub, "cap")
    assert cf_dirty(blank.graph_name)
    monkeypatch.setattr(Q, "run", real_run)
    cut.with_capacities(blank, sub, "cap")    # next call heals first (I3)
    assert cf_dirty(blank.graph_name) is None
    assert _cf_count(blank) == 0


def test_dirty_graph_refuses_when_clear_fails(blank, monkeypatch):
    _, _, sub = _setup(blank)
    real_run = Q.run

    def always_fail(g, name, *a, **k):
        if name == "CLEAR_CF":
            raise ConnectionError("down")
        return real_run(g, name, *a, **k)
    monkeypatch.setattr(Q, "run", always_fail)
    with pytest.raises(GraphUnavailable):
        cut.with_capacities(blank, sub, "cap")


def test_garbage_cf_is_overwritten_before_read(blank):
    """I1: stale cf = 0 on random edges must not change the answer."""
    nodes, edges, sub = _setup(blank, seed=7)
    want = nx_flow(nodes, edges, "cap")
    blank.graph.query("MATCH ()-[r:ATTACK]->() WITH r, rand() AS x WHERE x < 0.5 SET r.cf = 0")
    mf, _ = cut.with_capacities(blank, sub, "cap")
    assert abs(mf - min(want, BIG)) < 1e-6 or (want >= BIG and mf >= BIG)


def test_stored_cap_and_unit_never_touched(blank):
    _, _, sub = _setup(blank, seed=11)
    before = blank.graph.query("MATCH ()-[r:ATTACK]->() RETURN id(r), r.cap, r.unit ORDER BY id(r)").result_set
    rnd = random.Random(1)
    for i in range(50):
        keep = rnd.sample([n["id"] for n in sub.nodes.values() if n["label"] == "Grant"], 2)
        cut.with_capacities(blank, sub, "cap", big=sub.holds_edge_ids(set(keep)))
    after = blank.graph.query("MATCH ()-[r:ATTACK]->() RETURN id(r), r.cap, r.unit ORDER BY id(r)").result_set
    assert before == after


def test_concurrent_calls_do_not_see_each_others_cf(blank):
    nodes, edges, sub = _setup(blank, seed=5)
    grants = [n["id"] for n in sub.nodes.values() if n["label"] == "Grant"]
    expected, results, errors = {}, {}, []
    for i, g in enumerate(grants[:6]):
        expected[i] = nx_flow(nodes, edges, "cap", forced_big={g})

    def work(i, g):
        try:
            results[i] = cut.with_capacities(blank, sub, "cap", big=sub.holds_edge_ids({g}))[0]
        except Exception as e:  # pragma: no cover
            errors.append(e)
    ts = [threading.Thread(target=work, args=(i, g)) for i, g in enumerate(grants[:6])]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errors
    for i in results:
        w = expected[i]
        assert (results[i] >= BIG and w >= BIG) or abs(results[i] - w) < 1e-6
    assert _cf_count(blank) == 0


def test_verify_partial_plan_raises(scenario):
    sub = cut.subgraph(scenario, "F-1")
    p = cut.Plan("Px", "test", ["G-102"], 1, 1.0, True)
    with pytest.raises(cut.SeveranceError):
        cut.verify(scenario, sub, p)
    assert _cf_count(scenario) == 0
