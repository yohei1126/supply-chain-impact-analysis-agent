"""Tests for Cypher execution against domain Neo4j databases."""

from __future__ import annotations

import pytest

from app.federation.analysis import (
    query_ebom_for_components,
    query_routing_for_components,
    query_sourcing_for_supplier,
)
from app.federation.cypher_executor import execute_domain_cypher
from app.federation.cypher_queries import cypher_components_by_supplier
from app.federation.graph_store import GraphStore
from pipeline.demo.load_domains import load_all_domains_separately


def test_execute_domain_cypher_sourcing(graph_store: GraphStore) -> None:
    load_all_domains_separately(graph_store)
    rows = execute_domain_cypher(
        graph_store.domain("sourcing"),
        "sourcing",
        cypher_components_by_supplier(),
        parameters={"supplier_id": "SUP-002"},
    )
    assert rows
    assert all(row["supplier_id"] == "SUP-002" for row in rows)


def test_query_helpers_return_cypher(graph_store: GraphStore) -> None:
    load_all_domains_separately(graph_store)
    sourcing = query_sourcing_for_supplier(graph_store, "SUP-001")
    assert "MATCH" in sourcing.cypher
    assert sourcing.rows

    component_ids = {row["component_id"] for row in sourcing.rows}
    ebom = query_ebom_for_components(graph_store, component_ids)
    routing = query_routing_for_components(graph_store, component_ids)
    assert "USED_IN" in ebom.cypher
    assert "INPUT_OF" in routing.cypher


def test_execute_domain_cypher_rejects_writes(graph_store: GraphStore) -> None:
    with pytest.raises(ValueError, match="Write Cypher is not allowed"):
        execute_domain_cypher(
            graph_store.domain("ebom"),
            "ebom",
            "CREATE (n:Component {id: 'X', graph_id: 'ebom'})",
        )
