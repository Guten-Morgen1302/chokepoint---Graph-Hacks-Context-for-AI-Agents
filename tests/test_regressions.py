"""Regression tests for the bug-hunt fixes (2026-10-02)."""

import pytest

from chokepoint import decisions, tools
from chokepoint import queries as Q
from chokepoint.agent import run_agent
from chokepoint.llm import Call, Step, StubLLM
from chokepoint.runs import RunCtx

pytestmark = pytest.mark.db


def call(i, name, args):
    return Step(calls=[Call(f"t{i}", name, args)], stop="tool")


CHOOSE = [call(1, "explain_grant", {"grant_ids": ["G-102", "G-103", "G-106"]}),
          call(2, "what_if", {"keep": ["G-102"], "cites": ["doc:dr-runbook"]}),
          call(3, "choose_plan", {"plan_id": "P1", "reason": "keeps DR", "cites": ["doc:dr-runbook"]})]


def test_chosen_plan_survives_late_llm_error(scenario):
    ev = list(run_agent(scenario, RunCtx(), "F-1", llm=StubLLM(CHOOSE + [Step(stop="error", error="gemini 503")])))[-1]
    assert ev["status"] == "chosen" and ev["note"].startswith("explanations offline")
    assert [g["id"] for g in ev["plan"]["grants"]] == ["G-101", "G-106"]


def test_non_agent_tool_is_rejected(scenario):
    run = RunCtx()
    events = list(run_agent(scenario, run, "F-1", llm=StubLLM([call(1, "plan_cut", {"finding_id": "F-2"}), Step()])))
    t = [e for e in events if e["type"] == "tool"][0]
    assert not t["result"]["ok"] and run.finding == "F-1"


def test_agent_revoke_planned_is_only_a_proposal(scenario):
    run = RunCtx()
    tools.call(scenario, run, "plan_cut", {"finding_id": "F-1"})
    tools.call(scenario, run, "explain_grant", {"grant_ids": ["G-102"]})
    r = tools.call(scenario, run, "record_decision", {"grant_id": "G-102", "disposition": "REVOKE_PLANNED",
                                                      "rationale": "x", "cites": ["doc:dr-runbook"]})
    assert r["ok"] and r["data"]["status"] == "proposed"
    assert decisions.recall(scenario) == []


def test_bad_review_by_and_non_grant_rejected(scenario):
    with pytest.raises(decisions.DecisionError, match="YYYY-MM-DD"):
        decisions.record_decision(scenario, "G-102", "REVOKE_PLANNED", "x", "next week", [], "t", confirmed=True)
    with pytest.raises(decisions.DecisionError, match="does not exist"):
        decisions.record_decision(scenario, "doc:dr-runbook", "REVOKE_PLANNED", "x", None, [], "t", confirmed=True)


def test_unexpected_tool_error_is_structured_and_evidence_restored(scenario):
    parent = Q.start_evidence()
    r = tools.call(scenario, RunCtx(), "who_owns", {"node_ids": 12345})   # wrong type from a model
    assert not r["ok"] and r["error"]
    r = tools.call(scenario, RunCtx(), "nope", {})
    assert not r["ok"]
    assert Q._evidence.get() is parent


def test_ask_graph_records_evidence(scenario):
    parent = Q.start_evidence()
    tools.call(scenario, RunCtx(), "ask_graph", {"cypher": "MATCH (g:Grant) RETURN count(g)"})
    assert any(e.label == "ad-hoc" for e in parent)


def test_new_finding_resets_run(scenario):
    run = RunCtx()
    tools.call(scenario, run, "plan_cut", {"finding_id": "F-1"})
    tools.call(scenario, run, "explain_grant", {"grant_ids": ["G-102"]})
    assert "doc:dr-runbook" in run.evidence_types
    tools.call(scenario, run, "find_attack_paths", {"finding_id": "F-2"})
    assert run.plans == {} and "doc:dr-runbook" not in run.evidence_types


def test_cancel_stops_loop(scenario):
    import threading
    ev = threading.Event()
    ev.set()
    out = list(run_agent(scenario, RunCtx(), "F-1", llm=StubLLM(CHOOSE), cancel=ev))[-1]
    assert out["status"] == "fallback" and out["fallback"]["reason"] == "cancelled"


def test_scratch_graph_registered_and_dropped(template):
    from chokepoint.graphdb import copy_scratch, db, drop_scratch, is_scratch
    ctx = copy_scratch("cli_test_scratch")
    assert is_scratch("cli_test_scratch")
    drop_scratch(ctx.graph_name)
    assert "cli_test_scratch" not in db().list_graphs() and not is_scratch("cli_test_scratch")


def test_plan_view_names_kept_grants(scenario):
    run = RunCtx()
    tools.call(scenario, run, "plan_cut", {"finding_id": "F-1"})
    tools.call(scenario, run, "explain_grant", {"grant_ids": ["G-102"]})
    r = tools.call(scenario, run, "what_if", {"keep": ["G-102"], "cites": ["doc:dr-runbook"]})
    assert [g["id"] for g in r["data"]["kept_grants"]] == ["G-102"]
    assert "prod-customers-db" in r["data"]["kept_grants"][0]["name"]
