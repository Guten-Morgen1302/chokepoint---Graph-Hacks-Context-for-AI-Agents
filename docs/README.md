# docs/: Chokepoint planning

Planning for the Graph Hacks build (FalkorDB, Oct 15–18 2026). **No code yet**: hackathon rule 8 doesn't allow any before the event starts.

## The idea in 30 seconds

A credential leaks. Chokepoint looks at the company's permission graph and finds every route to the crown-jewel systems. It then works out the **cheapest set of grants to revoke** using FalkorDB's `algo.maxFlow`.

The agent then **reads the company's tickets, chats and runbooks** to check whether that cheapest fix would break something. For example, a "dormant" grant might be the one the disaster-recovery failover needs. If so, it asks the graph for a different plan. When it has one, it **proves the attack is cut off** ("✓ Severed: 0 routes remain") and drafts tickets to the owners.

Your exceptions become memory. They carry a review date, they change the next answer, and they get flagged when the graph drifts.

**Tracks: all three.**

| Track | Fit |
|---|---|
| 01: Act on connected data | Strong |
| 02: Memory | Strong |
| 03: Company brain | Strong. This depends on the seed-time knowledge ingestion shipping. |

## Main files (read in this order)

| File | What it is |
|---|---|
| [PLAN.md](PLAN.md) | **The source of truth.** <br>• **Parts C2, B2 and A2** (at the end) are the round-2 design, eng and CEO reviews. <br>• **Part A2** (at the end) is CEO round 2. It covers the agent loop, the FalkorDB moat, the cost model, tie-breaks, the 3-minute video, Track 03 and the cut line, and **it overrides earlier parts where they conflict**. <br>• Part A: CEO round 1 (the pivot to attack paths). <br>• Part B: eng review (graph model, cut engine, tests, day plan). <br>• Part C: design review. |
| [DESIGN.md](DESIGN.md) | Visual system, plus the round-2 components (reasoning trail, severance line, provenance drawer, accept-risk form) |
| [TODOS.md](TODOS.md) | Deferred items: CUT-1…5, DR-TODO-1, K-1 |
| [hackathon-brief.md](hackathon-brief.md) | Dates, tracks, rules and submission checklist |
| [ENV_SETUP.md](ENV_SETUP.md) | **How to get every `.env` value** (Gemini key, FalkorDB Cloud, hosting) |

## History

| File | Stage |
|---|---|
| [history/01-office-hours-design-doc.md](history/01-office-hours-design-doc.md) | First design: an npm supply-chain agent. **Superseded.** |
| [history/02-office-hours-second-opinion.md](history/02-office-hours-second-opinion.md) | Cold read of the npm idea |
| [history/office-hours-spec-review/](history/office-hours-spec-review/) | Spec review rounds 1–2 for the office-hours doc |
| [history/03-ceo-review-outside-voice.md](history/03-ceo-review-outside-voice.md) | The critique that triggered the attack-path pivot |
| [history/04-eng-review-outside-voice.md](history/04-eng-review-outside-voice.md) | The critique that fixed the cut engine |
| [history/05-eng-review-test-plan.md](history/05-eng-review-test-plan.md) | QA test plan v2 (from round 2) |
| [history/09-eng-round2-outside-voice.md](history/09-eng-round2-outside-voice.md) | Eng round-2 critique: false-severed risk, citation guard, schedule |
| [history/10-design-round2-outside-voice.md](history/10-design-round2-outside-voice.md) | Design round-2 critique: overloaded strip, hero transition |
| [history/06-design-review-outside-voice.md](history/06-design-review-outside-voice.md) | Design critique |
| [history/07-ceo-round2-outside-voice.md](history/07-ceo-round2-outside-voice.md) | Round-2 critique: "the cost model cancels the agent" |
| [history/08-ceo-round2-scope-summary.md](history/08-ceo-round2-scope-summary.md) | Round-2 scope decisions (X-1…X-13) |

## Status (2026-10-02): built, not pushed

Planning is complete, with CEO, eng and design reviews all CLEAR.

The organisers confirmed by Discord and email that building may start now, and that Oct 15–18 is for showcase and submission. On that basis the app is **built and verified locally**. **Nothing has been pushed, and there is no git repo yet.** On Oct 15: run `git init`, push, and deploy.

### What works (verified on real FalkorDB)

| Check | Result |
|---|---|
| `pytest`: 122 tests | ✅ All pass: cut vs networkx, the Menger check, `cf` safety, the scenario, decisions, knowledge, tool guards, the agent loop with a stub LLM, the Gemini adapter against real `google-genai` types, and regressions for the 15 bug-hunt fixes |
| Seed + `expected.yaml` verification | ✅ P0 = {G-102, G-103, G-106} cost 5 · P1 = {G-101, G-106} cost 6 · keyword baseline is wrong (cost 8) |
| Web UI at 1440×900 | ✅ Triage, the attack graph, the cut, the proof, the provenance drawer (policy violation + runbook), accept risk → re-route, F-2 memory, drift → NEEDS REVIEW |
| MCP server | ✅ 11 tools. The full P0 → explain → what_if → P1 → severed flow works over MCP. |
| Docker image | ✅ Builds and serves `/healthz` |
| README queries section | ✅ 22 queries, generated and checked in CI |

### Not verified yet (needs your inputs)

| Item | Needs |
|---|---|
| The real **Gemini** agent loop (tested with a stub and with real SDK types, but not yet with a live model) | `GEMINI_API_KEY`, see [ENV_SETUP.md](ENV_SETUP.md) |
| `cli ingest` (Gemini extraction; the hand-written fallback edges are used today) | `GEMINI_API_KEY` |
| `cli eval -n 3`, the 3/3 gate before recording | `GEMINI_API_KEY` |
| Live deployment | FalkorDB Cloud credentials + a host (Render, Railway or Fly) |
| GitHub push | An empty public repo, on Oct 15 |

**How to read `PLAN.md`:** later parts override earlier ones. Precedence: **D (pre-freeze stress test) > C2 > B2 > A2 > C > B > A**.
