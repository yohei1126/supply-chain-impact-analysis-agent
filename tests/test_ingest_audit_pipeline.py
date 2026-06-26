"""Tests for async Graph Contract on_ingest audit pipeline (L4)."""

from __future__ import annotations

import json

from app.federation.graph_store import GraphStore
from app.validation.ingest_audit_checks import run_on_ingest_audit_checks
from app.validation.ingest_audit_pipeline import (
    export_violation_report,
    run_ingest_audit_pipeline,
)
from pipeline.demo.load_domains import load_all_domains_separately


def test_on_ingest_audit_checks_pass_after_full_load(
    graph_store: GraphStore,
    tmp_path,
) -> None:
    load_all_domains_separately(graph_store)
    duckdb = tmp_path / "bom.duckdb"
    from app.component_master_store import ComponentMasterStore

    master = ComponentMasterStore(graph_store=graph_store, duckdb_path=str(duckdb))
    try:
        for node in graph_store._all_nodes():
            if node["label"] != "Component":
                continue
            props = {
                key: node["properties"][key]
                for key in ("id", "name", "material", "cost")
                if key in node["properties"]
            }
            master.upsert_component(props)
    finally:
        master.close()

    checks_run, violations = run_on_ingest_audit_checks(
        graph_store.driver,
        duckdb_path=duckdb,
    )
    assert checks_run
    assert not violations, violations


def test_ingest_audit_pipeline_passes_after_full_load(
    graph_store: GraphStore,
    tmp_path,
) -> None:
    load_all_domains_separately(graph_store)
    duckdb = tmp_path / "bom.duckdb"
    from app.component_master_store import ComponentMasterStore

    master = ComponentMasterStore(graph_store=graph_store, duckdb_path=str(duckdb))
    try:
        for node in graph_store._all_nodes():
            if node["label"] != "Component":
                continue
            props = {
                key: node["properties"][key]
                for key in ("id", "name", "material", "cost")
                if key in node["properties"]
            }
            master.upsert_component(props)
    finally:
        master.close()

    report = run_ingest_audit_pipeline(graph_store.driver, duckdb_path=duckdb)
    assert report.passed, report.audit_violations + report.ingest_quality.violations
    payload = export_violation_report(report)
    assert payload["format"] == "bom-violation-report"
    assert payload["passed"] is True
    json.dumps(payload)


def test_ingest_audit_pipeline_catches_orphan_edge_endpoints(graph_store: GraphStore) -> None:
    load_all_domains_separately(graph_store)
    with graph_store.driver.session() as session:
        session.run(
            """
            MATCH (c:Component {id: 'COMP-100', graph_id: 'ebom'})
            MATCH (p:Product {id: 'PROD-900', graph_id: 'ebom'})
            CREATE (c)-[:USED_IN]->(p)
            SET p.graph_id = 'sourcing'
            """
        )
    _, violations = run_on_ingest_audit_checks(graph_store.driver)
    assert any(v.check_id == "orphan_edge_endpoints" for v in violations)
