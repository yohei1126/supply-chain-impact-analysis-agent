"""Async Graph Contract on_ingest audit pipeline for data stewards (L4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.storage.neo4j_config import DEFAULT_DATABASE
from app.validation.contract_ingest import (
    IngestQualityReport,
    IngestQualityViolation,
    format_ingest_quality_report,
    run_on_ingest_quality_gates,
)
from app.validation.contract_loader import get_graph_contract
from app.validation.ingest_audit_checks import run_on_ingest_audit_checks
from app.validation.neo4j_l3_audit import L3AuditReport, format_report, run_l3_audit

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    Driver = Any  # type: ignore[misc, assignment]


@dataclass
class IngestAuditPipelineReport:
    """Combined steward report: L3 + on_ingest + on_ingest_audit batch checks."""

    generated_at: str
    contract_version: str
    l3_report: L3AuditReport
    ingest_quality: IngestQualityReport
    audit_checks_run: list[str] = field(default_factory=list)
    audit_violations: list[IngestQualityViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.l3_report.passed and self.ingest_quality.passed and not self.audit_violations


def run_ingest_audit_pipeline(
    driver: Driver,
    *,
    duckdb_path: str | Path = "data/bom.duckdb",
    duckdb_conn: Any | None = None,
    database: str = DEFAULT_DATABASE,
) -> IngestAuditPipelineReport:
    """Run the full async on_ingest audit pipeline against a live Neo4j graph."""
    contract = get_graph_contract()
    l3_report = run_l3_audit(driver, database=database)
    ingest_quality = run_on_ingest_quality_gates(
        driver,
        contract,
        duckdb_path=duckdb_path,
        duckdb_conn=duckdb_conn,
        database=database,
        l3_report=l3_report,
    )
    audit_checks_run, audit_violations = run_on_ingest_audit_checks(
        driver,
        contract,
        duckdb_path=duckdb_path,
        duckdb_conn=duckdb_conn,
        database=database,
    )
    return IngestAuditPipelineReport(
        generated_at=datetime.now(tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        contract_version=contract.version,
        l3_report=l3_report,
        ingest_quality=ingest_quality,
        audit_checks_run=audit_checks_run,
        audit_violations=audit_violations,
    )


def export_violation_report(report: IngestAuditPipelineReport) -> dict[str, Any]:
    """Steward-facing JSON report (bom-validate Skill compatible shape)."""
    violations: list[dict[str, Any]] = []
    for item in report.l3_report.cypher_violations:
        violations.append(
            {
                "check_id": item.check_id,
                "layer": "L3",
                "description": item.description,
                "count": item.count,
                "sample": item.sample,
            }
        )
    for error in report.l3_report.payload_errors:
        violations.append(
            {
                "check_id": "payload_validation",
                "layer": "L3",
                "description": error.get("error", "payload validation failed"),
                "sample": [error],
            }
        )
    for violation in report.ingest_quality.violations:
        violations.append(
            {
                "check_id": violation.check_id,
                "layer": "L4-on_ingest",
                "description": violation.description,
                "sample": violation.sample,
            }
        )
    for violation in report.audit_violations:
        violations.append(
            {
                "check_id": violation.check_id,
                "layer": "L4-on_ingest_audit",
                "description": violation.description,
                "sample": violation.sample,
            }
        )
    return {
        "format": "bom-violation-report",
        "version": 1,
        "generated_at": report.generated_at,
        "graph_contract_version": report.contract_version,
        "passed": report.passed,
        "checks_run": {
            "on_ingest": list(report.ingest_quality.checks_run),
            "on_ingest_audit": list(report.audit_checks_run),
        },
        "violations": violations,
    }


def format_ingest_audit_pipeline_report(report: IngestAuditPipelineReport) -> str:
    lines = [
        f"Graph Contract on_ingest audit pipeline (v{report.contract_version})",
        f"  generated_at: {report.generated_at}",
    ]
    if report.passed:
        lines.append("  status: PASS")
        return "\n".join(lines)

    lines.append("  status: FAIL")
    if not report.l3_report.passed:
        lines.append(format_report(report.l3_report))
    if not report.ingest_quality.passed:
        lines.append(format_ingest_quality_report(report.ingest_quality))
    for violation in report.audit_violations:
        lines.append(f"  [audit:{violation.check_id}] {violation.description}")
        for row in violation.sample[:3]:
            lines.append(f"    sample: {row}")
    return "\n".join(lines)


__all__ = [
    "IngestAuditPipelineReport",
    "export_violation_report",
    "format_ingest_audit_pipeline_report",
    "run_ingest_audit_pipeline",
]
