# Design review round 2: outside voice (Claude design subagent)

This review covers the round-2 UI additions. All 7 findings were accepted as decisions DR2-1 … DR2-7, recorded in `docs/PLAN.md` Part C2.

| # | Severity | Finding | Fix (decision) |
|---|---|---|---|
| 1 | Critical | The answer strip holds about 12 lines, which squeezes the graph. The trail also contradicts DR-5's "never above the answer". | A 4-slot strip capped at 200px, plus an "Agent review" section in the rail. Narrative removed. (DR2-1) |
| 2 | Critical | The hero going from cost 3 to cost 5 reads as the result getting worse | The interim value is muted and labelled `Cheapest:`. The final value is ink and labelled `Agent's plan:`. The causal "why" line names what the extra cost saves. No count-up animation. (DR2-2) |
| 3 | High | ✗ has three meanings, ▲ is used for both the policy violation and NEEDS REVIEW, and ✓/✗ aren't on the allow-list | A glyph/token map with no collisions; policy violation becomes ■ `--danger` (DR2-4) |
| 4 | High | States and copy missing: escalate, fallback reasons, budget, does-not-sever, live ingest, form errors | State matrix with final copy (DR2-3) |
| 5 | High | No styling defined for the proof line or citations | Type-prefixed citation links; the drawer opens on the quoted evidence; the proof line links to the evidence drawer (DR2-5) |
| 6 | High | The agent-proposed acceptance has no visual treatment | Inline row with a `--warn` rule, "Proposed by agent · not saved", and Confirm / Discard buttons. No graph change until the user confirms. (DR2-6) |
| 7 | Medium | Accessibility of the streaming trail, drawer, chips and tooltip | Trail is `role=log` and appends one line per plan. The hero announces after the trail. Drawer focus rules. Chip combobox. Cost breakdown shown inline instead of on hover. (DR2-7) |

**Litmus, before → after:** one visual anchor: NO → YES. Scannable by headings: NO → YES. Each section has one job: NO → YES.
