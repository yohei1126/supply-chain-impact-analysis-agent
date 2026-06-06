"""Tests for per-domain datasets and federated disruption analysis."""

from __future__ import annotations

import shutil

import pytest

from app.federation.analysis import analyze_supplier_disruption
from app.federation.graph_store import LanceGraphStore
from pipeline.demo.domain_datasets import build_all_domain_datasets, validate_all_datasets
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


def test_domain_datasets_validate_clean() -> None:
    datasets = build_all_domain_datasets()
    errors = validate_all_datasets(datasets)
    assert all(not errs for errs in errors.values())


def test_analyze_supplier_disruption_sup001(federated_graph) -> None:
    analysis = analyze_supplier_disruption(federated_graph, "SUP-001")
    assert analysis.supplier_id == "SUP-001"
    assert len(analysis.domain_queries) == 3
    assert analysis.federated_rows
    assert analysis.impact_score > 0
    assert analysis.problems
    assert analysis.mitigations
    product_ids = {row["product_id"] for row in analysis.federated_rows}
    assert "PROD-900" in product_ids or "PROD-901" in product_ids


def test_analyze_unknown_supplier_reports_no_supply(federated_graph) -> None:
    analysis = analyze_supplier_disruption(federated_graph, "SUP-999")
    assert not analysis.federated_rows
    assert any(p.category == "no_supply" for p in analysis.problems)
