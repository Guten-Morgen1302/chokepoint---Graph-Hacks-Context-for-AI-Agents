"""Write a Fixture into FalkorDB and manage the versioned template (ENG-6).

Every node also carries the label `:E` (indexed on `id`) so edges can be
created by id quickly; the semantic label is stored too as `n.label`.
"""

from __future__ import annotations

import time
from collections import defaultdict

from chokepoint.graphdb import db, set_template, template_name

from .generate import Fixture, build, fixture_sha

BATCH = 500


def _chunks(rows, n=BATCH):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


def write_fixture(graph_name: str, fx: Fixture) -> dict:
    g = db().select_graph(graph_name)
    try:
        g.delete()
    except Exception:
        pass
    g = db().select_graph(graph_name)
    by_label: dict[str, list[dict]] = defaultdict(list)
    for n in fx.nodes.values():
        by_label[n["label"]].append({k: v for k, v in n.items() if v is not None})
    for label, rows in by_label.items():
        for chunk in _chunks(rows):
            g.query(f"UNWIND $rows AS r CREATE (n:{label}:E) SET n = r", {"rows": chunk})
    g.query("CREATE INDEX FOR (n:E) ON (n.id)")
    g.query("CREATE INDEX FOR (n:Grant) ON (n.id)")
    g.query("CREATE INDEX FOR (n:Decision) ON (n.grant_id)")
    for chunk in _chunks(fx.attack):
        g.query("""UNWIND $rows AS r
                   MATCH (a:E {id: r.s}), (b:E {id: r.d})
                   CREATE (a)-[:ATTACK {kind: r.kind, cap: r.cap, unit: r.unit, w: 1}]->(b)""",
                {"rows": chunk})
    by_rel: dict[str, list[dict]] = defaultdict(list)
    for rel, s, d, props in fx.context:
        by_rel[rel].append({"s": s, "d": d, "p": props})
    for rel, rows in by_rel.items():
        for chunk in _chunks(rows):
            g.query(f"""UNWIND $rows AS r
                        MATCH (a:E {{id: r.s}}), (b:E {{id: r.d}})
                        CREATE (a)-[x:{rel}]->(b) SET x = r.p""", {"rows": chunk})
    return {"nodes": len(fx.nodes), "attack_edges": len(fx.attack), "context_edges": len(fx.context)}


def seed(verify: bool = True) -> dict:
    """Build the template, verify it against expected.yaml, then switch the pointer."""
    t0 = time.time()
    fx = build()
    name = f"tmpl_{fixture_sha()}"
    stats = write_fixture(name, fx)
    if verify:
        from .verify import verify_graph
        verify_graph(name)
    old = set_template(name)
    if old and old != name:
        try:
            db().select_graph(old).delete()
        except Exception:
            pass
    stats.update({"template": name, "previous": old, "seconds": round(time.time() - t0, 2)})
    return stats


def ensure_template() -> str:
    """Seed if no template exists or the fixtures changed."""
    want = f"tmpl_{fixture_sha()}"
    if template_name() != want or want not in set(db().list_graphs()):
        seed()
    return want
