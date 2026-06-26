"""Batch-only Graph Contract on_ingest_audit checks (async steward pipeline)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.storage.neo4j_config import DEFAULT_DATABASE
from app.validation.contract_ingest import IngestQualityViolation, _check_bridge_ids_in_master
from app.validation.contract_loader import get_graph_contract
from ontology.contract.graph_contract import GraphContract

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    Driver = Any  # type: ignore[misc, assignment]


def _orphan_edge_endpoints(session: Any) -> IngestQualityViolation | None:
    result = session.run(
        """
        MATCH (s)-[r]->(t)
        WHERE s.graph_id IS NOT NULL
          AND (t.graph_id IS NULL OR t.graph_id <> s.graph_id)
        RETURN type(r) AS edge_type, s.graph_id AS graph_id,
               labels(s)[0] AS source_label, s.id AS source_id,
               labels(t)[0] AS target_label, t.id AS target_id
        LIMIT $sample_limit
        """,
        sample_limit=50,
    )
    rows = [dict(record) for record in result]
    if not rows:
        return None
    return IngestQualityViolation(
        check_id="orphan_edge_endpoints",
        description="Edge connects nodes with missing or mismatched graph_id (orphan endpoints)",
        sample=rows[:10],
    )


def _ingest_metadata_complete(session: Any) -> IngestQualityViolation | None:
    result = session.run(
        """
        MATCH (n)
        WHERE n.graph_id IS NOT NULL
          AND (
            n.as_of IS NULL OR n.as_of = ''
            OR n.graph_contract_version IS NULL OR n.graph_contract_version = ''
            OR n.source_system IS NULL OR n.source_system = ''
          )
        RETURN labels(n)[0] AS label, n.id AS id, n.graph_id AS graph_id,
               n.as_of AS as_of, n.graph_contract_version AS graph_contract_version,
               n.source_system AS source_system
        LIMIT $sample_limit
        """,
        sample_limit=50,
    )
    rows = [dict(record) for record in result]
    if not rows:
        return None
    return IngestQualityViolation(
        check_id="ingest_metadata_complete",
        description=(
            "Node is missing as_of, graph_contract_version, or source_system ingest metadata"
        ),
        sample=rows[:10],
    )


def _domain_edge_leakage(session: Any, contract: GraphContract) -> IngestQualityViolation | None:
    rows: list[dict[str, Any]] = []
    for graph_id, domain in contract.domains.items():
        result = session.run(
            """
            MATCH (s {graph_id: $graph_id})-[r]->(t {graph_id: $graph_id})
            WHERE NOT type(r) IN $allowed_edges
            RETURN $graph_id AS graph_id, type(r) AS edge_type,
                   labels(s)[0] AS source_label, s.id AS source_id,
                   labels(t)[0] AS target_label, t.id AS target_id
            LIMIT $sample_limit
            """,
            graph_id=graph_id,
            allowed_edges=sorted(domain.edges.keys()),
            sample_limit=50,
        )
        rows.extend(dict(record) for record in result)
    if not rows:
        return None
    return IngestQualityViolation(
        check_id="domain_edge_leakage",
        description="Edge type is not allowed in the domain graph (domain edge leakage)",
        sample=rows[:10],
    )


def run_on_ingest_audit_checks(
    driver: Driver,
    contract: GraphContract | None = None,
    *,
    duckdb_path: str | Path = "data/bom.duckdb",
    duckdb_conn: Any | None = None,
    database: str = DEFAULT_DATABASE,
) -> tuple[list[str], list[IngestQualityViolation]]:
    """Execute quality.on_ingest_audit batch checks for data stewards."""
    contract = contract or get_graph_contract()
    checks = contract.on_ingest_audit_checks()
    violations: list[IngestQualityViolation] = []

    with driver.session(database=database) as session:
        for check_name in checks:
            if check_name == "orphan_edge_endpoints":
                violation = _orphan_edge_endpoints(session)
            elif check_name == "ingest_metadata_complete":
                violation = _ingest_metadata_complete(session)
            elif check_name == "bridge_id_present_in_master":
                violation = _check_bridge_ids_in_master(
                    session,
                    duckdb_path=Path(duckdb_path),
                    duckdb_conn=duckdb_conn,
                )
            elif check_name == "domain_edge_leakage":
                violation = _domain_edge_leakage(session, contract)
            else:
                violations.append(
                    IngestQualityViolation(
                        check_id=check_name,
                        description="Unknown on_ingest_audit quality gate",
                        sample=[],
                    )
                )
                continue
            if violation is not None:
                violations.append(violation)

    return list(checks), violations


__all__ = ["run_on_ingest_audit_checks"]
