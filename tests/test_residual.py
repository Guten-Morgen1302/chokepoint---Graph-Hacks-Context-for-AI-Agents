"""Pure residual-cut function vs networkx on random weighted digraphs (no DB)."""

import itertools
import random

import networkx as nx

from chokepoint.cut import choose_default, cost_from_usage, residual_cut


def _random(seed, n=10, m=22):
    rnd = random.Random(seed)
    edges = []
    for e in range(m):
        u, v = rnd.randrange(n), rnd.randrange(n)
        if u != v:
            edges.append((u, v, e, float(rnd.randint(1, 9))))
    return edges


def _flows(edges, s, sinks):
    G = nx.DiGraph()
    for u, v, e, c in edges:
        if G.has_edge(u, v):  # keep simple digraph: merge parallel edges by id later
            G[u][v]["capacity"] += c
            G[u][v]["ids"].append((e, c))
        else:
            G.add_edge(u, v, capacity=c, ids=[(e, c)])
    G.add_node(s)
    for t in sinks:
        G.add_edge(t, "SINK", capacity=1e12, ids=[])
    val, fd = nx.maximum_flow(G, s, "SINK")
    flows = {}
    for u, v, d in G.edges(data=True):
        f = fd[u][v]
        for e, c in d["ids"]:  # split flow over parallel edges greedily
            take = min(c, f)
            flows[e] = take
            f -= take
    return val, flows


def test_cut_capacity_equals_maxflow_500_graphs():
    for seed in range(500):
        edges = _random(seed)
        s, sinks = 0, {8, 9}
        val, flows = _flows(edges, s, sinks)
        src, sink, S = residual_cut(edges, flows, s, sinks)
        cap = {e: c for _, _, e, c in edges}
        assert abs(sum(cap[e] for e in src) - val) < 1e-6, seed
        assert abs(sum(cap[e] for e in sink) - val) < 1e-6, seed
        # removing the cut disconnects s from every sink
        G = nx.DiGraph([(u, v) for u, v, e, _ in edges if e not in set(src)])
        G.add_node(s)
        assert not any(t in G and nx.has_path(G, s, t) for t in sinks), seed


def test_unique_flag_matches_brute_force():
    checked = 0
    for seed in range(300):
        edges = _random(seed, n=6, m=9)
        s, sinks = 0, {5}
        val, flows = _flows(edges, s, sinks)
        if val == 0:
            continue
        src, sink, _ = residual_cut(edges, flows, s, sinks)
        minimal = []
        for r in range(1, len(edges) + 1):
            for combo in itertools.combinations(edges, r):
                if abs(sum(c for *_, c in combo) - val) > 1e-9:
                    continue
                ids = {e for _, _, e, _ in combo}
                G = nx.DiGraph([(u, v) for u, v, e, _ in edges if e not in ids])
                G.add_node(s)
                if not (5 in G and nx.has_path(G, s, 5)):
                    minimal.append(frozenset(ids))
        unique = len(set(minimal)) == 1
        assert (src == sink) == unique, seed
        checked += 1
    assert checked > 50


def test_cost_formula():
    assert cost_from_usage(0) == 1
    assert cost_from_usage(1) == 2
    assert cost_from_usage(140) == 9
    assert cost_from_usage(3) == 3


def test_choose_default_tiebreak():
    # fewest services broken wins; otherwise source side (index 0)
    assert choose_default([(["a"], ["svc"]), (["b"], [])]) == 1
    assert choose_default([(["a"], []), (["b"], [])]) == 0
    assert choose_default([(["a"], [])]) == 0
