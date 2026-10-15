# Graph Hacks: Context for AI Agents (FalkorDB × WeMakeDevs)

Summarised from https://www.wemakedevs.org/hackathons/falkordb (overview, schedule, rules, resources, FAQ), read 2026-10-02. **Check the site for updates**: the organisers say the rules and schedule may change before the event starts.

## Dates

| | |
|---|---|
| **Hacking** | Oct 15, 12:01 AM IST → Oct 18, 11:59 PM IST, 2026. Online. |
| **Submissions close** | Oct 18, 11:59 PM IST |
| **Kickoff, FalkorDB workshop, office hours** | Dates TBA. They'll be announced on the page and in the FalkorDB Discord. |

Teams can be solo or up to 4 people, and each person can be on only one team.

## Tracks

You can enter more than one track. You must **name every track you're entering** when you submit.

| # | Track | Prize | Focus |
|---|---|---|---|
| 01 | Agents That Act on Connected Data | iPhone 18 Pro | Multi-hop reasoning, graph queries and algorithms as agent tools, choosing tools through MCP, taking actions based on what the graph shows, explainable results |
| 02 | Agent Memory and Coordination | PS5 + GTA VI | Episodic, semantic and procedural memory; persistent history; shared state and handoffs; heavy concurrent reads and writes; separate memory per user or tenant |
| 03 | Company Brain | M6 Mac Mini | Docs, tickets and chats in one graph; who owns what; tracing decisions back to their sources; keeping knowledge current; answers with sources |

**Side prizes:**
- AirPods 5 for each of the 5 best blog posts.
- A t-shirt for every member of the top 50 teams.

## Rules that shape the build

1. **FalkorDB must be the primary graph database** and must support a central part of what the product does.
2. **The graph has to do real work.** A visualisation drawn on top of ordinary storage doesn't qualify: if the product still works with FalkorDB taken out, it fails this rule.
3. You can run FalkorDB with Docker, self-hosted, or on FalkorDB Cloud. Any language or framework is fine.
4. **Data:** use only public, synthetic, or your own data. Nothing private, behind a login, paywalled, or personal.
5. **The main coding and design work must start after Oct 15, 12:01 AM IST.** Before that you may discuss ideas, take notes, sketch the graph model, and prepare diagrams.
6. Frameworks, libraries, public APIs, templates and public datasets are allowed. Only original work done during the hackathon is judged.

**The submission must include:**
- a public source-code repository
- a README with setup instructions
- the graph data model
- **the Cypher queries and graph algorithms the product depends on**
- a demo video of the working project
- a live deployment, or complete local setup instructions if it can't be deployed
- the track(s) you're entering

**AI coding assistants** are allowed, but you **must disclose** using them. You also have to be able to explain the graph model, the queries, the architecture and the decisions behind them. Projects generated entirely by AI, without meaningful contribution or understanding from the team, may be rejected.

The intellectual property belongs to the team. The WeMakeDevs Code of Conduct applies.

## Resources

| Resource | Link |
|---|---|
| Docs | https://docs.falkordb.com/ (getting started, Cypher, algorithms, clients, integrations) |
| GitHub | https://github.com/FalkorDB/FalkorDB |
| GraphRAG-SDK | https://github.com/FalkorDB/GraphRAG-SDK |
| MCP server | https://github.com/FalkorDB/FalkorDB-MCPServer (`npx -y @falkordb/mcpserver`) |
| FalkorDB Cloud | https://app.falkordb.cloud/ |
| Discord | https://discord.com/invite/Y2mMT9VdMy |
| Run locally | `docker pull falkordb/falkordb:latest` |

**Algorithms** (called with `CALL algo.*`): BFS, SPpath, SSpaths, A*, MSF, PageRank, betweenness, harmonic centrality, WCC, CDLP, and MaxFlow.
