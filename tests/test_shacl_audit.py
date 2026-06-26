"""Tests for Neosemantics SHACL batch validation (L3)."""

from __future__ import annotations

import pytest

from app.federation.graph_store import GraphStore
from app.validation.neo4j_l3_audit import run_l3_audit
from app.validation.neo4j_shacl_audit import neosemantics_shacl_available, run_shacl_audit
from pipeline.demo.load_domains import load_all_domains_separately


def _require_n10s(graph_store: GraphStore) -> None:
    with graph_store.driver.session() as session:
        if not neosemantics_shacl_available(session):
            pytest.skip("Neosemantics n10s plugin is not installed on Neo4j")


def test_shacl_audit_passes_after_domain_load(graph_store: GraphStore) -> None:
    _require_n10s(graph_store)
    load_all_domains_separately(graph_store)
    report = run_shacl_audit(graph_store.driver)
    assert not report.skipped
    assert report.passed, report.violations


def test_l3_audit_includes_shacl_when_n10s_available(graph_store: GraphStore) -> None:
    _require_n10s(graph_store)
    load_all_domains_separately(graph_store)
    report = run_l3_audit(graph_store.driver)
    assert report.shacl_report is not None
    assert not report.shacl_report.skipped
    assert report.passed, (
        report.cypher_violations
        + report.payload_errors
        + (report.shacl_report.violations if report.shacl_report else [])
    )


def test_shacl_audit_catches_invalid_component_cost(graph_store: GraphStore) -> None:
    _require_n10s(graph_store)
    load_all_domains_separately(graph_store)
    with graph_store.driver.session() as session:
        session.run(
            """
            MATCH (c:Component {id: 'COMP-100', graph_id: 'ebom'})
            SET c.cost = -1.0
            """
        )
    report = run_shacl_audit(graph_store.driver)
    assert not report.passed
    assert report.violations
