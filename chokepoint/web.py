"""FastAPI web app: one page, SSE triage stream, decisions, scenario events.

The answer card is rendered from tool JSON by the browser (ENG-8); the LLM
only writes the short narrative. Graph names come only from the signed
visitor cookie, never from the client (S3-1).
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import graphdb, tools
from .agent import run_agent
from .config import settings
from .decisions import DecisionError, record_decision, recall
from .graphdb import GraphUnavailable, TenantCtx
from .llm import provider_ready
from .queries import start_evidence
from .runs import RunCtx
from .scenario.events import ScenarioEventRejected, apply_event, applied
from .scenario.seed import ensure_template

HERE = Path(__file__).parent
COOKIE = "cp_vid"
app = FastAPI(title="Chokepoint")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

_spend = {"day": time.strftime("%Y-%m-%d"), "runs": 0}
_visitor_runs: dict[str, list[float]] = {}


@app.on_event("startup")
def _startup():
    try:
        ensure_template()
    except Exception as e:  # FalkorDB down at boot: /healthz shows red
        print("template not ready:", e)

    def sweeper():
        while True:
            try:
                graphdb.sweep()
            except Exception:
                pass
            time.sleep(300)
    threading.Thread(target=sweeper, daemon=True).start()


def _visitor(request: Request) -> tuple[str, bool]:
    vid = graphdb.verify(request.cookies.get(COOKIE))
    if vid:
        return vid, False
    return graphdb.new_visitor_id(), True


def _tenant(request: Request) -> tuple[TenantCtx, str, bool]:
    vid, new = _visitor(request)
    ip = request.client.host if request.client else "?"
    ctx = graphdb.ensure_visitor_graph(vid, ip)
    graphdb.touch(ctx)
    return ctx, vid, new


def _with_cookie(resp, vid: str, new: bool):
    if new:
        resp.set_cookie(COOKIE, graphdb.sign(vid), httponly=True, samesite="lax", max_age=86400)
    return resp


def _llm_allowed(vid: str) -> bool:
    now = time.time()
    day = time.strftime("%Y-%m-%d")
    if _spend["day"] != day:
        _spend.update(day=day, runs=0)
    runs = [t for t in _visitor_runs.get(vid, []) if t > now - 3600]
    if _spend["runs"] >= settings.llm_runs_per_day or len(runs) >= settings.llm_runs_per_visitor_hour:
        return False
    runs.append(now)
    _visitor_runs[vid] = runs
    _spend["runs"] += 1
    return True


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    html = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
    try:
        ctx, vid, new = _tenant(request)
        state = {"readonly": ctx.readonly, "graph": "private copy" if not ctx.readonly else "shared read-only"}
    except Exception as e:   # FalkorDB down / no template: show the banner, not a blank 500
        return HTMLResponse(html.replace("__BOOT__", json.dumps({"error": f"{type(e).__name__}: {e}"})))
    resp = HTMLResponse(html.replace("__BOOT__", json.dumps(state)))
    return _with_cookie(resp, vid, new)


@app.get("/api/findings")
def findings(request: Request):
    ctx, vid, new = _tenant(request)
    rows = ctx.graph.ro_query("MATCH (f:Finding) RETURN f.id, f.title, f.severity, f.at ORDER BY f.at").result_set
    resp = JSONResponse({"findings": [{"id": r[0], "title": r[1], "severity": r[2], "at": r[3]} for r in rows],
                         "applied_events": applied(ctx)})
    return _with_cookie(resp, vid, new)


@app.get("/api/triage")
async def triage(request: Request, finding: str, q: str | None = None):
    ctx, vid, new = await run_in_threadpool(_tenant, request)
    use_llm = provider_ready() and not ctx.readonly and _llm_allowed(vid)   # charge only real LLM runs
    reason = "explanations offline (no API key)" if not provider_ready() else "demo budget reached"
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    cancel = threading.Event()

    def worker():
        ev_all = start_evidence()
        try:
            for ev in run_agent(ctx, RunCtx(), finding, q, use_llm=use_llm, offline_reason=reason, cancel=cancel):
                ev["evidence"] = [e.__dict__ for e in ev_all][-60:]
                if q:
                    ev["question"] = q
                loop.call_soon_threadsafe(queue.put_nowait, ev)
                if cancel.is_set():
                    break
        except GraphUnavailable as e:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "final", "status": "error", "error": f"graph unavailable: {e}"})
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "final", "status": "error", "error": f"{type(e).__name__}: {e}"})
        loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=worker, daemon=True).start()

    async def stream():
        try:
            while True:
                ev = await queue.get()
                if ev is None:
                    break
                yield f"data: {json.dumps(ev, default=str)}\n\n"
        finally:
            cancel.set()   # client went away (or stream ended): stop the agent loop

    resp = StreamingResponse(stream(), media_type="text/event-stream")
    return _with_cookie(resp, vid, new)


@app.get("/api/source/{source_id}")
def source(request: Request, source_id: str):
    """The quoted text behind a citation (doc / ticket / message)."""
    ctx, vid, new = _tenant(request)
    rows = ctx.graph.ro_query(
        "MATCH (s:E {id: $id}) WHERE s:Doc OR s:Ticket OR s:Message "
        "OPTIONAL MATCH (p:Person)-[:WROTE]->(s) OPTIONAL MATCH (th:Thread)-[:HAS]->(s) "
        "RETURN s.id, s.label, coalesce(s.text, s.body), coalesce(s.title, th.channel), s.section, p.name",
        {"id": source_id}).result_set
    if not rows:
        raise HTTPException(404, "source not found")
    r = rows[0]
    return _with_cookie(JSONResponse({"id": r[0], "type": r[1], "text": r[2], "title": r[3], "section": r[4],
                                      "author": r[5]}), vid, new)


@app.get("/api/explain/{grant_id}")
def explain(request: Request, grant_id: str):
    ctx, vid, new = _tenant(request)
    res = tools.call(ctx, RunCtx(), "explain_grant", {"grant_ids": [grant_id]})
    return _with_cookie(JSONResponse(res), vid, new)


@app.get("/api/who_knows/{node_id}")
def who_knows(request: Request, node_id: str):
    ctx, vid, new = _tenant(request)
    return _with_cookie(JSONResponse(tools.call(ctx, RunCtx(), "who_knows", {"node_id": node_id})), vid, new)


@app.get("/api/decisions")
def decisions(request: Request):
    ctx, vid, new = _tenant(request)
    return _with_cookie(JSONResponse({"decisions": recall(ctx)}), vid, new)


@app.post("/api/decisions")
async def post_decision(request: Request):
    """The ONLY path that writes an ACCEPT_RISK: a person confirming the form."""
    ctx, vid, new = await run_in_threadpool(_tenant, request)
    if ctx.readonly:
        raise HTTPException(409, "shared read-only copy: decisions are not saved")
    body = await request.json()
    try:
        res = await run_in_threadpool(record_decision, ctx, body.get("grant_id", ""), body.get("disposition", ""),
                                      body.get("rationale", ""), body.get("review_by"), body.get("cites") or [],
                                      "you", confirmed=True)
    except DecisionError as e:
        raise HTTPException(422, str(e)) from e
    return _with_cookie(JSONResponse(res), vid, new)


@app.post("/api/event/{event_id}")
def event(request: Request, event_id: str):
    ctx, vid, new = _tenant(request)
    try:
        res = apply_event(ctx, event_id)
    except ScenarioEventRejected as e:
        raise HTTPException(409, str(e)) from e
    return _with_cookie(JSONResponse(res), vid, new)


@app.post("/api/reset")
def reset(request: Request):
    vid, new = _visitor(request)
    graphdb.drop_graph(graphdb.visitor_graph_name(vid))
    ctx = graphdb.ensure_visitor_graph(vid, request.client.host if request.client else "?")
    return _with_cookie(JSONResponse({"ok": True, "readonly": ctx.readonly}), vid, new)


@app.get("/healthz")
def healthz():
    ok = graphdb.ping()
    tmpl = graphdb.template_name() if ok else None
    status = 200 if ok and tmpl else 503
    return JSONResponse({"falkordb": ok, "template": tmpl, "llm": provider_ready(),
                         "provider": settings.llm_provider, "model": settings.model}, status_code=status)


@app.get("/admin")
def admin(token: str = ""):
    if not settings.admin_token or token != settings.admin_token:
        raise HTTPException(403)
    return {"llm_runs_today": _spend["runs"], "visitor_graphs": graphdb.visitor_count(),
            "graphs": graphdb.db().list_graphs()}
