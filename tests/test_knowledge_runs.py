import pytest

from chokepoint import cut, tools
from chokepoint.knowledge import explain_grant, keyword_baseline, policy_status, validate_edges, who_knows
from chokepoint.runs import BudgetExceeded, ConstraintRejected, RunCtx, check_cites
from chokepoint.scenario.verify import expected


def test_policy_status_cases():
    assert policy_status("ADMIN_TO", [])["status"] == "none"
    d = [{"id": "d1", "title": "P", "section": "§1", "allows": ["WRITES"]},
         {"id": "d2", "title": "Q", "section": "§2", "allows": ["READS"]}]
    assert policy_status("READS", d)["status"] == "ok"            # union rule
    v = policy_status("ADMIN_TO", d)
    assert v["status"] == "violation" and v["allowed"] == ["READS", "WRITES"]


def test_validate_edges_drops_bad():
    text = "deployer needs WRITES"
    good, bad = validate_edges([
        {"target_id": "G-1", "rel": "MENTIONS", "span": "deployer"},
        {"target_id": "G-9", "rel": "MENTIONS", "span": "deployer"},
        {"target_id": "G-1", "rel": "MENTIONS", "span": "not in text"},
        {"target_id": "G-1", "rel": "LIKES", "span": "deployer"},
    ], "doc:a", text, {"G-1"})
    assert len(good) == 1 and len(bad) == 3


def test_check_cites_cases():
    run = RunCtx()
    run.register("doc:dr-runbook", "Doc")
    run.register("G-102", "Grant")
    with pytest.raises(ConstraintRejected, match="no source"):
        check_cites(run, [])
    with pytest.raises(ConstraintRejected, match="not seen"):
        check_cites(run, ["doc:other"])
    with pytest.raises(ConstraintRejected, match="grant id alone"):
        check_cites(run, ["G-102"])
    check_cites(run, ["doc:dr-runbook", "G-102"])


@pytest.mark.db
def test_must_mention_and_policy(scenario):
    ex = expected()
    for src, tgt in ex["must_mention"]:
        assert src in {m["source_id"] for m in explain_grant(scenario, [tgt])[0]["mentions"]}
    for gid, want in ex["policy"].items():
        assert explain_grant(scenario, [gid])[0]["policy"]["status"] == want


@pytest.mark.db
def test_keyword_baseline_is_wrong(scenario):
    """SD-3: a regex over 'deployer' + dependency verbs keeps the wrong grants."""
    sub = cut.subgraph(scenario, "F-1")
    p0 = cut.plan_cut(scenario, sub)
    keep = keyword_baseline(explain_grant(scenario, p0.grants))
    assert sorted(keep) == sorted(expected()["F-1"]["keyword_baseline"]["keep"])
    kb = cut.what_if(scenario, sub, keep, "KB")
    assert kb.grants != expected()["F-1"]["P1"]["grants"]


@pytest.mark.db
def test_who_knows_top(scenario):
    top = who_knows(scenario, "role:deployer")[0]
    assert top["person_id"] == expected()["who_knows"]["role:deployer"]["top"]


@pytest.mark.db
def test_tool_guards(scenario):
    run = RunCtx()
    tools.call(scenario, run, "plan_cut", {"finding_id": "F-1"})
    r = tools.call(scenario, run, "what_if", {"keep": ["G-102"], "cites": ["G-102"]})
    assert not r["ok"] and "grant id alone" in r["error"]
    r = tools.call(scenario, run, "what_if", {"keep": ["G-102"], "cites": ["doc:dr-runbook"]})
    assert not r["ok"] and "not seen" in r["error"]           # must come from explain_grant first
    tools.call(scenario, run, "explain_grant", {"grant_ids": ["G-102", "G-103", "G-106"]})
    r = tools.call(scenario, run, "what_if", {"keep": ["G-102"], "cites": ["doc:dr-runbook"]})
    assert r["ok"] and [g["id"] for g in r["data"]["grants"]] == ["G-101", "G-106"]
    r = tools.call(scenario, run, "choose_plan", {"plan_id": "P1", "reason": "keeps DR"})
    assert not r["ok"]                                          # costlier without cites
    r = tools.call(scenario, run, "choose_plan", {"plan_id": "P1", "reason": "keeps DR", "cites": ["doc:dr-runbook"]})
    assert r["ok"] and r["data"]["severed"]
    r = tools.call(scenario, run, "ask_graph", {"cypher": "MATCH (n) DETACH DELETE n"})
    assert not r["ok"] and "read-only" in r["error"]
    r = tools.call(scenario, run, "ask_graph", {"cypher": "MATCH (g:Grant) RETURN g.id"})
    assert r["ok"] and r["data"]["truncated"] and len(r["data"]["rows"]) == 200
    run.what_if_count = 3
    r = tools.call(scenario, run, "what_if", {"keep": ["G-102"], "cites": ["doc:dr-runbook"]})
    assert not r["ok"] and "BudgetExceeded" in r["error"]
