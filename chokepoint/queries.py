"""Every Cypher query and graph-algorithm call the product depends on.

Each query is a named constant, so the README "Queries" section can be
generated from this file (`python -m chokepoint.cli queries --markdown`).
Every execution goes through `run()`, which records an evidence entry
(query name, params, row count, ms). Those entries become the evidence
drawer in the UI.
"""

from __future__ import annotations

import contextvars
import time
from dataclasses import dataclass

# ── reachability ────────────────────────────────────────────────────────────

BFS_NODES = """
MATCH (f:Finding {id: $finding})
CALL algo.bfs(f, 64, 'ATTACK') YIELD nodes
RETURN id(f), [n IN nodes | id(n)]
"""
"""algo.bfs from the finding over ATTACK edges. Only `nodes` is used: probe 2b
showed `edges` are BFS tree edges, and the start node is not included."""

INDUCED_EDGES = """
MATCH (a)-[r:ATTACK]->(b) WHERE id(a) IN $ids
RETURN id(a), id(b), id(r), r.kind, r.cap, r.unit
"""
"""Every ATTACK edge whose source is in the BFS node set (ENG-3, OVE-1)."""

NODE_INFO = """
MATCH (n) WHERE id(n) IN $ids
RETURN id(n), n.label, n.id, n.name, coalesce(n.crown_jewel, false),
       n.kind, n.cost, n.uses_30d, n.revocable, n.holder_id, n.target_id, n.owner
"""

# ── flows (algo.maxFlow) ────────────────────────────────────────────────────

MAX_FLOW = """
MATCH (s) WHERE id(s) = $source
MATCH (t) WHERE id(t) IN $sinks
WITH s, collect(t) AS ts
CALL algo.maxFlow({sourceNodes: [s], targetNodes: ts,
                   relationshipTypes: ['ATTACK'], capacityProperty: $prop})
YIELD edges, edgeFlows, maxFlow
RETURN [e IN edges | id(e)], edgeFlows, maxFlow
"""
"""One call with all crown jewels as sinks: FalkorDB adds a virtual super-sink
(SD-1). $prop is 'cap' (cut), 'unit' (independent routes) or 'cf'
(counterfactual / verify)."""

CLEAR_CF = """
MATCH ()-[r:ATTACK]->() WHERE r.cf IS NOT NULL REMOVE r.cf
"""

WRITE_CF = """
MATCH ()-[r:ATTACK]->()
SET r.cf = CASE
  WHEN id(r) IN $zero THEN 0
  WHEN id(r) IN $big THEN $BIG
  WHEN $base = 'unit' THEN r.unit
  WHEN $base = 'big' THEN $BIG
  ELSE r.cap END
"""
"""ONE set-based write over ALL ATTACK edges (OVE2-2; probe 9: maxFlow errors if
any edge of the type lacks the property, even unreachable ones)."""

COUNT_CF = """
MATCH ()-[r:ATTACK]->() WHERE r.cf IS NOT NULL RETURN count(r)
"""

SHORTEST_PATH = """
MATCH (f:Finding {id: $finding}), (t) WHERE id(t) = $target
CALL algo.SPpaths({sourceNode: f, targetNode: t, relTypes: ['ATTACK'],
                   weightProp: 'w', pathCount: 1})
YIELD path, pathWeight
RETURN [n IN nodes(path) | n.id], [n IN nodes(path) | n.label], pathWeight
"""

# ── context: owners, services, provenance ───────────────────────────────────

SERVICES_BROKEN = """
MATCH (s:Service)-[:DEPENDS_ON_GRANT]->(g:Grant) WHERE g.id IN $grants
RETURN g.id, collect(s.name)
"""

GRANT_CONTEXT = """
MATCH (g:Grant) WHERE g.id IN $grants
OPTIONAL MATCH (g)-[:GRANTED_VIA]->(t:Ticket)
OPTIONAL MATCH (t)-[:REQUESTED_BY]->(req:Person)
OPTIONAL MATCH (t)-[:APPROVED_BY]->(apr:Person)
OPTIONAL MATCH (g)-[:GRANTED_BY]->(gb:Person)
OPTIONAL MATCH (team:Team)-[:OWNS]->(g)
RETURN g.id, g.kind, g.holder_id, g.holder_name, g.target_id, g.target_name, g.cost,
       g.uses_30d, g.last_used, g.revocable,
       t.id, t.title, t.body, req.name, apr.name, gb.name, team.name
"""

GRANT_MENTIONS = """
MATCH (src)-[m:MENTIONS]->(g:Grant {id: $grant})
WHERE src:Message OR src:Ticket OR src:Doc
OPTIONAL MATCH (author:Person)-[:WROTE]->(src)
OPTIONAL MATCH (th:Thread)-[:HAS]->(src)
RETURN src.id, src.label, coalesce(src.text, src.body), m.span,
       coalesce(src.title, th.channel), src.section, author.name
"""

GOVERNING_DOCS = """
MATCH (g:Grant {id: $grant})
MATCH (d:Doc)-[gv:GOVERNS]->(h:E) WHERE h.id = g.holder_id
RETURN d.id, d.title, d.section, d.text, gv.allows
"""

GRANT_DECISIONS = """
MATCH (d:Decision {grant_id: $grant})
RETURN d.id, d.disposition, d.status, d.rationale, d.review_by, d.by, d.at, d.cited_ids
ORDER BY d.at DESC
"""

