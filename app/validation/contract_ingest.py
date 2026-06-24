"""Graph Contract quality.on_ingest checks against a live Neo4j graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.storage.neo4j_config import DEFAULT_DATABASE
from app.validation.contract_loader import get_graph_contract
from app.validation.neo4j_l3_audit import run_l3_audit
from ontology.contract.graph_contract import GraphContract

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    Driver = Any  # type: ignore[misc, assignment]


@dataclass
class IngestQualityViolation:
    check_id: str
    description: str
    sample: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class IngestQualityReport:
    passed: bool
    contract_version: str
    checks_run: list[str] = field(default_factory=list)
    violations: list[IngestQualityViolation] = field(default_factory=list)


def _check_bridge_ids_in_master(
    session: Any,
    *,
    duckdb_path: Path,
) -> IngestQualityViolation | None:
    import duckdb

    if not duckdb_path.is_file():
        return None

    result = session.run(
        "MATCH (c:Component) WHERE c.graph_id IS NOT NULL "
        "RETURN DISTINCT c.id AS component_id ORDER BY component_id LIMIT 500"
    )
    component_ids = [record["component_id"] for record in result if record["component_id"]]
    if not component_ids:
        return None

    conn = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        placeholders = ", ".join("?" for _ in component_ids)
        rows = conn.execute(
            f"SELECT id FROM components WHERE id IN ({placeholders})",
            component_ids,
        ).fetchall()
    finally:
        conn.close()

    known = {row[0] for row in rows}
    missing = [component_id for component_id in component_ids if component_id not in known]
    if not missing:
        return None
    return IngestQualityViolation(
        check_id="bridge_id_present_in_master",
        description="Component.id in Neo4j is missing from component master (identity binding)",
        sample=[{"component_id": component_id} for component_id in missing[:10]],
    )


def run_on_ingest_quality_gates(
    driver: Driver,
    contract: GraphContract | None = None,
    *,
    duckdb_path: str | Path = "data/bom.duckdb",
    database: str = DEFAULT_DATABASE,
) -> IngestQualityReport:
    """Execute quality.on_ingest checks declared in the Graph Contract."""
    contract = contract or get_graph_contract()
    checks = contract.on_ingest_checks()
    violations: list[IngestQualityViolation] = []

    l3_report = run_l3_audit(driver, database=database)
    check_map = {
        "intra_graph_endpoints_exist": {
            "invalid_edge_endpoints",
            "unknown_edge_type",
            "cross_graph_edge",
            "missing_node_id",
        },
        "domain_edge_allowed": {
            "domain_edge_ebom",
            "domain_edge_routing",
            "domain_edge_sourcing",
            "invalid_edge_endpoints",
        },
    }

    for check_name in checks:
        if check_name in check_map:
            ids = check_map[check_name]
            matched = [v for v in l3_report.cypher_violations if v.check_id in ids]
            if not matched and l3_report.payload_errors:
                matched = [
                    IngestQualityViolation(
                        check_id=check_name,
                        description="Payload validation failed during L3 audit",
                        sample=l3_report.payload_errors[:5],
                    )
                ]
            else:
                for item in matched:
                    violations.append(
                        IngestQualityViolation(
                            check_id=check_name,
                            description=item.description,
                            sample=item.sample,
                        )
                    )
        elif check_name == "bridge_id_present_in_master":
            with driver.session(database=database) as session:
                violation = _check_bridge_ids_in_master(session, duckdb_path=Path(duckdb_path))
            if violation is not None:
                violations.append(violation)
        else:
            violations.append(
                IngestQualityViolation(
                    check_id=check_name,
                    description="Unknown on_ingest quality gate",
                    sample=[],
                )
            )

    passed = l3_report.passed and not violations
    return IngestQualityReport(
        passed=passed,
        contract_version=contract.version,
        checks_run=list(checks),
        violations=violations,
    )


def format_ingest_quality_report(report: IngestQualityReport) -> str:
    lines = [f"Graph Contract ingest quality (v{report.contract_version})"]
    if report.passed:
        lines.append("  status: PASS")
        return "\n".join(lines)
    lines.append("  status: FAIL")
    for violation in report.violations:
        lines.append(f"  [{violation.check_id}] {violation.description}")
        for row in violation.sample[:3]:
            lines.append(f"    sample: {row}")
    return "\n".join(lines)


__all__ = [
    "IngestQualityReport",
    "IngestQualityViolation",
    "format_ingest_quality_report",
    "run_on_ingest_quality_gates",
]
