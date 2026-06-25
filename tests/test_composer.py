"""Tests for federation composer and on_federate quality gates (no Neo4j)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb

from app.federation.composer import merge_supplier_to_products_rows
from app.validation.contract_federate import (
    DomainSnapshot,
    run_on_federate_quality_gates,
)
from ontology.contract.graph_contract import load_graph_contract


def test_graph_contract_join_plan() -> None:
    contract = load_graph_contract()
    join = contract.join_plan("supplier_to_products")
    assert join.name == "supplier_to_products"
    assert len(join.steps) == 2
    assert contract.on_federate_rules()["reject_join_if_master_missing"] is True


def test_merge_supplier_to_products_rows() -> None:
    sourcing_rows = [
        {"component_id": "COMP-100", "component_name": "Frame", "cost": 1200.0},
    ]
    ebom_rows = [
        {
            "component_id": "COMP-100",
            "component_name": "Frame",
            "product_id": "PROD-900",
            "product_name": "Pump",
            "component_cost": 1200.0,
        }
    ]
    rows = merge_supplier_to_products_rows("SUP-001", sourcing_rows, ebom_rows)
    assert rows == [
        {
            "supplier_id": "SUP-001",
            "component_id": "COMP-100",
            "component_name": "Frame",
            "product_id": "PROD-900",
            "product_name": "Pump",
            "component_cost": 1200.0,
        }
    ]


def test_on_federate_warns_on_as_of_skew() -> None:
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    snapshots = [
        DomainSnapshot("sourcing", now.isoformat().replace("+00:00", "Z"), 3),
        DomainSnapshot(
            "ebom",
            (now - timedelta(hours=72)).isoformat().replace("+00:00", "Z"),
            2,
        ),
    ]
    report = run_on_federate_quality_gates(
        domain_snapshots=snapshots,
        component_ids={"COMP-100"},
        contract=load_graph_contract(),
        duckdb_path=Path("missing.duckdb"),
    )
    assert report.passed
    assert any(w.rule_id == "warn_if_as_of_skew_hours" for w in report.warnings)


def test_on_federate_rejects_missing_master_ids(tmp_path: Path) -> None:
    duckdb_path = tmp_path / "bom.duckdb"
    conn = duckdb.connect(str(duckdb_path))
    conn.execute(
        """
        CREATE TABLE components (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            material VARCHAR NOT NULL,
            cost DOUBLE NOT NULL
        )
        """
    )
    conn.execute("INSERT INTO components VALUES ('COMP-100', 'Frame', 'Steel', 1200.0)")
    conn.close()

    report = run_on_federate_quality_gates(
        domain_snapshots=[DomainSnapshot("sourcing", None, 1)],
        component_ids={"COMP-100", "COMP-999"},
        contract=load_graph_contract(),
        duckdb_path=duckdb_path,
    )
    assert not report.passed
    assert report.violations[0].rule_id == "reject_join_if_master_missing"


def test_on_federate_skips_master_check_without_duckdb_file() -> None:
    report = run_on_federate_quality_gates(
        domain_snapshots=[DomainSnapshot("sourcing", None, 1)],
        component_ids={"COMP-100"},
        contract=load_graph_contract(),
        duckdb_path=Path("does-not-exist.duckdb"),
    )
    assert report.passed
    assert "reject_join_if_master_missing" in report.rules_run