WHO_KNOWS = """
MATCH (n:E {id: $node})
OPTIONAL MATCH (g:Grant) WHERE g.holder_id = $node OR g.target_id = $node OR g.id = $node
WITH n, collect(g) + [n] AS subjects
UNWIND subjects AS s
MATCH (src)-[:MENTIONS]->(s)
OPTIONAL MATCH (p1:Person)-[:WROTE]->(src)
OPTIONAL MATCH (src)-[:REQUESTED_BY|APPROVED_BY]->(p2:Person)
WITH [x IN [p1, p2] WHERE x IS NOT NULL] AS ps, src
UNWIND ps AS p
RETURN p.id, p.name, count(DISTINCT src) AS score
ORDER BY score DESC, p.name ASC
LIMIT 3
"""

WHO_OWNS = """
MATCH (n:E) WHERE n.id IN $ids
OPTIONAL MATCH (t:Team)-[:OWNS]->(n)
OPTIONAL MATCH (p:Person)-[:MEMBER_OF_TEAM]->(t)
RETURN n.id, coalesce(n.name, n.id), t.name, collect(p.name)
"""

# ── decisions ────────────────────────────────────────────────────────────────

HOLDER_REACH = """
MATCH (g:Grant {id: $grant})
MATCH (h:E) WHERE h.id = g.holder_id
CALL algo.bfs(h, 64, 'ATTACK') YIELD nodes
RETURN [n IN nodes WHERE n.crown_jewel = true | n.id]
"""
"""Jewels reachable from the grant's holder: what keeping this exception exposes."""

RECORD_DECISION = """
MATCH (g:Grant {id: $grant})
OPTIONAL MATCH (old:Decision {status: 'ACTIVE'})-[:ABOUT]->(g)
WITH g, collect(old) AS olds
FOREACH (o IN olds | SET o.status = 'SUPERSEDED')
CREATE (d:Decision {id: $did, grant_id: $grant, disposition: $disp, rationale: $rationale,
                    review_by: $review_by, by: $by, at: $at, status: 'ACTIVE',
                    cited_ids: $cites, baseline_jewels: $baseline})
CREATE (d)-[:ABOUT]->(g)
FOREACH (o IN olds | CREATE (d)-[:SUPERSEDES]->(o))
WITH d, g
MATCH ()-[r:ATTACK {kind: 'holds'}]->(g)
SET r.cap = CASE WHEN $disp = 'ACCEPT_RISK' OR g.revocable = false THEN $BIG ELSE g.cost END
RETURN d.id
"""
"""ONE query: supersede, create, and set holds.cap atomically (ENG2-7)."""

LINK_CITES = """
MATCH (d:Decision {id: $did})
UNWIND $cites AS cid
MATCH (c:E) WHERE c.id = cid AND (c:Ticket OR c:Message OR c:Doc)
CREATE (d)-[:CITES]->(c)
"""

WITHDRAW_DECISION = """
MATCH (d:Decision {id: $did, status: 'ACTIVE'})-[:ABOUT]->(g:Grant)
SET d.status = 'WITHDRAWN'
WITH g
MATCH ()-[r:ATTACK {kind: 'holds'}]->(g)
SET r.cap = CASE WHEN g.revocable = false THEN $BIG ELSE g.cost END
"""

ALL_DECISIONS = """
MATCH (d:Decision)
OPTIONAL MATCH (d)-[:ABOUT]->(g:Grant)
RETURN d.id, d.grant_id, d.disposition, d.status, d.rationale, d.review_by, d.by, d.at,
       d.cited_ids, d.baseline_jewels, g IS NOT NULL
ORDER BY d.at DESC
"""

GRANT_EXISTS = """
MATCH (g:Grant {id: $grant}) RETURN g.id
"""

EXISTING_IDS = """
UNWIND $ids AS i MATCH (n:E {id: i}) RETURN n.id
"""

VERIFY_CAPS = """
MATCH (h)-[r:ATTACK {kind: 'holds'}]->(g:Grant)
OPTIONAL MATCH (d:Decision {status: 'ACTIVE', disposition: 'ACCEPT_RISK'})-[:ABOUT]->(g)
WITH g, r, count(d) AS acc
WITH g, r, CASE WHEN acc > 0 OR g.revocable = false THEN $BIG ELSE g.cost END AS want
WHERE r.cap <> want
RETURN g.id, r.cap, want
"""


@dataclass
class Evidence:
    name: str
    cypher: str
    params: dict
    rows: int
    ms: float
    label: str = ""


_evidence: contextvars.ContextVar[list | None] = contextvars.ContextVar("evidence", default=None)


def start_evidence() -> list:
    lst: list = []
    _evidence.set(lst)
    return lst


def current_evidence() -> list:
    return _evidence.get() or []


def run(graph, name: str, params: dict | None = None, *, ro: bool = False, label: str = ""):
    """Execute a named query and record evidence."""
    cypher = globals()[name]
    t0 = time.perf_counter()
    res = graph.ro_query(cypher, params or {}) if ro else graph.query(cypher, params or {})
    ms = (time.perf_counter() - t0) * 1000
    lst = _evidence.get()
    if lst is not None:
        shown = {k: v for k, v in (params or {}).items() if not (isinstance(v, list) and len(v) > 12)}
        lst.append(Evidence(name, cypher.strip(), shown, len(res.result_set), round(ms, 2), label))
    return res.result_set


def all_queries() -> list[tuple[str, str, str]]:
    import inspect
    import sys

    mod = sys.modules[__name__]
    src = inspect.getsource(mod)
    out = []
    for name, val in vars(mod).items():
        if name.isupper() and isinstance(val, str) and ("MATCH" in val or "UNWIND" in val):
            # docstring = string literal right after the constant, if any
            doc = ""
            marker = f'{name} = """'
            i = src.find(marker)
            if i >= 0:
                j = src.find('"""', i + len(marker))
                k = src.find('"""', j + 3)
                after = src[j + 3:k + 3 if k >= 0 else j + 3].strip()
                if after.startswith('"""'):
                    doc = after.strip('"').strip()
            out.append((name, val.strip(), doc))
    return out
