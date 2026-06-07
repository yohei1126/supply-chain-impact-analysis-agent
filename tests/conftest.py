from __future__ import annotations

import pytest

from app.federation.graph_store import GraphStore
from app.storage.neo4j_config import ensure_domain_databases, get_driver, reset_neo4j, verify_connectivity


@pytest.fixture(scope="session")
def neo4j_driver():
    try:
        driver = get_driver()
        verify_connectivity(driver)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Neo4j not available: {exc}")
    ensure_domain_databases(driver)
    yield driver
    driver.close()


@pytest.fixture
def graph_store(neo4j_driver):
    reset_neo4j(neo4j_driver)
    store = GraphStore(driver=neo4j_driver)
    yield store
