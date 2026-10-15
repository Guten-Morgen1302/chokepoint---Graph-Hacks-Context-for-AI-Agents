"""Tenancy bookkeeping in the chokepoint_meta graph (works where Redis key commands are denied)."""

import dataclasses
import uuid

import pytest

from chokepoint import graphdb as G
from chokepoint.config import settings

pytestmark = pytest.mark.db


@pytest.fixture
def ip():
    ip = f"test-{uuid.uuid4().hex[:8]}"
    yield ip
    G._meta("MATCH (h:IpHit {ip: $ip}) DELETE h", {"ip": ip})


def _cleanup(*vids):
    for v in vids:
        G.drop_graph(G.visitor_graph_name(v))


def test_visitor_copy_registered_and_reused(template, ip):
    vid = G.new_visitor_id()
    try:
        ctx = G.ensure_visitor_graph(vid, ip)
        assert not ctx.readonly and ctx.graph_name in G.db().list_graphs()
        assert G._meta("MATCH (v:Visitor {name: $n}) RETURN count(v)", {"n": ctx.graph_name})[0][0] == 1
        again = G.ensure_visitor_graph(vid, ip)
        assert again.graph_name == ctx.graph_name
        assert G._meta("MATCH (h:IpHit {ip: $ip}) RETURN count(h)", {"ip": ip})[0][0] == 1
    finally:
        _cleanup(vid)
    assert G._meta("MATCH (v:Visitor {name: $n}) RETURN count(v)", {"n": ctx.graph_name})[0][0] == 0


def test_per_ip_limit_but_reset_is_free(template, ip, monkeypatch):
    monkeypatch.setattr(G, "settings", dataclasses.replace(settings, per_ip_graphs_per_hour=2))
    vids = [G.new_visitor_id() for _ in range(3)]
    try:
        a, b = (G.ensure_visitor_graph(v, ip) for v in vids[:2])
        assert not a.readonly and not b.readonly
        assert G.ensure_visitor_graph(vids[2], ip).readonly   # third new visitor from this IP
        G.drop_graph(a.graph_name)                             # "Reset demo" = drop + recreate
        assert not G.ensure_visitor_graph(vids[0], ip).readonly
    finally:
        _cleanup(*vids)


def test_sweep_lock_and_expiry(template):
    G._meta("MATCH (l:Kv {k: 'sweep_lock'}) DELETE l")
    stale = f"v_test{uuid.uuid4().hex[:8]}"
    G.db().select_graph(template).copy(stale)
    G._meta("CREATE (:Visitor {name: $n, ts: 0})", {"n": stale})
    G.copy_scratch("cli_test_old")
    G._meta("MATCH (s:Scratch {name: 'cli_test_old'}) SET s.ts = 0")
    try:
        out = G.sweep()
        assert stale in out["dropped"] and "cli_test_old" in out["dropped"]
        assert stale not in G.db().list_graphs() and not G.is_scratch("cli_test_old")
        assert G.sweep() == {"skipped": True}                  # lock held for 240 s
    finally:
        G._meta("MATCH (l:Kv {k: 'sweep_lock'}) DELETE l")
        G.drop_graph(stale)
        G.drop_scratch("cli_test_old")
