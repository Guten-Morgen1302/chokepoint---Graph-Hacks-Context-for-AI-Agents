# Office hours: second opinion (Claude subagent, 2026-10-02)

This is a cold read of the **original npm supply-chain idea**. That idea was replaced by the attack-path pivot during the CEO review; see `docs/PLAN.md` Part A, decision CEO-1b.

## 1. The coolest version they haven't considered

Make "Chokepoint" a literal min-cut, and add a replay of a real incident.

- **Min-cut upgrade planner.** Treat "every service → dependency paths → vulnerable package version" as a flow network. Run `algo.MaxFlow` to get the minimum cut: the smallest set of direct-dependency bumps that cuts every service off from the vulnerability. Upgrades happen at direct-dependency edges, so the cut should be modelled on those edges. MaxFlow cuts edges, not nodes, so a node cut needs each node split in two. This fits on one slide, and SQL can't do it.
- **Replay a real incident.** Pin 5 repos to tags from just before a known incident: Dec 2021 (Log4Shell era), Mar 2024 (xz / CVE-2024-3094), or for npm specifically the event-stream or `ua-parser-js` hijacks. Then ask the agent "It's Dec 10, 2021. What do we do?" and have it show the paths, the min cut and the drafted team issues.
- **Maintainer bus factor (optional, but high wow).** Add `Package -MAINTAINED_BY-> Maintainer` and run betweenness or PageRank. That answers "which single unpaid maintainer, if compromised, reaches the most services", which is the xz lesson asked before any CVE exists.

## 2. The one thing that reveals what wins

Two rules together: "the graph must do real work; a visualisation on top of ordinary storage doesn't qualify", and the requirement to submit the Cypher queries and algorithms the product depends on. Judges will open the README's query list and ask "could this be a SQL join?" Win by having 2–3 queries that can't be done that way: variable-length paths, MaxFlow, and centrality. Use FalkorDB's own `algo.*` procedures and its MCP server; sponsors reward showcases of their own features.

## 3. Open source that gets you halfway

- **osv-scanner** (or the `api.osv.dev/v1/querybatch` endpoint) maps lockfile packages to vulnerabilities and fixed versions.
- **deps.dev API** returns resolved dependency graphs.
- **OpenSSF GUAC** is literally a supply-chain graph. Cite it as prior art; don't adopt it.

The half you'd build yourself: the FalkorDB schema and loader, the min-cut and centrality queries, typed MCP tools, the agent that explains paths, decision memory, and issue drafting.

## 4. Weekend build order

**Stack:** Python with falkordb-py, FalkorDB in Docker locally and FalkorDB Cloud for the live demo, and Claude with 5–6 typed custom tools. Use typed tools, not free text-to-Cypher. Keep `@falkordb/mcpserver` as an extra tool for ad-hoc questions. A small Next.js or Streamlit UI that renders paths.

**Data:** npm only. Use 5 real repos at old tags, chosen so that known vulnerabilities actually show up in their `package-lock.json`. Add synthetic Team/Owner nodes.

**Order:**

1. Loader
2. `MATCH p=(s:Service)-[:DEPENDS_ON*1..10]->(:PackageVersion)<-[:AFFECTS]-(v:Vuln {id:$cve})`
3. MaxFlow min-cut planner
4. Notify-owners query
5. Decision nodes and recall
6. Agent
7. Issue drafts
8. Video

**Skip:** Graphiti/Cognee, multi-agent, multiple ecosystems, live ingestion, auth, and semver range solving. Use OSV's fixed versions directly.

**Rules flag:** "complete pipeline before Oct 15" conflicts with "main coding must begin after Oct 15", and repo timestamps are public. Before Oct 15, limit yourself to sketching the schema, drafting queries in notes, picking repos and tags, and downloading raw data. Write no product code.

## 5. Biggest risk

It could read as "Dependabot / npm audit with a chat box". Single-repo "are we exposed to CVE X" is already solved, so if the demo leads with that, judges conclude the graph isn't needed. The hero moment has to be the cross-service min-cut upgrade plan plus "here's why last week's decision still holds", with the Cypher and algorithm on screen.

The second risk is correctness. A wrong fixed version or a missed transitive path in a live demo kills credibility, so use only repos and CVEs you have checked by hand.

**Recommendation:** build Chokepoint npm-only, with a replay of a real historical incident and the MaxFlow min-cut as the hero query. The judging rule rewards a graph doing work that SQL and Dependabot can't, and a cross-service minimum-upgrade cut is the clearest proof of that. Write no product code until Oct 15.

> **What happened next:** the spec review and the CEO review both found that a dependency-graph min-cut is trivial under real npm remediation rules, so the project pivoted to identity attack paths.
