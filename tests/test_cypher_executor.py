"""Tests for Cypher execution against domain Lance graphs."""

from __future__ import annotations

import shutil

import pytest

from app.federation.analysis import (
    query_ebom_for_components,
    query_routing_for_components,
    query_sourcing_for_supplier,
)
from app.federation.cypher_executor import execute_domain_cypher
from app.federation.cypher_queries import cypher_components_by_supplier
from app.federation.graph_store import LanceGraphStore
from pipeline.demo.load_domains import load_all_domains_separately, reset_lancedb


@pytest.fixture
def federated_graph(tmp_path):
    lance = tmp_path / "lancedb"
    reset_lancedb(lance)
    graph = LanceGraphStore(lancedb_path=str(lance))
    load_all_domains_separately(graph)
    yield graph
    if lance.exists():
        shutil.rmtree(lance)


def test_execute_domain_cypher_sourcing(federated_graph) -> None:
    rows = execute_domain_cypher(
        federated_graph.domain("sourcing"),
        "sourcing",
        cypher_components_by_supplier(),
        parameters={"supplier_id": "SUP-002"},
    )
    assert rows
    assert all(row["supplier_id"] == "SUP-002" for row in rows)


def test_query_helpers_return_cypher(federated_graph) -> None:
    sourcing = query_sourcing_for_supplier(federated_graph, "SUP-001")
    assert "MATCH" in sourcing.cypher
    assert sourcing.rows

    component_ids = {row["component_id"] for row in sourcing.rows}
    ebom = query_ebom_for_components(federated_graph, component_ids)
    routing = query_routing_for_components(federated_graph, component_ids)
    assert "USED_IN" in ebom.cypher
    assert "INPUT_OF" in routing.cypher
