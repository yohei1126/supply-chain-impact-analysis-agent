"""Tests for L3 post-load Neo4j conformance audit."""

from __future__ import annotations

from app.federation.graph_store import GraphStore
from app.validation.neo4j_l3_audit import run_l3_audit
from domains.registry import DOMAIN_GRAPHS
from ontology.l3_audit import all_l3_checks, ontology_l3_checks
from pipeline.demo.load_domains import load_all_domains_separately


def test_ontology_l3_checks_cover_allowed_edges() -> None:
    checks = ontology_l3_checks()
    ids = {check.check_id for check in checks}
    assert "unknown_node_label" in ids
    assert "invalid_edge_endpoints" in ids
    assert "cross_graph_edge" in ids


def test_all_l3_checks_include_domain_partitions() -> None:
    checks = all_l3_checks(DOMAIN_GRAPHS, graph_contract_version="1.0.0")
    ids = {check.check_id for check in checks}
    assert "domain_node_ebom" in ids
    assert "domain_edge_sourcing" in ids
    assert "stale_graph_contract_version" in ids


def test_l3_audit_passes_after_domain_load(graph_store: GraphStore) -> None:
    load_all_domains_separately(graph_store)
    report = run_l3_audit(graph_store.driver)
    assert report.passed, report.cypher_violations + report.payload_errors


def test_l3_audit_catches_invalid_edge_endpoints(graph_store: GraphStore) -> None:
    load_all_domains_separately(graph_store)
    with graph_store.driver.session() as session:
        session.run(
            """
            MATCH (c:Component {id: 'COMP-100', graph_id: 'ebom'})
            MATCH (p:Product {id: 'PROD-900', graph_id: 'ebom'})
            CREATE (c)-[:PRODUCED_BY]->(p)
            """
        )
    report = run_l3_audit(graph_store.driver)
    assert not report.passed
    assert any(v.check_id == "invalid_edge_endpoints" for v in report.cypher_violations)


def test_l3_audit_catches_domain_edge_violation(graph_store: GraphStore) -> None:
    load_all_domains_separately(graph_store)
    with graph_store.driver.session() as session:
        session.run(
            """
            MATCH (c:Component {id: 'COMP-100', graph_id: 'ebom'})
            MATCH (p:Product {id: 'PROD-900', graph_id: 'ebom'})
            CREATE (c)-[:USED_IN]->(p)
            CREATE (c)-[:SUPPLIED_BY {graph_id: 'ebom'}]->(p)
            """
        )
    report = run_l3_audit(graph_store.driver)
    assert not report.passed
    assert any(v.check_id == "domain_edge_ebom" for v in report.cypher_violations)
