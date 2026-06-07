from __future__ import annotations

import os
from typing import Any

from domains.registry import DOMAIN_GRAPHS, GraphId

try:
    from neo4j import Driver, GraphDatabase
except ImportError:  # pragma: no cover - optional until package install
    GraphDatabase = None  # type: ignore[misc, assignment]
    Driver = Any  # type: ignore[misc, assignment]

DEFAULT_DATABASE = "neo4j"


def neo4j_uri() -> str:
    return os.getenv("BOM_NEO4J_URI", "bolt://localhost:7687")


def neo4j_auth() -> tuple[str, str]:
    user = os.getenv("BOM_NEO4J_USER", "neo4j")
    password = os.getenv("BOM_NEO4J_PASSWORD", "password")
    return user, password


def get_driver(uri: str | None = None, auth: tuple[str, str] | None = None) -> Driver:
    if GraphDatabase is None:
        raise RuntimeError("neo4j package is not installed")
    return GraphDatabase.driver(uri or neo4j_uri(), auth=auth or neo4j_auth())


def verify_connectivity(driver: Driver) -> None:
    driver.verify_connectivity()


def ensure_domain_databases(driver: Driver) -> None:
    """Neo4j Community uses one database; domains are separated by graph_id property."""
    del driver


def reset_neo4j(driver: Driver, graph_ids: tuple[GraphId, ...] | None = None) -> None:
    targets = graph_ids or tuple(DOMAIN_GRAPHS.keys())
    with driver.session(database=DEFAULT_DATABASE) as session:
        for graph_id in targets:
            session.run("MATCH (n {graph_id: $graph_id}) DETACH DELETE n", graph_id=graph_id)
