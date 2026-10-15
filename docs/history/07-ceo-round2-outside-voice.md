# CEO review round 2: outside voice (gstack Claude runner, read-only)

This reviewed the **first draft** of Part A2. Each finding is resolved in `docs/PLAN.md` Part A2 under "Spec review and outside voice".

## Findings the first round missed

**1. CEO-7 kills CEO-5's demo.** The cost formula adds `4 × Σ criticality(dependents)`. So the min cut *already* avoids breaking critical services — that's the whole point of the term. But the video beat at 0:35 shows "Plan A cheapest (cost 3) breaks nightly-release ✗ → Plan B (cost 9) breaks nothing ✓." Under your own formula, a plan that breaks a crit-3 dependent carries +12, so B would be cheaper and the baseline would already be B. To film that beat you must rig fixtures so the cost ordering inverts, and the agent's "judgment" becomes "the cost model is wrong, override it." Pick one: breakage is in the cost (graph disposes, LLM is ornamental again) or it isn't (your hero number isn't business friction). Right now you've built both and they cancel. This is the single biggest hole.

**2. The tie-break is dead code in the demo.** ENG-4 (line 622) requires every cut in `expected.yaml` to be **unique** for reproducibility. Probing runs only when `unique=false`. So CEO-8's candidate set, "1 of 3 equally cheap plans," and `choose_plan` never fire in the recorded demo. Worse: the video's override is *not* an equal-cost tie-break (3 vs 9), and `choose_plan` is specced only for ties. And once the agent picks cost 9, the hero number announced at 0:35 ("cheapest fix, cost 4") is retracted on camera. Decide which number is the hero and announce it once.

**3. Agency defense: half-honest.** The constraint-translation claim is the right one, but X-8 deferral guts it. All "unstructured" context is pre-authored into typed `MENTIONS`/`GRANTED_VIA` edges — reading it is Cypher, not comprehension. The LLM's remaining job is argmax over ≤4 candidates, i.e. a for-loop. The firewall guards ("no citation, no constraint") are good and judges will like them, but they prove *safety*, not *necessity*. Shrink X-8 to S: LLM-extract 15–20 real artifacts (public GitHub issues) into the same schema at seed time, keep everything downstream deterministic. That's the only version where removing the LLM actually loses something.

**4. Moat claims 1, 2, 4 are soft; 3 is real and is on the cut line.** The rule-3 audit is circular — "without the graph DB you lose the graph DB calls." On ~400 nodes, in-process networkx beats you; claim 1 won't survive an expert. Claim 2 is false (Postgres also persists). Claim 4 is true of any graph DB. Only `GRAPH.COPY` multi-tenancy is FalkorDB-specific — and CEO-12 makes it cut item 5 while CEO-6 leans on it. Fix the ordering.

**5. Budget arithmetic.** ENG-14's 300 ms was for one maxFlow. You now have baseline + 3 probes + 4 `what_if` + verify = up to 9, plus `cf` property writes and `verify_caps` per `plan_cut`. "6 cuts in N ms" miscounts. Re-measure or restate.

**6. Video.** 8 beats / 180 s. The agent beat gets 40 s but the loop budget is 60 s — you'll trim away the thing you're proving. Provenance in 25 s is unreadable. Cut to 6 beats: drop Drift and Company-brain's `who_knows`; give the agent 55 s.

**7. Feasibility: no.** OVE-7 already called base scope 2× too big. D2 now holds decisions, caps, 11 tools, the agent loop, `what_if` + cleanup, `explain_grant`, `who_knows`, `choose_plan`, 5 test files and an 8-beat script. That's ~3 days. And "Never cut" protects every round-2 addition while sacrificing tenancy and Cytoscape — you've inverted the cut line.

**Track 03: decorative-leaning.** Hand-authored edges you then query. Policy-drift is the one genuine moment; keep it, call the track Medium, or do finding 3.

Recommendation: **send back for a scope-and-coherence pass before eng re-lock**, because the cost model and the agency loop currently cancel each other and the tie-break can't fire under ENG-4's uniqueness rule — building this as written produces a demo whose central beat contradicts its own math.