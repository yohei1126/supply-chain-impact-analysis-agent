"""Post-load gates for validated ingest pipelines (L2 write path + L3 proof)."""

from __future__ import annotations

from app.validation.neo4j_l3_audit import L3AuditReport, format_report, run_l3_audit

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    from typing import Any

    Driver = Any  # type: ignore[misc, assignment]


class L3ConformanceError(RuntimeError):
    """Raised when a loaded Neo4j graph fails L3 conformance checks."""


def require_l3_conformance(
    driver: Driver,
    *,
    quiet: bool = False,
) -> L3AuditReport:
    """Run L3 audit and raise if the live graph is not ontology-conformant."""
    report = run_l3_audit(driver)
    if report.passed:
        if quiet:
            print("L3 audit: PASS")
        else:
            print(format_report(report))
        return report
    message = format_report(report)
    print(message)
    raise L3ConformanceError(message)


__all__ = ["L3ConformanceError", "require_l3_conformance"]
