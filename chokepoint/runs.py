"""Run context: plan registry, evidence ids and the citation guard (ENG2-3).

The citation guard is the hallucination firewall: an LLM-proposed constraint
or override must cite at least one Doc/Ticket/Message that explain_grant
actually returned in THIS run (OVE2-3). Grant ids alone prove nothing.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .cut import Plan, Sub

TEXT_TYPES = {"Doc", "Ticket", "Message"}


class ConstraintRejected(Exception):
    pass


class BudgetExceeded(Exception):
    pass


@dataclass
class RunCtx:
    finding: str | None = None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    started: float = field(default_factory=time.time)
    sub: Sub | None = None
    plans: dict[str, Plan] = field(default_factory=dict)
    evidence_types: dict[str, str] = field(default_factory=dict)
    chosen: str | None = None
    choose_reason: str | None = None
    choose_cites: list[str] = field(default_factory=list)
    what_if_count: int = 0
    tool_count: int = 0
    trail: list[dict] = field(default_factory=list)
    proposals: list[dict] = field(default_factory=list)
    deadline_s: float = 60.0
    max_what_if: int = 3
    max_tools: int = 12

    def reset_for(self, finding: str) -> None:
        self.finding, self.sub, self.chosen = finding, None, None
        self.plans.clear()
        self.evidence_types.clear()
        self.what_if_count = 0
        self.choose_reason, self.choose_cites = None, []

    def register(self, node_id: str, node_type: str) -> None:
        self.evidence_types.setdefault(node_id, node_type)

    def cheapest(self) -> Plan | None:
        return self.plans.get("P0")

    def next_plan_id(self) -> str:
        return f"P{len(self.plans)}"


def check_cites(run: RunCtx, cites: list[str] | None) -> None:
    cites = list(cites or [])
    if not cites:
        raise ConstraintRejected("no source cited")
    unknown = [c for c in cites if c not in run.evidence_types]
    if unknown:
        raise ConstraintRejected(f"cited source not seen in this run: {', '.join(unknown)}")
    if not any(run.evidence_types[c] in TEXT_TYPES for c in cites):
        raise ConstraintRejected("cite at least one doc, ticket or message (a grant id alone proves nothing)")


def check_keep(run: RunCtx, keep: list[str]) -> None:
    in_plans = {g for p in run.plans.values() for g in p.grants + (p.alt_grants or [])}
    bad = [g for g in keep if g not in in_plans]
    if bad:
        raise ConstraintRejected(f"can only keep grants that appear in a plan: {', '.join(bad)}")
