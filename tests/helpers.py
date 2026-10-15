"""Random grant graphs shared by FalkorDB and networkx (same BIG sentinel)."""

import random

import networkx as nx

from chokepoint import BIG


def random_grant_graph(seed: int, n_principals: int = 8, n_grants: int = 16, n_jewels: int = 2):
    """Principals P0..Pn, grants G0..Gm (reified), finding F -> P0, jewels J0..Jk.
    Returns (nodes, attack_edges) in the generator's Fixture shape."""
    rnd = random.Random(seed)
    nodes = {"F": {"id": "F", "label": "Finding", "name": "F"}}
    for i in range(n_principals):
        nodes[f"P{i}"] = {"id": f"P{i}", "label": "Role", "name": f"P{i}"}
    for j in range(n_jewels):
        nodes[f"J{j}"] = {"id": f"J{j}", "label": "Database", "name": f"J{j}", "crown_jewel": True}
    targets = [f"P{i}" for i in range(1, n_principals)] + [f"J{j}" for j in range(n_jewels)]
    edges = [{"s": "F", "d": "P0", "kind": "entry", "cap": BIG, "unit": BIG}]
    for g in range(n_grants):
        h = f"P{rnd.randrange(n_principals)}"
        t = rnd.choice(targets)
        if t == h:
            continue
        cost = rnd.randint(1, 9)
        gid = f"G{g}"
        nodes[gid] = {"id": gid, "label": "Grant", "name": gid, "kind": "CAN_ASSUME", "cost": cost,
                      "revocable": True, "holder_id": h, "target_id": t, "uses_30d": 0}
        edges.append({"s": h, "d": gid, "kind": "holds", "cap": cost, "unit": 1})
        edges.append({"s": gid, "d": t, "kind": "grants", "cap": BIG, "unit": BIG})
    return nodes, edges


def to_nx(nodes, edges, prop: str, forced_big: set[str] = frozenset()):
    G = nx.DiGraph()
    for e in edges:
        c = e[prop]
        if e["kind"] == "holds" and e["d"] in forced_big:
            c = BIG
        G.add_edge(e["s"], e["d"], capacity=c)
    for nid, n in nodes.items():
        if n.get("crown_jewel"):
            G.add_edge(nid, "__SINK__", capacity=BIG)  # explicit super-sink (SD-1)
    return G


def nx_flow(nodes, edges, prop: str, forced_big=frozenset()) -> float:
    G = to_nx(nodes, edges, prop, forced_big)
    if "F" not in G or "__SINK__" not in G or not nx.has_path(G, "F", "__SINK__"):
        return 0.0
    return nx.maximum_flow_value(G, "F", "__SINK__")


def load(ctx, nodes, edges):
    from chokepoint.scenario.generate import Fixture
    from chokepoint.scenario.seed import write_fixture

    fx = Fixture()
    fx.nodes = nodes
    fx.attack = edges
    write_fixture(ctx.graph_name, fx)
