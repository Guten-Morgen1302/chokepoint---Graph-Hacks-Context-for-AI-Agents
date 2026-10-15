"""FalkorDB access, per-visitor tenancy and the per-graph `cf` lock.

Tenancy (ENG-6 / ENG2): each visitor gets an isolated GRAPH.COPY of the
current template, `v_<hmac16>`, all in ONE FalkorDB instance (multigraph).
The client never sends a graph name; it is derived from an HMAC-signed cookie.

Bookkeeping lives in a small graph, not in Redis keys: FalkorDB Cloud only
lets the database user run GRAPH.* commands (GET/SET/ZADD are denied).

    chokepoint_meta
      (:Kv {k:'template', v:'tmpl_<fixture_sha8>'})   (:Kv {k:'sweep_lock', v:until})
      (:Visitor {name, ts})   (:IpHit {ip, name, ts})   (:Scratch {name, ts})
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass

from falkordb import FalkorDB

from .config import settings

META_GRAPH = "chokepoint_meta"
SCRATCH_TTL_S = 2 * 3600
IDLE_EVICT_S = 30 * 60
EXPIRE_S = 24 * 3600


class GraphUnavailable(Exception):
    pass


class TenantCapReached(Exception):
    pass


_db: FalkorDB | None = None
_db_lock = threading.Lock()


def db() -> FalkorDB:
    global _db
    with _db_lock:
        if _db is None:
            _db = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port,
                           username=settings.falkordb_username, password=settings.falkordb_password)
        return _db


def redis():
    return db().connection


def _meta(q: str, params: dict | None = None) -> list:
    return db().select_graph(META_GRAPH).query(q, params or {}).result_set


def visitor_count() -> int:
    return _meta("MATCH (v:Visitor) RETURN count(v)")[0][0]


def is_scratch(name: str) -> bool:
    return bool(_meta("MATCH (s:Scratch {name: $n}) RETURN count(s)", {"n": name})[0][0])


def ping() -> bool:
    try:
        return bool(redis().ping())
    except Exception:
        return False


# ── per-graph lock for the counterfactual capacity property `cf` ────────────
_graph_locks: dict[str, threading.Lock] = {}
_graph_locks_guard = threading.Lock()


def graph_lock(name: str) -> threading.Lock:
    with _graph_locks_guard:
        lk = _graph_locks.get(name)
        if lk is None:
            lk = _graph_locks[name] = threading.Lock()
        return lk


@dataclass
class TenantCtx:
    graph_name: str
    readonly: bool = False
    cf_dirty: str | None = None  # set when a cf cleanup failed (SD-2, I3)

    @property
    def graph(self):
        return db().select_graph(self.graph_name)

    @property
    def lock(self) -> threading.Lock:
        return graph_lock(self.graph_name)


_dirty: dict[str, str] = {}


def mark_cf_dirty(graph_name: str, err: str) -> None:
    _dirty[graph_name] = err


def cf_dirty(graph_name: str) -> str | None:
    return _dirty.get(graph_name)


def clear_cf_dirty(graph_name: str) -> None:
    _dirty.pop(graph_name, None)


# ── template + visitors ─────────────────────────────────────────────────────

def template_name() -> str | None:
    rows = _meta("MATCH (t:Kv {k: 'template'}) RETURN t.v")
    return rows[0][0] if rows else None


def set_template(name: str) -> str | None:
    old = template_name()
    _meta("MERGE (t:Kv {k: 'template'}) SET t.v = $v", {"v": name})
    return old


def new_visitor_id() -> str:
    return secrets.token_hex(16)


def sign(visitor_id: str) -> str:
    sig = hmac.new(settings.secret.encode(), visitor_id.encode(), hashlib.sha256).hexdigest()[:24]
    return f"{visitor_id}.{sig}"


def verify(cookie: str | None) -> str | None:
    if not cookie or "." not in cookie:
        return None
    vid, sig = cookie.rsplit(".", 1)
    good = hmac.new(settings.secret.encode(), vid.encode(), hashlib.sha256).hexdigest()[:24]
    return vid if hmac.compare_digest(sig, good) else None


def visitor_graph_name(visitor_id: str) -> str:
    return "v_" + hmac.new(settings.secret.encode(), visitor_id.encode(), hashlib.sha256).hexdigest()[:16]


def _graph_exists(name: str) -> bool:
    try:
        return name in set(db().list_graphs())
    except Exception as e:  # connection problems surface as GraphUnavailable
        raise GraphUnavailable(str(e)) from e


def ensure_visitor_graph(visitor_id: str, ip: str = "?") -> TenantCtx:
    """Register-before-create, then GRAPH.COPY the template (ENG-6)."""
    tmpl = template_name()
    if not tmpl:
        raise GraphUnavailable("no template graph: run `python -m chokepoint.cli seed`")
    name = visitor_graph_name(visitor_id)
    now = time.time()
    if _graph_exists(name):
        _touch(name, now)
        return TenantCtx(name)
    # per-IP creation limit
    _meta("MATCH (h:IpHit) WHERE h.ts < $t DELETE h", {"t": now - 3600})
    known, hits = _meta("MATCH (h:IpHit {ip: $ip}) RETURN count(CASE WHEN h.name = $n THEN 1 END), count(h)",
                        {"ip": ip, "n": name})[0]
    if not known and hits >= settings.per_ip_graphs_per_hour:  # a reset of the same visitor is not a new graph
        return TenantCtx(tmpl, readonly=True)
    # global cap with LRU eviction of idle graphs
    if visitor_count() >= settings.max_visitor_graphs:
        idle = _meta("MATCH (v:Visitor) WHERE v.ts <= $t RETURN v.name ORDER BY v.ts LIMIT 1",
                     {"t": now - IDLE_EVICT_S})
        if not idle:
            return TenantCtx(tmpl, readonly=True)
        drop_graph(idle[0][0])
    _touch(name, now)                          # register BEFORE create
    _meta("CREATE (:IpHit {ip: $ip, name: $n, ts: $t})", {"ip": ip, "n": name, "t": now})
    db().select_graph(tmpl).copy(name)
    return TenantCtx(name)


def _touch(name: str, now: float) -> None:
    _meta("MERGE (v:Visitor {name: $n}) SET v.ts = $t", {"n": name, "t": now})


def touch(ctx: TenantCtx) -> None:
    if not ctx.readonly:
        _touch(ctx.graph_name, time.time())


def drop_graph(name: str) -> None:
    try:
        db().select_graph(name).delete()
    except Exception:
        pass
    _meta("MATCH (v:Visitor {name: $n}) DELETE v", {"n": name})


def copy_scratch(name: str) -> "TenantCtx":
    """A private copy of the template for the CLI / MCP, swept after 2h if leaked."""
    tmpl = template_name()
    if not tmpl:
        raise GraphUnavailable("no template graph: run `python -m chokepoint.cli seed`")
    _meta("MERGE (s:Scratch {name: $n}) SET s.ts = $t", {"n": name, "t": time.time()})
    if name not in set(db().list_graphs()):
        db().select_graph(tmpl).copy(name)
    return TenantCtx(name)


def drop_scratch(name: str) -> None:
    drop_graph(name)
    _meta("MATCH (s:Scratch {name: $n}) DELETE s", {"n": name})


_orphan_seen: set[str] = set()


def sweep() -> dict:
    """Drop visitor graphs idle > 24h; two-pass orphan removal (ENG-6)."""
    now = time.time()
    # one write query = atomic test-and-set (writes to a graph are serialized)
    got = _meta("MERGE (l:Kv {k: 'sweep_lock'}) WITH l, coalesce(l.v, 0) < $now AS free "
                "SET l.v = CASE WHEN free THEN $now + 240 ELSE l.v END RETURN free", {"now": now})[0][0]
    if not got:
        return {"skipped": True}
    dropped = []
    for (g,) in _meta("MATCH (v:Visitor) WHERE v.ts <= $t RETURN v.name", {"t": now - EXPIRE_S}):
        drop_graph(g)
        dropped.append(g)
    for (g,) in _meta("MATCH (s:Scratch) WHERE s.ts <= $t RETURN s.name", {"t": now - SCRATCH_TTL_S}):
        drop_scratch(g)
        dropped.append(g)
    registered = {g for (g,) in _meta("MATCH (v:Visitor) RETURN v.name")}
    orphans = {g for g in db().list_graphs() if g.startswith("v_") and g not in registered}
    for g in orphans & _orphan_seen:
        drop_graph(g)
        dropped.append(g)
    _orphan_seen.clear()
    _orphan_seen.update(orphans)
    return {"dropped": dropped}
