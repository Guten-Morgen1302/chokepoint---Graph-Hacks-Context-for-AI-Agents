"""MCP server exposing the same 11 tool functions (Track 01: tool selection
through MCP). Plug it into any MCP client (Claude Desktop, Claude Code, Gemini CLI, Cursor):

    python -m chokepoint.cli mcp            # stdio
    python -m chokepoint.cli mcp --http     # streamable HTTP on :8765/mcp

External MCP clients work on their own copy of the template graph
(`mcp_<pid>`), so they can run counterfactuals without touching visitors.
"""

from __future__ import annotations

import atexit
import json
import os

from mcp.server.mcpserver import MCPServer

from . import tools
from .graphdb import TenantCtx, copy_scratch, drop_scratch
from .runs import RunCtx

_state: dict = {}


def _ctx() -> tuple[TenantCtx, RunCtx]:
    if "ctx" not in _state:
        name = f"mcp_{os.getpid()}"
        _state["ctx"] = copy_scratch(name)
        _state["run"] = RunCtx()
        atexit.register(drop_scratch, name)
    return _state["ctx"], _state["run"]


def _call(name: str, args: dict) -> str:
    ctx, run = _ctx()
    if name in ("find_attack_paths", "plan_cut") and args.get("finding_id") != run.finding:
        _state["run"] = run = RunCtx()         # a new finding starts a fresh run
    res = tools.call(ctx, run, name, args)
    return json.dumps({k: res[k] for k in ("ok", "data", "error", "ms")}, default=str)


def build() -> MCPServer:
    m = MCPServer("chokepoint", instructions="Identity attack-path triage on FalkorDB. Start with "
                  "find_attack_paths, then plan_cut, explain_grant, what_if and choose_plan.")
    d = {n: t.description for n, t in tools.TOOLS.items()}

    @m.tool(name="find_attack_paths", description=d["find_attack_paths"])
    def find_attack_paths(finding_id: str) -> str:
        return _call("find_attack_paths", {"finding_id": finding_id})

    @m.tool(name="plan_cut", description=d["plan_cut"])
    def plan_cut(finding_id: str) -> str:
        return _call("plan_cut", {"finding_id": finding_id})

    @m.tool(name="what_if", description=d["what_if"])
    def what_if(keep: list[str], cites: list[str]) -> str:
        return _call("what_if", {"keep": keep, "cites": cites})

    @m.tool(name="choose_plan", description=d["choose_plan"])
    def choose_plan(plan_id: str, reason: str, cites: list[str] | None = None) -> str:
        return _call("choose_plan", {"plan_id": plan_id, "reason": reason, "cites": cites or []})

    @m.tool(name="explain_grant", description=d["explain_grant"])
    def explain_grant(grant_ids: list[str]) -> str:
        return _call("explain_grant", {"grant_ids": grant_ids})

    @m.tool(name="who_owns", description=d["who_owns"])
    def who_owns(node_ids: list[str]) -> str:
        return _call("who_owns", {"node_ids": node_ids})

    @m.tool(name="who_knows", description=d["who_knows"])
    def who_knows(node_id: str) -> str:
        return _call("who_knows", {"node_id": node_id})

    @m.tool(name="record_decision", description=d["record_decision"])
    def record_decision(grant_id: str, disposition: str, rationale: str,
                        review_by: str | None = None, cites: list[str] | None = None) -> str:
        return _call("record_decision", {"grant_id": grant_id, "disposition": disposition,
                                         "rationale": rationale, "review_by": review_by, "cites": cites or []})

    @m.tool(name="recall_decisions", description=d["recall_decisions"])
    def recall_decisions(grant_ids: list[str] | None = None) -> str:
        return _call("recall_decisions", {"grant_ids": grant_ids})

    @m.tool(name="draft_tickets", description=d["draft_tickets"])
    def draft_tickets(plan_id: str, context_note: str = "") -> str:
        return _call("draft_tickets", {"plan_id": plan_id, "context_note": context_note})

    @m.tool(name="ask_graph", description=d["ask_graph"])
    def ask_graph(cypher: str) -> str:
        return _call("ask_graph", {"cypher": cypher})

    return m
