"""Seed-time verification: the live graph must reproduce expected.yaml
through the REAL FalkorDB queries before the template pointer switches."""

from __future__ import annotations

from pathlib import Path

import yaml

from chokepoint import cut
from chokepoint.graphdb import TenantCtx
from chokepoint.knowledge import explain_grant, keyword_baseline

HERE = Path(__file__).parent


def expected() -> dict:
    return yaml.safe_load((HERE / "expected.yaml").read_text(encoding="utf-8"))


class VerifyError(AssertionError):
    pass


def _eq(what, got, want):
    if got != want:
        raise VerifyError(f"{what}: got {got!r}, expected {want!r}")


def verify_graph(graph_name: str) -> dict:
    ex = expected()
    ctx = TenantCtx(graph_name)
    out = {}

    f1 = cut.subgraph(ctx, "F-1")
    _eq("F-1 jewels", sorted(f1.nodes[j]["id"] for j in f1.jewels), sorted(ex["F-1"]["jewels"]))
    r = cut.routes(ctx, f1)
    _eq("F-1 routes", r, ex["F-1"]["routes"])
    p0 = cut.plan_cut(ctx, f1)
    _eq("F-1 P0 grants", p0.grants, ex["F-1"]["P0"]["grants"])
    _eq("F-1 P0 cost", p0.cost, ex["F-1"]["P0"]["cost"])
    _eq("F-1 P0 unique", p0.unique, ex["F-1"]["P0"]["unique"])
    if not r <= len(p0.grants):
        raise VerifyError("Menger bound violated: routes > |P0|")
    _eq("F-1 menger strict", r < len(p0.grants), ex["F-1"]["menger_strict"])
    _eq("F-1 naive cost", cut.naive_cost(f1), ex["F-1"]["naive_cost"])
    sp = cut.shortest(ctx, f1)
    _eq("F-1 shortest grants", sp["grants"], ex["F-1"]["shortest_grants"])
    p1 = cut.what_if(ctx, f1, ex["F-1"]["P1_keep"], "P1")
    _eq("F-1 P1 grants", p1.grants, ex["F-1"]["P1"]["grants"])
    _eq("F-1 P1 cost", p1.cost, ex["F-1"]["P1"]["cost"])
    _eq("F-1 P1 services_broken", p1.services_broken, ex["F-1"]["P1"]["services_broken"])
    cut.verify(ctx, f1, p1)
    prov = explain_grant(ctx, p0.grants)
    kb_keep = keyword_baseline(prov)
    _eq("keyword baseline keep", sorted(kb_keep), sorted(ex["F-1"]["keyword_baseline"]["keep"]))
    kb = cut.what_if(ctx, f1, kb_keep, "KB")
    _eq("keyword baseline plan", kb.grants, ex["F-1"]["keyword_baseline"]["plan"]["grants"])
    _eq("keyword baseline cost", kb.cost, ex["F-1"]["keyword_baseline"]["plan"]["cost"])
    if kb.grants == p1.grants:
        raise VerifyError("keyword baseline accidentally matches the agent's plan (SD-3)")

    f2 = cut.subgraph(ctx, "F-2")
    _eq("F-2 routes", cut.routes(ctx, f2), ex["F-2"]["routes"])
    _eq("F-2 shortest", cut.shortest(ctx, f2)["grants"], ex["F-2"]["shortest_grants"])
    b = cut.plan_cut(ctx, f2)
    _eq("F-2 before unique", b.unique, ex["F-2"]["before_accept"]["unique"])
    _eq("F-2 before src", b.grants, ex["F-2"]["before_accept"]["grants_src"])
    _eq("F-2 before sink", b.alt_grants, ex["F-2"]["before_accept"]["grants_sink"])
    _eq("F-2 before cost", b.cost, ex["F-2"]["before_accept"]["cost"])
    a = cut.what_if(ctx, f2, ["G-102"], "F2acc")
    _eq("F-2 after src", a.grants, ex["F-2"]["after_accept_G-102"]["grants_src"])
    _eq("F-2 after sink", a.alt_grants, ex["F-2"]["after_accept_G-102"]["grants_sink"])
    _eq("F-2 after cost", a.cost, ex["F-2"]["after_accept_G-102"]["cost"])

    for gid, want in ex["policy"].items():
        p = explain_grant(ctx, [gid])[0]["policy"]["status"]
        _eq(f"policy {gid}", p, want)
    for src, tgt in ex["must_mention"]:
        prov = explain_grant(ctx, [tgt])[0]
        if src not in {m["source_id"] for m in prov["mentions"]}:
            raise VerifyError(f"missing MENTIONS {src} -> {tgt}")
    out.update(routes=r, p0=p0.grants, p1=p1.grants, keyword=kb.grants)
    return out
