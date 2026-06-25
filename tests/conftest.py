from __future__ import annotations

from pathlib import Path

import pytest

from app.federation.graph_store import GraphStore
from app.storage.neo4j_config import (
    ensure_domain_databases,
    get_driver,
    reset_neo4j,
    verify_connectivity,
)


def populate_duckdb_master(graph: GraphStore, duckdb_path: Path) -> None:
    """Insert component rows from the graph into DuckDB without mutating Neo4j."""
    import duckdb

    conn = duckdb.connect(str(duckdb_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS components (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            material VARCHAR NOT NULL,
            cost DOUBLE NOT NULL
        )
        """
    )
    for node in graph._all_nodes():
        if node["label"] != "Component":
            continue
        props = node["properties"]
        conn.execute(
            """
            INSERT INTO components AS c (id, name, material, cost)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                material = excluded.material,
                cost = excluded.cost
            """,
            [
                props["id"],
                props["name"],
                props["material"],
                props["cost"],
            ],
        )
    conn.close()


def init_empty_duckdb(duckdb_path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(duckdb_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS components (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            material VARCHAR NOT NULL,
            cost DOUBLE NOT NULL
        )
        """
    )
    conn.close()


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
