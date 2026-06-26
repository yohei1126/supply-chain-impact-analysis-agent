"""Post-load gates for validated ingest pipelines (L2 write path + L3/L4 proof)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.validation.contract_ingest import (
    IngestQualityReport,
    format_ingest_quality_report,
    run_on_ingest_quality_gates,
)
from app.validation.neo4j_l3_audit import L3AuditReport, format_report, run_l3_audit

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    from typing import Any

    Driver = Any  # type: ignore[misc, assignment]


class L3ConformanceError(RuntimeError):
    """Raised when a loaded Neo4j graph fails L3/L4 ingest conformance checks."""


def require_l3_conformance(
    driver: Driver,
    *,
    quiet: bool = False,
    duckdb_path: str | Path = "data/bom.duckdb",
    duckdb_conn: Any | None = None,
    require_shacl: bool | None = None,
) -> L3AuditReport:
    """Run L3 audit and Graph Contract on_ingest gates; raise if not conformant."""
    if require_shacl is None:
        require_shacl = os.getenv("BOM_L3_REQUIRE_SHACL", "0") == "1"

    l3_report = run_l3_audit(driver)
    quality_report = run_on_ingest_quality_gates(
        driver,
        duckdb_path=duckdb_path,
        duckdb_conn=duckdb_conn,
    )

    shacl_skipped = l3_report.shacl_report is not None and l3_report.shacl_report.skipped
    if require_shacl and shacl_skipped:
        message = format_report(l3_report)
        print(message)
        raise L3ConformanceError(
            "Neosemantics SHACL validation is required but the n10s plugin is not available."
        )

    if l3_report.passed and quality_report.passed:
        if quiet:
            print(f"L3 audit: PASS (Graph Contract v{quality_report.contract_version})")
        else:
            print(format_report(l3_report))
            print(format_ingest_quality_report(quality_report))
        return l3_report

    parts = []
    if not l3_report.passed:
        parts.append(format_report(l3_report))
    if not quality_report.passed:
        parts.append(format_ingest_quality_report(quality_report))
    message = "\n".join(parts)
    print(message)
    raise L3ConformanceError(message)


__all__ = ["IngestQualityReport", "L3ConformanceError", "require_l3_conformance"]
