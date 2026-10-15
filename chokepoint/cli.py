"""Command line: seed | ask | ingest | queries | mcp | sweep | eval

    python -m chokepoint.cli seed               build + verify the template graph
    python -m chokepoint.cli ask F-1 [--no-llm] run triage end to end in the terminal
    python -m chokepoint.cli ingest             LLM extraction → knowledge_edges.jsonl (needs GEMINI_API_KEY)
    python -m chokepoint.cli queries --markdown print every Cypher query (README section)
    python -m chokepoint.cli mcp [--http]       MCP server
    python -m chokepoint.cli eval [-n 3]        real-model eval: agent must keep only G-102
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _cli_ctx():
    """The CLI never touches a live graph: it works on its own copy (OVE2-5)."""
    from .graphdb import copy_scratch
    from .scenario.seed import ensure_template

    ensure_template()
    return copy_scratch(f"cli_{os.getpid()}")


def _drop(ctx):
    from .graphdb import drop_scratch
    drop_scratch(ctx.graph_name)


def cmd_seed(a):
    from .scenario.seed import seed
    print(json.dumps(seed(), indent=2))


def cmd_ask(a):
    from .agent import run_agent
    from .runs import RunCtx

    ctx = _cli_ctx()
    try:
        for ev in run_agent(ctx, RunCtx(), a.finding, a.question, use_llm=not a.no_llm):
            if ev["type"] == "baseline":
                b = ev["data"]
                print("PATHS:", json.dumps(b["paths"]["data"], indent=1))
                print("P0:   ", json.dumps(b["p0"]["data"], indent=1))
            elif ev["type"] == "tool":
                r = ev["result"]
                print(f"→ {ev['name']}({json.dumps(ev['input'])[:160]}) ok={r['ok']} {r['error'] or ''}")
            else:
                print("FINAL:", json.dumps(ev, indent=1, default=str))
    finally:
        _drop(ctx)


def cmd_ingest(a):
    from .knowledge import ingest_knowledge
    from .llm import provider_ready

    if not provider_ready():
        sys.exit("set GEMINI_API_KEY (or LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY) in .env first")
    out = Path(__file__).parent / "scenario" / "knowledge_edges.jsonl"
    print(json.dumps(ingest_knowledge(out), indent=2))
    print("Now re-seed: python -m chokepoint.cli seed")


def cmd_queries(a):
    from .queries import all_queries
    for name, cy, doc in all_queries():
        if a.markdown:
            print(f"### `{name}`\n")
            if doc:
                print(doc + "\n")
            print(f"```cypher\n{cy}\n```\n")
        else:
            print(name)


def cmd_mcp(a):
    from .mcp_server import build
    m = build()
    if a.http:
        import asyncio
        asyncio.run(m.run_streamable_http_async())
    else:
        m.run()


def cmd_sweep(a):
    from .graphdb import sweep
    print(sweep())


def cmd_eval(a):
    """Gate before recording the video (SD-3): N real-model runs on F-1."""
    from .agent import run_agent
    from .llm import provider_ready
    from .runs import RunCtx

    if not provider_ready():
        sys.exit("set GEMINI_API_KEY in .env first")
    hits = 0
    for i in range(a.n):
        if i and a.pause:
            time.sleep(a.pause)   # free-tier Gemini keys allow only a few requests per minute
        ctx = _cli_ctx()
        try:
            final = [e for e in run_agent(ctx, RunCtx(), "F-1") if e["type"] == "final"][0]
            plan = (final.get("plan") or {}).get("grants") or []
            ids = sorted(g["id"] for g in plan)
            ok = (final.get("status") == "chosen" and ids == ["G-101", "G-106"]
                  and "doc:dr-runbook" in (final.get("cites") or [])
                  and not {"doc:deploy-runbook", "doc:inc-2291", "doc:onboarding", "msg:po-inj"} & set(final.get("cites") or []))
            hits += ok
            print(f"run {i + 1}: {'PASS' if ok else 'FAIL'} status={final.get('status')} plan={ids} cites={final.get('cites')}")
        finally:
            _drop(ctx)
    print(f"hit rate: {hits}/{a.n}")
    sys.exit(0 if hits == a.n else 1)


def main(argv=None):
    p = argparse.ArgumentParser(prog="chokepoint")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("seed").set_defaults(fn=cmd_seed)
    s = sp.add_parser("ask"); s.add_argument("finding"); s.add_argument("question", nargs="?")
    s.add_argument("--no-llm", action="store_true"); s.set_defaults(fn=cmd_ask)
    sp.add_parser("ingest").set_defaults(fn=cmd_ingest)
    s = sp.add_parser("queries"); s.add_argument("--markdown", action="store_true"); s.set_defaults(fn=cmd_queries)
    s = sp.add_parser("mcp"); s.add_argument("--http", action="store_true"); s.set_defaults(fn=cmd_mcp)
    sp.add_parser("sweep").set_defaults(fn=cmd_sweep)
    s = sp.add_parser("eval"); s.add_argument("-n", type=int, default=3)
    s.add_argument("--pause", type=float, default=30, help="seconds between runs"); s.set_defaults(fn=cmd_eval)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
