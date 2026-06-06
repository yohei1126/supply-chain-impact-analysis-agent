"""Domain-scoped queries, federated disruption analysis, and mitigations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.federation.graph_store import LanceGraphStore

GraphId = Literal["sourcing", "ebom", "routing"]


@dataclass(frozen=True)
class DomainQueryResult:
    graph_id: GraphId
    query_name: str
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


def query_sourcing_for_supplier(store: LanceGraphStore, supplier_id: str) -> DomainQueryResult:
    sourcing = store.domain("sourcing")
    suppliers = [n for n in sourcing.all_nodes() if n["label"] == "Supplier" and n["id"] == supplier_id]
    supplier = suppliers[0]["properties"] if suppliers else {}
    components: list[dict[str, Any]] = []
    for edge in sourcing.all_edges():
        if (
            edge["edge_type"] == "SUPPLIED_BY"
            and edge["target_id"] == supplier_id
            and edge["target_label"] == "Supplier"
        ):
            comp_id = edge["source_id"]
            comp_nodes = [n for n in sourcing.all_nodes() if n["label"] == "Component" and n["id"] == comp_id]
            comp = comp_nodes[0]["properties"] if comp_nodes else {}
            components.append(
                {
                    "component_id": comp_id,
                    "component_name": comp.get("name"),
                    "material": comp.get("material"),
                    "cost": comp.get("cost"),
                    "lead_time_days": edge["properties"].get("lead_time_days"),
                    "supplier_id": supplier_id,
                    "supplier_name": supplier.get("company_name"),
                    "country": supplier.get("country"),
                    "risk_level": supplier.get("risk_level"),
                }
            )
    components.sort(key=lambda r: r.get("cost") or 0, reverse=True)
    return DomainQueryResult(
        graph_id="sourcing",
        query_name="components_by_supplier",
        summary=f"Sourcing graph: {len(components)} components supplied by {supplier_id}",
        rows=components,
    )


def query_ebom_for_components(
    store: LanceGraphStore, component_ids: set[str]
) -> DomainQueryResult:
    ebom = store.domain("ebom")
    rows: list[dict[str, Any]] = []
    for edge in ebom.all_edges():
        if edge["edge_type"] == "USED_IN" and edge["source_id"] in component_ids:
            product_nodes = [
                n for n in ebom.all_nodes() if n["label"] == "Product" and n["id"] == edge["target_id"]
            ]
            product = product_nodes[0]["properties"] if product_nodes else {}
            rows.append(
                {
                    "component_id": edge["source_id"],
                    "product_id": edge["target_id"],
                    "product_name": product.get("name"),
                    "product_version": product.get("version"),
                }
            )
    rows.sort(key=lambda r: (r["product_id"], r["component_id"]))
    return DomainQueryResult(
        graph_id="ebom",
        query_name="products_by_components",
        summary=f"EBOM graph: {len(rows)} component-to-product links",
        rows=rows,
    )


def query_routing_for_components(
    store: LanceGraphStore, component_ids: set[str]
) -> DomainQueryResult:
    routing = store.domain("routing")
    rows: list[dict[str, Any]] = []
    for edge in routing.all_edges():
        if edge["edge_type"] == "INPUT_OF" and edge["source_id"] in component_ids:
            process_nodes = [
                n for n in routing.all_nodes() if n["label"] == "Process" and n["id"] == edge["target_id"]
            ]
            process = process_nodes[0]["properties"] if process_nodes else {}
            rows.append(
                {
                    "component_id": edge["source_id"],
                    "process_id": edge["target_id"],
                    "process_name": process.get("name"),
                    "work_center": process.get("work_center"),
                    "cycle_time_min": process.get("cycle_time_min"),
                }
            )
    rows.sort(key=lambda r: (r.get("work_center") or "", r["component_id"]))
    return DomainQueryResult(
        graph_id="routing",
        query_name="processes_by_components",
        summary=f"Routing graph: {len(rows)} component-to-process links",
        rows=rows,
    )


def _single_source_components(store: LanceGraphStore, component_ids: set[str]) -> set[str]:
    supplier_count: dict[str, int] = {}
    for edge in store.domain("sourcing").all_edges():
        if edge["edge_type"] == "SUPPLIED_BY" and edge["source_id"] in component_ids:
            supplier_count[edge["source_id"]] = supplier_count.get(edge["source_id"], 0) + 1
    return {cid for cid, count in supplier_count.items() if count == 1}


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


def analyze_supplier_disruption(store: LanceGraphStore, supplier_id: str) -> FederatedAnalysis:
    """
    Federate sourcing → ebom → routing on Component.id for a supplier disruption scenario.
    """
    sourcing = query_sourcing_for_supplier(store, supplier_id)
    component_ids = {r["component_id"] for r in sourcing.rows}
    ebom = query_ebom_for_components(store, component_ids)
    routing = query_routing_for_components(store, component_ids)
    single_source = _single_source_components(store, component_ids)

    federated_rows = store.impacted_products_by_supplier(supplier_id)
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
