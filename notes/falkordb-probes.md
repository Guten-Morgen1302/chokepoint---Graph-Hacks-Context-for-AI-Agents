# FalkorDB probes (T4): results

- **When and where:** run 2026-10-02 against `falkordb/falkordb:latest` (graph module 6.0.1) in Docker, on port 6390.
- **Client:** `falkordb` Python 1.7.1.

| # | Probe | Result | Consequence for the build |
|---|---|---|---|
| 1 | maxFlow on the 3-node docs example | maxFlow = 13. `edgeFlows` returns A→B 8, A→C 5 and B→C 8, exactly as documented. Took 0.67 ms. | Cut engine works as planned |
| 1b | Multiple sinks (`targetNodes:[B,C]`) | maxFlow = 15 | The built-in virtual super-sink works (SD-1) |
| 2 | Is `algo.bfs` directed? | From A in `D→A→B→C` it returns `[B, C]`. D is not included (directed), and **the start node is not included either**. | Add the finding node to the BFS node set ourselves |
| 2b | BFS edges on a diamond A→B, A→C, B→D, C→D | 3 nodes, **3 edges** (4 exist), so they are **tree edges only** | Confirms OVE-1. Use BFS `nodes` only, then fetch the induced edges. |
| 3 | `GRAPH.COPY` and `GRAPH.MEMORY USAGE` | Both work | Per-visitor tenancy can use `GRAPH.COPY` |
| 4 | `GRAPH.RO_QUERY … TIMEOUT 2000` | Works. A write returns "graph.RO_QUERY is to be executed only on read-only queries". | `ask_graph` can use RO_QUERY |
| 5 | Relationship-property index | `CREATE INDEX FOR ()-[r:PIPE]-() ON (r.cap)` creates it | OK |
| 6 | Plain Redis keys (`ZADD`, `SET NX EX`) next to graphs | Work | Tenancy metadata can live in plain keys |
| 7 | Custom `capacityProperty:'cf'` | maxFlow = 13 | A per-run `cf` property works |
| 8 | Every edge has `cf = 0` | maxFlow = 0, no edges, no error | The verify step can use capacity 0 |
| **9** | Some edges missing the capacity property | **Error:** `algo.maxFlow: invalid or missing attribute and no default attribute specified`. This happens **even when the edge is unreachable**. | `cf` (and `cap`, `unit`) **must exist on every edge of the relationship type**. ENG2-2's "write cf on all ATTACK edges" is **required**, not optional. |
| 10 | Write atomicity when the client is killed | Not run (the session was interrupted) | I1, overwrite before read, makes this irrelevant to correctness |

## Python client notes

- Set up the graph with `FalkorDB(host, port).select_graph(name)`.
- Query methods: `.query(q, params, timeout)`, `.ro_query(...)` and `.copy(clone)`.
- `id(node)` / `id(edge)` return integers.
- A `maxFlow` result arrives as `[[ [src,dst,eid]... ], [flows...], maxFlow]`, with flows as floats.
