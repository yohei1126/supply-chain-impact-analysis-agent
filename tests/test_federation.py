"""Integration tests for Graph Contract federation composer (Neo4j)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.federation.analysis import analyze_supplier_disruption
from app.federation.composer import compose_supplier_disruption
from app.federation.graph_store import GraphStore
from pipeline.demo.load_domains import load_all_domains_separately
from tests.conftest import init_empty_duckdb, populate_duckdb_master


@pytest.fixture
def federated_graph(graph_store: GraphStore, tmp_path: Path):
    load_all_domains_separately(graph_store)
    duckdb_path = tmp_path / "bom.duckdb"
    populate_duckdb_master(graph_store, duckdb_path)
    return graph_store, duckdb_path


def test_compose_supplier_to_products_join(federated_graph) -> None:
    store, duckdb_path = federated_graph
    compose = compose_supplier_disruption(store, "SUP-002", duckdb_path=duckdb_path)
    assert compose.passed
    assert compose.join_name == "supplier_to_products"
    assert compose.contract_version == "1.0.0"
    assert len(compose.join_plan) == 2
    assert compose.federated_rows
    assert compose.graph_view["node_count"] >= 1
    product_ids = {row["product_id"] for row in compose.federated_rows}
    assert "PROD-900" in product_ids or "PROD-901" in product_ids


def test_analyze_supplier_disruption_uses_composer(federated_graph) -> None:
    store, duckdb_path = federated_graph
    analysis = analyze_supplier_disruption(store, "SUP-001", duckdb_path=str(duckdb_path))
    assert analysis.join_name == "supplier_to_products"
    assert analysis.graph_contract_version == "1.0.0"
    assert analysis.quality_passed
    assert analysis.federated_rows
    assert len(analysis.join_plan) == 2
    assert analysis.domain_snapshots
    snapshots = {item.graph_id: item.as_of for item in analysis.domain_snapshots}
    assert snapshots["sourcing"] == "2026-06-01T06:00:00Z"
    assert snapshots["ebom"] == "2026-06-01T07:00:00Z"


def test_compose_rejects_when_master_missing_ids(graph_store: GraphStore, tmp_path: Path) -> None:
    load_all_domains_separately(graph_store)
    duckdb_path = tmp_path / "empty.duckdb"
    init_empty_duckdb(duckdb_path)
    compose = compose_supplier_disruption(graph_store, "SUP-001", duckdb_path=duckdb_path)
    assert not compose.passed
    assert compose.federated_rows == []
    assert compose.quality is not None
    assert compose.quality.violations[0].rule_id == "reject_join_if_master_missing"
