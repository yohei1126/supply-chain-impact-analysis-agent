"""Run L3 post-load conformance audits against a live Neo4j graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.storage.neo4j_config import DEFAULT_DATABASE
from domains.registry import DOMAIN_GRAPHS, GraphId, assert_edge_allowed_in_graph
from ontology.l3_audit import L3Check, all_l3_checks
from ontology.schema import RelationEdge, ValidationError, validate_node_payload

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    Driver = Any  # type: ignore[misc, assignment]


@dataclass
class L3Violation:
    check_id: str
    description: str
    count: int
    sample: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class L3AuditReport:
    passed: bool
    cypher_violations: list[L3Violation] = field(default_factory=list)
    payload_errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        return len(self.cypher_violations) + len(self.payload_errors)


def _run_check(session: Any, check: L3Check) -> L3Violation | None:
    params = dict(check.parameters or {})
    result = session.run(check.cypher, **params)
    rows = [dict(record) for record in result]
    if not rows:
        return None
    return L3Violation(
        check_id=check.check_id,
        description=check.description,
        count=len(rows),
        sample=rows[:10],
    )


def _validate_node_payloads(session: Any) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    result = session.run(
        "MATCH (n) WHERE n.graph_id IS NOT NULL "
        "RETURN labels(n)[0] AS label, properties(n) AS props"
    )
    for record in result:
        label = record["label"]
        props = dict(record["props"])
        graph_id = props.get("graph_id")
        payload = {k: v for k, v in props.items() if k != "graph_id"}
        try:
            validate_node_payload(label, payload)
        except (ValidationError, ValueError) as exc:
            errors.append(
                {
                    "kind": "node_payload",
                    "label": label,
                    "id": props.get("id"),
                    "graph_id": graph_id,
                    "error": str(exc),
                }
            )
            if len(errors) >= 50:
                break
    return errors


def _validate_edge_payloads(session: Any) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    result = session.run(
        """
        MATCH (s)-[r]->(t)
        WHERE s.graph_id IS NOT NULL AND t.graph_id = s.graph_id
        RETURN
          labels(s)[0] AS source_label,
          s.id AS source_id,
          labels(t)[0] AS target_label,
          t.id AS target_id,
          type(r) AS edge_type,
          properties(r) AS properties,
          s.graph_id AS graph_id
        """
    )
    for record in result:
        row = {
            "source_label": record["source_label"],
            "source_id": record["source_id"],
            "target_label": record["target_label"],
            "target_id": record["target_id"],
            "edge_type": record["edge_type"],
            "properties": dict(record["properties"] or {}),
        }
        graph_id = record["graph_id"]
        try:
            RelationEdge(**row)
            assert_edge_allowed_in_graph(graph_id, row["edge_type"])  # type: ignore[arg-type]
        except (ValidationError, ValueError) as exc:
            errors.append(
                {
                    "kind": "edge_payload",
                    "graph_id": graph_id,
                    "edge_type": row["edge_type"],
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                    "error": str(exc),
                }
            )
            if len(errors) >= 50:
                break
    return errors


def run_l3_audit(
    driver: Driver,
    *,
    database: str = DEFAULT_DATABASE,
    graph_ids: tuple[GraphId, ...] | None = None,
) -> L3AuditReport:
    """Execute L3 Cypher checks and Pydantic re-validation on all scoped graph data."""
    del graph_ids  # reserved for future scoped audits
    checks = all_l3_checks({graph_id: spec for graph_id, spec in DOMAIN_GRAPHS.items()})
    cypher_violations: list[L3Violation] = []

    with driver.session(database=database) as session:
        for check in checks:
            violation = _run_check(session, check)
            if violation is not None:
                cypher_violations.append(violation)

        payload_errors = _validate_node_payloads(session)
        payload_errors.extend(_validate_edge_payloads(session))

    passed = not cypher_violations and not payload_errors
    return L3AuditReport(
        passed=passed,
        cypher_violations=cypher_violations,
        payload_errors=payload_errors,
    )


def format_report(report: L3AuditReport) -> str:
    lines = ["L3 Neo4j conformance audit"]
    if report.passed:
        lines.append("  status: PASS")
        return "\n".join(lines)

    lines.append("  status: FAIL")
    for violation in report.cypher_violations:
        lines.append(f"  [{violation.check_id}] {violation.description} ({violation.count} rows)")
        for row in violation.sample[:3]:
            lines.append(f"    sample: {row}")
    for error in report.payload_errors[:10]:
        kind = error["kind"]
        graph_id = error.get("graph_id")
        lines.append(f"  [payload] {kind} graph_id={graph_id}: {error['error']}")
    if len(report.payload_errors) > 10:
        lines.append(f"  ... {len(report.payload_errors) - 10} more payload errors")
    return "\n".join(lines)


__all__ = ["L3AuditReport", "L3Violation", "format_report", "run_l3_audit"]
