# TODOS

## Chokepoint (Graph Hacks)

These items were deferred by `/plan-ceo-review` on 2026-10-02 (SCOPE REDUCTION). For the full context, see `docs/PLAN.md` § 0G.

- [ ] **CUT-1: `@falkordb/mcpserver` as an extra MCP server (P3)**
  - **Why:** gives the agent ad-hoc Cypher beyond our pinned `ask_graph` tool.
  - **Cons:** it can read other visitors' graphs, and it's unclear whether its ACL works with a user that's limited to `GRAPH.RO_QUERY`.
  - **Effort:** human S / CC S.
  - **Depends on:** a per-visitor ACL, or a proxy that pins the graph.
- [ ] **CUT-2: centrality panel (P2, first stretch goal)**
  - PageRank and betweenness over the grant graph, showing "most dangerous groups/roles", labelled as structural hubs rather than cuts.
  - **Effort:** human S / CC S.
  - **Depends on:** Day 3 finishing early.
- [ ] **CUT-3: live IdP/cloud ingestion, Okta/AWS (P3)**
  - Post-hackathon only. Real identity data is not allowed under rule 6.
  - **Effort:** human L / CC M.
- [ ] **CUT-4: no-LLM button mode (P3)**
  - Lets the tools run as UI buttons when Claude is down. There are 11 tools after CEO round 2.
  - Partly covered by the CEO-5 deterministic fallback: P0 is shown labelled "Not reviewed by agent".
  - **Effort:** human S / CC S.
  - **Depends on:** the CEO-4 banner shipping first.
- [ ] **CUT-5: posting tickets to GitHub/Jira (P3)**
  - Today the tickets are drafts only. A stretch version would post them to a sandbox repo.
  - **Effort:** human S / CC S.
- [ ] **DR-TODO-1: Mockups for the triage screen (P2)**
  - **What:** once an OpenAI key is configured with `~/.claude/skills/gstack/design/dist/design setup`, generate mockups of the layout (DR-2), the hero (DR-3) and the visual tokens (DR-10).
  - **Why:** the design review was text-only, and visuals catch hierarchy problems that a text spec can't.
  - **Cons:** needs an API key and about 10 minutes.
  - **Context:** `docs/PLAN.md` Part C, and `DESIGN.md`.
  - **Depends on:** the key. Do it before the D3 web work.
- [ ] **K-1: ingest real public documents with GraphRAG-SDK (P3)**
  - **What:** replace or extend the seed-time `ingest_knowledge` extraction with FalkorDB's GraphRAG-SDK, running over real public docs such as open-source runbooks and RFCs.
  - **Why:** gives Track 03 a stronger "real ingestion" story than a synthetic corpus.
  - **Cons:** about 1.5 days of work. Extraction isn't deterministic, so the CI fixture check gets harder.
  - **Context:** deferred in `docs/PLAN.md` Part A2 (X-8). The X-11 seed-time extraction covers the hackathon need.
  - **Depends on:** X-11 shipping first.
