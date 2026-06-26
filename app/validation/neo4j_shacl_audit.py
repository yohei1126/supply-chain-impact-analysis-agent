"""Neosemantics SHACL batch validation for L3 post-load conformance."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.storage.neo4j_config import DEFAULT_DATABASE
from ontology.shacl_codegen import export_shacl_ttl

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    Driver = Any  # type: ignore[misc, assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHAPES_PATH = REPO_ROOT / "ontology" / "assets" / "bom-shapes.ttl"


@dataclass
class ShaclViolation:
    focus_node: Any
    node_type: str
    property_shape: str
    offending_value: Any
    result_path: str
    severity: str


@dataclass
class ShaclAuditReport:
    passed: bool
    skipped: bool = False
    skip_reason: str | None = None
    violations: list[ShaclViolation] = field(default_factory=list)


def default_shacl_ttl() -> str:
    if DEFAULT_SHAPES_PATH.is_file():
        return DEFAULT_SHAPES_PATH.read_text(encoding="utf-8")
    return export_shacl_ttl()


def neosemantics_shacl_available(session: Any) -> bool:
    result = session.run(
        "SHOW PROCEDURES YIELD name "
        "WHERE name = 'n10s.validation.shacl.validateSet' "
        "RETURN count(*) AS c"
    )
    record = result.single()
    return bool(record and record["c"])


def _import_shapes(session: Any, ttl: str) -> None:
    session.run(
        "CALL n10s.validation.shacl.import.inline($ttl, 'Turtle')",
        ttl=ttl,
    )


def _collect_scoped_nodes(session: Any) -> int:
    result = session.run("MATCH (n) WHERE n.graph_id IS NOT NULL RETURN count(n) AS c")
    record = result.single()
    return int(record["c"]) if record else 0


def _run_validate_set(session: Any) -> list[ShaclViolation]:
    result = session.run(
        """
        MATCH (n)
        WHERE n.graph_id IS NOT NULL
        WITH collect(n) AS nodes
        CALL n10s.validation.shacl.validateSet(nodes)
        YIELD focusNode, nodeType, propertyShape, offendingValue, resultPath, severity
        RETURN focusNode, nodeType, propertyShape, offendingValue, resultPath, severity
        """
    )
    return [
        ShaclViolation(
            focus_node=record["focusNode"],
            node_type=record["nodeType"],
            property_shape=record["propertyShape"],
            offending_value=record["offendingValue"],
            result_path=record["resultPath"],
            severity=record["severity"],
        )
        for record in result
    ]


def run_shacl_audit(
    driver: Driver,
    *,
    database: str = DEFAULT_DATABASE,
    ttl: str | None = None,
) -> ShaclAuditReport:
    """Run Neosemantics SHACL validation on nodes scoped by graph_id."""
    shapes = ttl if ttl is not None else default_shacl_ttl()
    with driver.session(database=database) as session:
        if not neosemantics_shacl_available(session):
            return ShaclAuditReport(
                passed=True,
                skipped=True,
                skip_reason="Neosemantics SHACL procedures are not installed (n10s plugin).",
            )

        node_count = _collect_scoped_nodes(session)
        _import_shapes(session, shapes)
        if node_count == 0:
            return ShaclAuditReport(passed=True)

        violations = _run_validate_set(session)
        return ShaclAuditReport(passed=not violations, violations=violations)


def format_shacl_report(report: ShaclAuditReport) -> str:
    lines = ["L3 Neosemantics SHACL audit"]
    if report.skipped:
        lines.append(f"  status: SKIPPED ({report.skip_reason})")
        return "\n".join(lines)
    if report.passed:
        lines.append("  status: PASS")
        return "\n".join(lines)

    lines.append("  status: FAIL")
    for violation in report.violations[:10]:
        lines.append(
            "  "
            f"[{violation.node_type}] {violation.result_path} "
            f"({violation.property_shape}): {violation.offending_value!r}"
        )
    if len(report.violations) > 10:
        lines.append(f"  ... {len(report.violations) - 10} more SHACL violations")
    return "\n".join(lines)


__all__ = [
    "DEFAULT_SHAPES_PATH",
    "ShaclAuditReport",
    "ShaclViolation",
    "default_shacl_ttl",
    "format_shacl_report",
    "neosemantics_shacl_available",
    "run_shacl_audit",
]
