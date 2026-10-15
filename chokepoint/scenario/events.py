"""Whitelisted scenario events (ENG2-7): the only graph mutations a visitor
can trigger besides decisions. Each event applies at most once per graph."""

from __future__ import annotations

from chokepoint import BIG
from chokepoint.cut import cost_from_usage
from chokepoint.graphdb import TenantCtx

from .generate import knowledge_edges, load_yaml


class ScenarioEventRejected(Exception):
    pass


def events() -> dict:
    return load_yaml("northwind.yaml")["events"]


def applied(ctx: TenantCtx) -> list[str]:
    rows = ctx.graph.ro_query("MATCH (e:AppliedEvent) RETURN e.id").result_set
    return [r[0] for r in rows]


def apply_event(ctx: TenantCtx, event_id: str) -> dict:
    ev = events().get(event_id)
    if ev is None:
        raise ScenarioEventRejected(f"unknown event {event_id}")
    if ctx.readonly:
        raise ScenarioEventRejected("demo busy: shared read-only copy")
    with ctx.lock:   # never mutate ATTACK edges while a cf computation runs
        return _apply(ctx, event_id, ev)


def _apply(ctx: TenantCtx, event_id: str, ev: dict) -> dict:
    if event_id in applied(ctx):
        raise ScenarioEventRejected("Change rejected: already applied.")
    g = ctx.graph
    out = {"event": event_id, "title": ev["title"]}
    if "add_grant" in ev:
        gr = ev["add_grant"]
        cost = cost_from_usage(gr["uses_30d"])
        g.query("""
            MATCH (h:E {id: $holder}), (t:E {id: $target})
            CREATE (x:Grant:E {id: $id, label: 'Grant', kind: $kind, uses_30d: $uses, cost: $cost,
                               revocable: true, holder_id: $holder, holder_name: h.name,
                               target_id: $target, target_name: t.name, owner: $owner, ticket: $ticket,
                               name: h.name + ' ' + $kind + ' ' + t.name})
            CREATE (h)-[:ATTACK {kind: 'holds', cap: $cost, unit: 1, w: 1}]->(x)
            CREATE (x)-[:ATTACK {kind: 'grants', cap: $BIG, unit: $BIG, w: 1}]->(t)
            WITH x
            OPTIONAL MATCH (tm:Team {id: $owner})
            FOREACH (_ IN CASE WHEN tm IS NULL THEN [] ELSE [1] END | CREATE (tm)-[:OWNS]->(x))
            WITH x
            OPTIONAL MATCH (tk:Ticket {id: $ticket})
            FOREACH (_ IN CASE WHEN tk IS NULL THEN [] ELSE [1] END | CREATE (x)-[:GRANTED_VIA]->(tk))
            WITH x
            OPTIONAL MATCH (p:Person {id: $granted_by})
            FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END | CREATE (x)-[:GRANTED_BY]->(p))
        """, {"id": gr["id"], "holder": gr["holder"], "target": gr["target"], "kind": gr["kind"],
              "uses": gr["uses_30d"], "cost": cost, "owner": gr["owner"], "ticket": gr["ticket"],
              "granted_by": gr["granted_by"], "BIG": BIG})
        out["added_grant"] = gr["id"]
    if "remove_grant" in ev:
        g.query("MATCH (x:Grant {id: $id}) DETACH DELETE x", {"id": ev["remove_grant"]})
        out["removed_grant"] = ev["remove_grant"]
    if "add_message" in ev:
        m = ev["add_message"]
        g.query("""
            MATCH (p:Person {id: $author}), (th:Thread {id: $thread})
            CREATE (msg:Message:E {id: $id, label: 'Message', text: $text, at: $at, name: $id})
            CREATE (p)-[:WROTE]->(msg)
            CREATE (th)-[:HAS]->(msg)
        """, {"id": m["id"], "author": m["author"], "thread": m["thread"], "text": m["text"], "at": m["at"]})
        edges, _ = knowledge_edges()
        mine = [e for e in edges if e["source_id"] == m["id"]]
        for e in mine:
            g.query("""MATCH (s:E {id: $s}), (t:E {id: $t}) CREATE (s)-[:MENTIONS {span: $span}]->(t)""",
                    {"s": e["source_id"], "t": e["target_id"], "span": e["span"]})
        out["ingested"] = {"message": m["id"], "mentions": len(mine), "mode": "pre-extracted"}
    g.query("CREATE (:AppliedEvent {id: $id})", {"id": event_id})
    return out
