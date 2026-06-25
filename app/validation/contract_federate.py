"""Graph Contract quality.on_federate checks for federation compose."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.validation.contract_loader import get_graph_contract
from ontology.contract.graph_contract import GraphContract


@dataclass
class DomainSnapshot:
    graph_id: str
    as_of: str | None
    row_count: int


@dataclass
class FederateQualityWarning:
    rule_id: str
    message: str


@dataclass
class FederateQualityViolation:
    rule_id: str
    message: str
    sample: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FederateQualityReport:
    passed: bool
    contract_version: str
    rules_run: list[str] = field(default_factory=list)
    warnings: list[FederateQualityWarning] = field(default_factory=list)
    violations: list[FederateQualityViolation] = field(default_factory=list)


def _parse_as_of(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _check_as_of_skew(
    snapshots: list[DomainSnapshot],
    *,
    max_skew_hours: int,
) -> FederateQualityWarning | None:
    timestamps: list[tuple[str, datetime]] = []
    for snapshot in snapshots:
        parsed = _parse_as_of(snapshot.as_of)
        if parsed is not None:
            timestamps.append((snapshot.graph_id, parsed))
    if len(timestamps) < 2:
        return None

    newest = max(timestamps, key=lambda item: item[1])
    oldest = min(timestamps, key=lambda item: item[1])
    skew_hours = (newest[1] - oldest[1]).total_seconds() / 3600.0
    if skew_hours <= max_skew_hours:
        return None

    return FederateQualityWarning(
        rule_id="warn_if_as_of_skew_hours",
        message=(
            f"Domain as_of skew is {skew_hours:.1f}h "
            f"(oldest={oldest[0]}, newest={newest[0]}; limit={max_skew_hours}h)."
        ),
    )


def _check_master_ids_present(
    component_ids: set[str],
    *,
    duckdb_path: Path | None = None,
    duckdb_conn: Any | None = None,
) -> FederateQualityViolation | None:
    if not component_ids:
        return None

    should_close = False
    if duckdb_conn is not None:
        conn = duckdb_conn
    elif duckdb_path is not None and duckdb_path.is_file():
        import duckdb

        conn = duckdb.connect(str(duckdb_path), read_only=True)
        should_close = True
    else:
        return None

    try:
        placeholders = ", ".join("?" for _ in component_ids)
        rows = conn.execute(
            f"SELECT id FROM components WHERE id IN ({placeholders})",
            list(component_ids),
        ).fetchall()
    finally:
        if should_close:
            conn.close()

    present = {row[0] for row in rows}
    missing = sorted(component_ids - present)
    if not missing:
        return None

    return FederateQualityViolation(
        rule_id="reject_join_if_master_missing",
        message=f"{len(missing)} component id(s) missing from component master.",
        sample=[{"missing_component_ids": missing[:20]}],
    )


def run_on_federate_quality_gates(
    *,
    domain_snapshots: list[DomainSnapshot],
    component_ids: set[str],
    contract: GraphContract | None = None,
    duckdb_path: str | Path = "data/bom.duckdb",
    duckdb_conn: Any | None = None,
) -> FederateQualityReport:
    """Apply Graph Contract quality.on_federate rules."""
    contract = contract or get_graph_contract()
    rules = contract.on_federate_rules()
    rules_run: list[str] = []
    warnings: list[FederateQualityWarning] = []
    violations: list[FederateQualityViolation] = []

    skew_hours = rules.get("warn_if_as_of_skew_hours")
    if isinstance(skew_hours, int):
        rules_run.append("warn_if_as_of_skew_hours")
        warning = _check_as_of_skew(domain_snapshots, max_skew_hours=skew_hours)
        if warning is not None:
            warnings.append(warning)

    reject_missing = rules.get("reject_join_if_master_missing")
    if reject_missing:
        rules_run.append("reject_join_if_master_missing")
        violation = _check_master_ids_present(
            component_ids,
            duckdb_path=Path(duckdb_path),
            duckdb_conn=duckdb_conn,
        )
        if violation is not None:
            violations.append(violation)

    return FederateQualityReport(
        passed=not violations,
        contract_version=contract.version,
        rules_run=rules_run,
        warnings=warnings,
        violations=violations,
    )
