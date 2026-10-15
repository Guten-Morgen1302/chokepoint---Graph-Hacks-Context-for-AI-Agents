import datetime as dt

import pytest

from chokepoint import BIG, cut, decisions
from chokepoint.scenario.events import apply_event


def row(**kw):
    base = {"status": "ACTIVE", "grant_exists": True, "cited_ids": ["doc:x"], "baseline_jewels": ["j1"], "review_by": None}
    base.update(kw)
    return base


@pytest.mark.parametrize("r,exists,cur,badge,reasons", [
    (row(status="SUPERSEDED"), {"doc:x"}, ["j1"], "SUPERSEDED", ["superseded"]),
    (row(status="WITHDRAWN"), {"doc:x"}, ["j1"], "WITHDRAWN", ["withdrawn"]),
    (row(grant_exists=False), {"doc:x"}, None, "STALE", ["grant_removed"]),
    (row(), set(), ["j1"], "STALE", ["source_removed"]),
    (row(grant_exists=False), set(), None, "STALE", ["grant_removed", "source_removed"]),
    (row(), {"doc:x"}, ["j1", "j2"], "NEEDS_REVIEW", ["new_jewels"]),
    (row(review_by="2000-01-01"), {"doc:x"}, ["j1"], "NEEDS_REVIEW", ["review_overdue"]),
    (row(review_by="2000-01-01"), {"doc:x"}, ["j1", "j2"], "NEEDS_REVIEW", ["new_jewels", "review_overdue"]),
    (row(baseline_jewels=["j1", "j2"]), {"doc:x"}, ["j1"], "HOLDS", ["exposure_shrank"]),
    (row(), {"doc:x"}, ["j1"], "HOLDS", []),
])
def test_precedence_table(r, exists, cur, badge, reasons):
    out = decisions.evaluate(r, exists, cur)
    assert out["badge"] == badge
    assert out["reasons"] == reasons


@pytest.mark.db
def test_accept_risk_changes_capacity_and_plan(scenario):
    res = decisions.record_decision(scenario, "G-102", "ACCEPT_RISK", "DR needs it", "2099-01-01",
                                    ["doc:dr-runbook"], "test", confirmed=True)
    assert res["status"] == "recorded"
    cap = scenario.graph.query("MATCH ()-[r:ATTACK {kind:'holds'}]->(:Grant {id:'G-102'}) RETURN r.cap").result_set[0][0]
    assert cap == BIG
    assert decisions.verify_caps(scenario) == []
    p = cut.plan_cut(scenario, cut.subgraph(scenario, "F-1"))
    assert "G-102" not in p.grants and p.grants == ["G-101", "G-106"]


@pytest.mark.db
def test_agent_proposal_is_not_written(scenario):
    res = decisions.record_decision(scenario, "G-102", "ACCEPT_RISK", "maybe", "2099-01-01",
                                    ["doc:dr-runbook"], "agent", confirmed=False)
    assert res["status"] == "proposed"
    assert decisions.recall(scenario) == []


@pytest.mark.db
def test_validation(scenario):
    with pytest.raises(decisions.DecisionError, match="source"):
        decisions.record_decision(scenario, "G-102", "ACCEPT_RISK", "x", "2099-01-01", [], "t", confirmed=True)
    with pytest.raises(decisions.DecisionError, match="after today"):
        decisions.record_decision(scenario, "G-102", "ACCEPT_RISK", "x", "2000-01-01", ["doc:dr-runbook"], "t", confirmed=True)
    with pytest.raises(decisions.DecisionError, match="does not exist"):
        decisions.record_decision(scenario, "G-999", "REVOKE_PLANNED", "x", None, [], "t", confirmed=True)


@pytest.mark.db
def test_supersede_and_events(scenario):
    decisions.record_decision(scenario, "G-102", "ACCEPT_RISK", "first", "2099-01-01", ["doc:dr-runbook"], "t", confirmed=True)
    decisions.record_decision(scenario, "G-102", "ACCEPT_RISK", "second", "2099-01-01", ["SEC-488"], "t", confirmed=True)
    badges = sorted(d["badge"] for d in decisions.recall(scenario))
    assert badges == ["HOLDS", "SUPERSEDED"]
    apply_event(scenario, "grant-hr-payroll")
    active = [d for d in decisions.recall(scenario) if d["status"] == "ACTIVE"][0]
    assert active["badge"] == "NEEDS_REVIEW" and active["new_jewels"] == ["db:hr-payroll-db"]
    apply_event(scenario, "decommission-dr-grant")
    active = [d for d in decisions.recall(scenario) if d["status"] == "ACTIVE"][0]
    assert active["badge"] == "STALE" and "grant_removed" in active["reasons"]


@pytest.mark.db
def test_review_overdue_with_injected_clock(scenario, monkeypatch):
    decisions.record_decision(scenario, "G-102", "ACCEPT_RISK", "x", "2099-01-01", ["doc:dr-runbook"], "t", confirmed=True)
    monkeypatch.setattr(decisions, "today", lambda: dt.date(2100, 1, 1))
    d = decisions.recall(scenario)[0]
    assert d["badge"] == "NEEDS_REVIEW" and d["reasons"] == ["review_overdue"]
