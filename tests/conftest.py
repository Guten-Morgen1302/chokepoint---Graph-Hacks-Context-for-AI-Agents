"""Tests run against a REAL FalkorDB (never mocked: rule 3 is what we test).

    docker run -d -p 6379:6379 falkordb/falkordb:latest
    pytest            # uses FALKORDB_* from the environment, then .env, then localhost:6379
"""

import uuid

import pytest

from chokepoint.graphdb import TenantCtx, db, ping


def pytest_collection_modifyitems(config, items):
    if not ping():
        skip = pytest.mark.skip(reason="FalkorDB not reachable on FALKORDB_HOST/PORT")
        for it in items:
            if "db" in it.keywords:
                it.add_marker(skip)


@pytest.fixture(scope="session")
def template():
    from chokepoint.scenario.seed import ensure_template
    return ensure_template()


@pytest.fixture
def scenario(template):
    """A private copy of the seeded Northwind template."""
    name = f"t_{uuid.uuid4().hex[:8]}"
    db().select_graph(template).copy(name)
    ctx = TenantCtx(name)
    yield ctx
    db().select_graph(name).delete()


@pytest.fixture
def blank():
    name = f"t_{uuid.uuid4().hex[:8]}"
    ctx = TenantCtx(name)
    yield ctx
    try:
        db().select_graph(name).delete()
    except Exception:
        pass
