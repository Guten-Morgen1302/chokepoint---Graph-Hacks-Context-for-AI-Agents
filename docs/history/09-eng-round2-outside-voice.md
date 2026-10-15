# Eng review round 2: outside voice (gstack Claude runner, read-only)

This covers Part B2 of `docs/PLAN.md`. All 10 findings were accepted; see "Outside voice (eng round 2)" in Part B2.

Read `docs/PLAN.md` (Part B at 582–625, A2 at 1541–1620, B2 at 1929+). Findings B2's own review missed:

**1. verify's `cf=0` contradicts T4 probe 8 (P1).** ENG2-2 writes `cf=0` on plan edges, but probe 8's fallback says delete edges instead, "never needed for `cf`." It *is* needed — verify is the only severance proof. If 0-capacity edges error or are skipped, verify has no fallback. Specify it: probe 8 fallback must be "delete-in-lock for verify."

**2. E2-1's safety argument is sound only if BFS over-reports (P1).** Confining flow to reachable-source edges is correct for the flow *value* and for both residual cuts. But it inverts under an *under*-reporting BFS (probe 2 fails, or depth > 64 after the `grant-hr-payroll` event): a reachable edge without `cf`, if missing⇒0, yields `maxFlow(cf)=0` → **false SEVERED presented as proof**. Don't make probe 9's "write `cf` on all ATTACK edges" a fallback — adopt it for verify unconditionally. Cost is one wider UNWIND.

**3. The citation guard is simultaneously too strict and trivially satisfiable (P1).** `evidence_ids` is seeded from `plan_cut`, so any P0 grant id passes `check_cites` — the guard proves nothing about relevance. Worse, after `explain_grant`/`who_knows` the *injected message's own `source_id` is valid evidence*, so "ACCEPT_RISK needs cites" does not block E2-4's injection path. Conversely, a first `what_if` before `explain_grant` (unenforced, step 2) gets `ConstraintRejected` and burns budget. Fix: require ≥1 cite from a `:Doc`/`:Ticket`/`:Message` (not a grant id) for ACCEPT_RISK and overrides.

**4. Budgets are not controls (P2).** 10-min TTL + "no context ⇒ fresh one" means `what_if:3` and `tools:12` reset per session or on expiry. Fine for UX, not stated as such.

**5. The lock doesn't cover other processes (P2).** `asyncio.Lock` is in-process; `cli eval`/`cli ask` (D4, against the same graph) races the running web app on `cf`. Use a Redis `SET NX PX` lock keyed on graph name, or forbid CLI against a live graph.

**6. `verify_caps` vs crash recovery ordering (P2).** `verify_caps` "checks no `cf` remains" and runs *before every* `plan_cut`; leftover `cf` is cleared at the *start of the next locked section*. First request after a crash hard-fails. Order it: clear, then verify.

**7. Ingest CI treats extras as warnings (P2).** An extra `GOVERNS` edge changes `policy_status` output. Extras must hard-fail for `GOVERNS`, warn for `MENTIONS`. Also pin model id + prompt hash in `knowledge_edges.jsonl`, or regeneration silently drifts the fixture. And `expected.yaml` becoming a runtime fallback input (live ingest) leaks the test oracle into the product.

**8. Precedence lost two ENG-5 states (P2).** `WITHDRAWN` and "HOLDS (exposure shrank) + `removed`" are absent from ENG2-7's chain; the 9-row table can't cover 4 levels × 4 reason codes × co-occurrence (`grant_removed` + `source_removed`).

**9. Test gaps:** `what_if(keep)` infeasible → `maxFlow ≥ BIG` has no row, yet the ESCALATE eval depends on it; no `cf` clearing test when maxFlow itself raises; `test_whatif`'s 30 random graphs need the ENG-4 grant invariant and a shared ∞ sentinel with networkx, otherwise it's a second model implementation. Menger as `≤` is correct — keep it.

**10. D1/D2 are not buildable solo (P1).** D1 stacks the whole flow engine + generator v2 + YAML + LLM extractor + 6 test files. D2 stacks `runs`+`decisions`+`knowledge`+11 tools+FastMCP+agent+7-segment stub E2E ≈ two days. Checkpoint A will fire, and its remedy cuts the hero — which CEO-12 lists as never-cut. Move `cli ingest` and `knowledge` to D3, and pre-author YAML before Oct 15.

Recommendation: **Amend before building** because findings 1, 2, 3 and 10 are contract-level — verify can emit a false SEVERED proof and the citation guard doesn't close the injection path it is credited with, both cheap to fix on paper and expensive to discover on D2.