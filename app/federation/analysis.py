"""Domain-scoped Cypher queries, federated disruption analysis, and mitigations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.federation.cypher_executor import execute_domain_cypher
from app.federation.cypher_queries import (
    ONTOLOGY_SOURCE,
    cypher_components_by_supplier,
    cypher_impact_by_components,
    cypher_processes_by_components,
    cypher_products_by_components,
    cypher_supplier_counts,
)
from app.federation.graph_store import GraphStore

GraphId = Literal["sourcing", "ebom", "routing"]


@dataclass(frozen=True)
class DomainQueryResult:
    graph_id: GraphId
    query_name: str
    cypher: str
    summary: str
    rows: list[dict[str, Any]]


@dataclass
class ProblemFinding:
    severity: Literal["high", "medium", "low"]
    category: str
    message: str
    evidence: dict[str, Any]


@dataclass
class MitigationAction:
    priority: int
    action: str
    owner_team: str
    evidence: str


@dataclass
class FederatedAnalysis:
    scenario: str
    supplier_id: str
    domain_queries: list[DomainQueryResult] = field(default_factory=list)
    problems: list[ProblemFinding] = field(default_factory=list)
    mitigations: list[MitigationAction] = field(default_factory=list)
    impact_score: float = 0.0
    federated_rows: list[dict[str, Any]] = field(default_factory=list)


def query_sourcing_for_supplier(store: GraphStore, supplier_id: str) -> DomainQueryResult:
    supplier_id = supplier_id.strip()
    cypher = cypher_components_by_supplier()
    rows = execute_domain_cypher(
        store.domain("sourcing"),
        "sourcing",
        cypher,
        parameters={"supplier_id": supplier_id},
    )
    return DomainQueryResult(
        graph_id="sourcing",
        query_name="components_by_supplier",
        cypher=cypher,
        summary=f"Sourcing graph: {len(rows)} components supplied by {supplier_id}",
        rows=rows,
    )


def query_ebom_for_components(
    store: GraphStore, component_ids: set[str]
) -> DomainQueryResult:
    if not component_ids:
        return DomainQueryResult(
            graph_id="ebom",
            query_name="products_by_components",
            cypher="/* skipped: no component_ids */",
            summary="EBOM graph: 0 component-to-product links",
            rows=[],
        )
    cypher = cypher_products_by_components(component_ids)
    rows = execute_domain_cypher(store.domain("ebom"), "ebom", cypher)
    return DomainQueryResult(
        graph_id="ebom",
        query_name="products_by_components",
        cypher=cypher,
        summary=f"EBOM graph: {len(rows)} component-to-product links",
        rows=rows,
    )


def query_routing_for_components(
    store: GraphStore, component_ids: set[str]
) -> DomainQueryResult:
    if not component_ids:
        return DomainQueryResult(
            graph_id="routing",
            query_name="processes_by_components",
            cypher="/* skipped: no component_ids */",
            summary="Routing graph: 0 component-to-process links",
            rows=[],
        )
    cypher = cypher_processes_by_components(component_ids)
    rows = execute_domain_cypher(store.domain("routing"), "routing", cypher)
    return DomainQueryResult(
        graph_id="routing",
        query_name="processes_by_components",
        cypher=cypher,
        summary=f"Routing graph: {len(rows)} component-to-process links",
        rows=rows,
    )


def _single_source_components(store: GraphStore, component_ids: set[str]) -> set[str]:
    if not component_ids:
        return set()
    cypher = cypher_supplier_counts(component_ids)
    rows = execute_domain_cypher(store.domain("sourcing"), "sourcing", cypher)
    return {row["component_id"] for row in rows if (row.get("supplier_count") or 0) == 1}


def _build_problems(
    sourcing: DomainQueryResult,
    ebom: DomainQueryResult,
    routing: DomainQueryResult,
    single_source: set[str],
    supplier_id: str,
) -> list[ProblemFinding]:
    problems: list[ProblemFinding] = []
    if not sourcing.rows:
        problems.append(
            ProblemFinding(
                severity="high",
                category="no_supply",
                message="No components found for the disrupted supplier in the sourcing graph.",
                evidence={"supplier_id": supplier_id},
            )
        )
        return problems

    supplier_meta = sourcing.rows[0]
    if supplier_meta.get("risk_level") == "High":
        problems.append(
            ProblemFinding(
                severity="high",
                category="supplier_risk",
                message=(
                    f"Supplier {supplier_meta.get('supplier_name')} ({supplier_meta.get('supplier_id')}) "
                    f"is already classified High risk ({supplier_meta.get('country')})."
                ),
                evidence={
                    "supplier_id": supplier_meta.get("supplier_id"),
                    "risk_level": supplier_meta.get("risk_level"),
                },
            )
        )

    long_lead = [r for r in sourcing.rows if (r.get("lead_time_days") or 0) >= 18]
    if long_lead:
        problems.append(
            ProblemFinding(
                severity="medium",
                category="lead_time",
                message=f"{len(long_lead)} affected components have lead time >= 18 days.",
                evidence={"component_ids": [r["component_id"] for r in long_lead]},
            )
        )

    if single_source:
        problems.append(
            ProblemFinding(
                severity="high",
                category="single_source",
                message=f"{len(single_source)} affected components have only one registered supplier.",
                evidence={"component_ids": sorted(single_source)},
            )
        )

    product_ids = {r["product_id"] for r in ebom.rows}
    if len(product_ids) >= 2:
        problems.append(
            ProblemFinding(
                severity="medium",
                category="product_spread",
                message=f"Disruption reaches {len(product_ids)} finished goods across the EBOM graph.",
                evidence={"product_ids": sorted(product_ids)},
            )
        )

    work_centers = {r["work_center"] for r in routing.rows if r.get("work_center")}
    if work_centers:
        problems.append(
            ProblemFinding(
                severity="medium",
                category="manufacturing",
                message=f"Routing graph shows impact on work centers: {', '.join(sorted(work_centers))}.",
                evidence={"work_centers": sorted(work_centers)},
            )
        )
    return problems


def _build_mitigations(
    sourcing: DomainQueryResult,
    ebom: DomainQueryResult,
    routing: DomainQueryResult,
    single_source: set[str],
    supplier_id: str,
) -> list[MitigationAction]:
    actions: list[MitigationAction] = []
    priority = 1

    if single_source:
        for row in sourcing.rows:
            if row["component_id"] in single_source:
                actions.append(
                    MitigationAction(
                        priority=priority,
                        action=(
                            f"Qualify alternate supplier for {row['component_id']} "
                            f"({row['component_name']}); only {supplier_id} on record."
                        ),
                        owner_team="procurement",
                        evidence=f"lead_time_days={row.get('lead_time_days')}, cost={row.get('cost')}",
                    )
                )
                priority += 1

    high_cost = sorted(sourcing.rows, key=lambda r: r.get("cost") or 0, reverse=True)[:2]
    for row in high_cost:
        product_hits = [r for r in ebom.rows if r["component_id"] == row["component_id"]]
        if product_hits:
            actions.append(
                MitigationAction(
                    priority=priority,
                    action=(
                        f"Assess ECO or substitute material for {row['component_id']} "
                        f"({row['component_name']}) affecting {product_hits[0]['product_name']}."
                    ),
                    owner_team="engineering",
                    evidence=f"USED_IN -> {product_hits[0]['product_id']}",
                )
            )
            priority += 1

    wc_rows = {r["work_center"]: r for r in routing.rows if r.get("work_center")}
    for wc, row in sorted(wc_rows.items()):
        actions.append(
            MitigationAction(
                priority=priority,
                action=f"Reschedule or outsource {wc} ({row['process_name']}) while components are delayed.",
                owner_team="manufacturing",
                evidence=f"INPUT_OF {row['component_id']} -> {row['process_id']}",
            )
        )
        priority += 1

    product_ids = sorted({r["product_id"] for r in ebom.rows})
    if product_ids:
        actions.append(
            MitigationAction(
                priority=priority,
                action=f"Notify program office for products: {', '.join(product_ids)}.",
                owner_team="program_management",
                evidence=f"{len(sourcing.rows)} components from disrupted supplier",
            )
        )
    return actions


def _impact_score(
    sourcing: DomainQueryResult,
    ebom: DomainQueryResult,
    single_source: set[str],
) -> float:
    product_count = len({r["product_id"] for r in ebom.rows})
    total_cost = sum(r.get("cost") or 0 for r in sourcing.rows)
    single_count = len(single_source)
    min_lead = min((r.get("lead_time_days") or 99 for r in sourcing.rows), default=99)
    stockout_factor = max(0.0, 30 - min_lead)
    return round(
        1.0 * product_count + 0.001 * total_cost + 2.0 * single_count + 0.5 * stockout_factor,
        2,
    )


def federated_impact_rows(store: GraphStore, supplier_id: str) -> list[dict[str, Any]]:
    """Join sourcing + ebom on Component.id using two Cypher queries."""
    sourcing = query_sourcing_for_supplier(store, supplier_id)
    component_ids = {row["component_id"] for row in sourcing.rows}
    if not component_ids:
        return []

    cypher = cypher_impact_by_components(component_ids)
    ebom_rows = execute_domain_cypher(store.domain("ebom"), "ebom", cypher)
    sourcing_by_component = {row["component_id"]: row for row in sourcing.rows}

    output: list[dict[str, Any]] = []
    for row in ebom_rows:
        source = sourcing_by_component.get(row["component_id"], {})
        output.append(
            {
                "supplier_id": supplier_id,
                "component_id": row["component_id"],
                "component_name": row.get("component_name") or source.get("component_name"),
                "product_id": row["product_id"],
                "product_name": row.get("product_name"),
                "component_cost": row.get("component_cost") or source.get("cost"),
            }
        )
    return output


def analyze_supplier_disruption(store: GraphStore, supplier_id: str) -> FederatedAnalysis:
    """
    Federate sourcing → ebom → routing on Component.id for a supplier disruption scenario.
    Each domain step runs Cypher via Neo4j; federation joins results in Python.
    """
    sourcing = query_sourcing_for_supplier(store, supplier_id)
    component_ids = {r["component_id"] for r in sourcing.rows}
    ebom = query_ebom_for_components(store, component_ids)
    routing = query_routing_for_components(store, component_ids)
    single_source = _single_source_components(store, component_ids)

    federated_rows = federated_impact_rows(store, supplier_id)
    problems = _build_problems(sourcing, ebom, routing, single_source, supplier_id)
    mitigations = _build_mitigations(sourcing, ebom, routing, single_source, supplier_id)
    score = _impact_score(sourcing, ebom, single_source)

    return FederatedAnalysis(
        scenario=f"supplier_disruption:{supplier_id}",
        supplier_id=supplier_id,
        domain_queries=[sourcing, ebom, routing],
        problems=problems,
        mitigations=mitigations,
        impact_score=score,
        federated_rows=federated_rows,
    )
