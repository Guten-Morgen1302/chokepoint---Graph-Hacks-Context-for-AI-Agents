"""Decision memory (Track 02): accepted risk becomes graph state that changes
the next computation, and is re-validated whenever the graph or calendar moves.

Precedence (ENG2-7 + OVE2-8):
  SUPERSEDED > WITHDRAWN > STALE (grant_removed | source_removed)
             > NEEDS_REVIEW (new_jewels | review_overdue) > HOLDS (plain | shrank)
Every applicable reason code is listed, not just the top one.
"""

from __future__ import annotations

import datetime as dt
import uuid

from . import BIG
from . import queries as Q
from .graphdb import TenantCtx

DISPOSITIONS = {"ACCEPT_RISK", "REVOKE_PLANNED"}


def _today() -> dt.date:
    return dt.date.today()


today = _today  # tests inject a clock by reassigning `decisions.today`


class DecisionError(ValueError):
    pass


def holder_jewels(ctx: TenantCtx, grant_id: str) -> list[str]:
    rows = Q.run(ctx.graph, "HOLDER_REACH", {"grant": grant_id}, ro=True, label="exception exposure")
    return sorted(set(rows[0][0])) if rows else []


def record_decision(ctx: TenantCtx, grant_id: str, disposition: str, rationale: str,
                    review_by: str | None, cites: list[str], by: str, *, confirmed: bool) -> dict:
    """Write a decision atomically with its capacity effect.

    An ACCEPT_RISK that is not `confirmed` (i.e. proposed by the agent) is
    returned as a draft and NOT written: a person must confirm it (OVE2-3).
    """
    if disposition not in DISPOSITIONS:
        raise DecisionError(f"disposition must be one of {sorted(DISPOSITIONS)}")
    if not rationale or not rationale.strip():
        raise DecisionError("rationale is required")
    if disposition == "ACCEPT_RISK" and not cites:
        raise DecisionError("Add at least one source.")
    if disposition == "ACCEPT_RISK" and not review_by:
        review_by = (today() + dt.timedelta(days=30)).isoformat()
    if review_by:
        try:
            rb = dt.date.fromisoformat(str(review_by))
        except ValueError as e:
            raise DecisionError("review_by must be YYYY-MM-DD") from e
        if rb <= today():
            raise DecisionError("Review date must be after today.")
        review_by = rb.isoformat()
    if not Q.run(ctx.graph, "GRANT_EXISTS", {"grant": grant_id}, ro=True):
        raise DecisionError(f"grant {grant_id} does not exist")
    existing = {r[0] for r in Q.run(ctx.graph, "EXISTING_IDS", {"ids": list(cites)}, ro=True)} if cites else set()
    missing = [c for c in cites if c not in existing]
    if missing:
        raise DecisionError(f"unknown sources: {missing}")
    draft = {"grant_id": grant_id, "disposition": disposition, "rationale": rationale.strip(),
             "review_by": review_by, "cites": list(cites), "by": by}
    if not confirmed:   # anything not confirmed by a person is only a proposal
        return {"status": "proposed", "draft": draft}
    did = f"D-{uuid.uuid4().hex[:8]}"
    baseline = holder_jewels(ctx, grant_id)
    Q.run(ctx.graph, "RECORD_DECISION", {
        "grant": grant_id, "did": did, "disp": disposition, "rationale": draft["rationale"],
        "review_by": review_by, "by": by, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "cites": list(cites), "baseline": baseline, "BIG": BIG}, label="record decision")
    if cites:
        Q.run(ctx.graph, "LINK_CITES", {"did": did, "cites": list(cites)})
    return {"status": "recorded", "id": did, **draft, "baseline_jewels": baseline}


def withdraw(ctx: TenantCtx, decision_id: str) -> None:
    Q.run(ctx.graph, "WITHDRAW_DECISION", {"did": decision_id, "BIG": BIG}, label="withdraw decision")


def evaluate(row: dict, exists: set[str], current_jewels: list[str] | None) -> dict:
    """Pure re-validation of one decision (unit-tested)."""
    reasons: list[str] = []
    if row["status"] == "SUPERSEDED":
        return {"badge": "SUPERSEDED", "reasons": ["superseded"]}
    if row["status"] == "WITHDRAWN":
        return {"badge": "WITHDRAWN", "reasons": ["withdrawn"]}
    stale = []
    if not row["grant_exists"]:
        stale.append("grant_removed")
    if any(c not in exists for c in row.get("cited_ids") or []):
        stale.append("source_removed")
    if stale:
        return {"badge": "STALE", "reasons": stale,
                "missing_sources": [c for c in row.get("cited_ids") or [] if c not in exists]}
    added = sorted(set(current_jewels or []) - set(row.get("baseline_jewels") or []))
    removed = sorted(set(row.get("baseline_jewels") or []) - set(current_jewels or []))
    if added:
        reasons.append("new_jewels")
    try:
        overdue = bool(row.get("review_by")) and dt.date.fromisoformat(str(row["review_by"])) < today()
    except ValueError:
        overdue = True   # unreadable date: ask for a review rather than crash recall
    if overdue:
        reasons.append("review_overdue")
    if reasons:
        return {"badge": "NEEDS_REVIEW", "reasons": reasons, "new_jewels": added}
    if removed:
        return {"badge": "HOLDS", "reasons": ["exposure_shrank"], "removed": removed}
    return {"badge": "HOLDS", "reasons": []}


def recall(ctx: TenantCtx, grant_ids: list[str] | None = None) -> list[dict]:
    rows = Q.run(ctx.graph, "ALL_DECISIONS", ro=True, label="recall decisions")
    decisions = []
    cited_all = sorted({c for r in rows for c in (r[8] or [])})
    exists = {r[0] for r in Q.run(ctx.graph, "EXISTING_IDS", {"ids": cited_all}, ro=True)} if cited_all else set()
    for r in rows:
        row = {"id": r[0], "grant_id": r[1], "disposition": r[2], "status": r[3], "rationale": r[4],
               "review_by": r[5], "by": r[6], "at": r[7], "cited_ids": r[8] or [], "baseline_jewels": r[9] or [],
               "grant_exists": bool(r[10])}
        if grant_ids and row["grant_id"] not in grant_ids:
            continue
        cur = holder_jewels(ctx, row["grant_id"]) if row["grant_exists"] and row["status"] == "ACTIVE" else None
        row.update(evaluate(row, exists, cur))
        decisions.append(row)
    return decisions


def verify_caps(ctx: TenantCtx) -> list:
    """Stored holds.cap must match the capacity rule (run after cf cleanup)."""
    return Q.run(ctx.graph, "VERIFY_CAPS", {"BIG": BIG}, ro=True)
