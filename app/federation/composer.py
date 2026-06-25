"""Federation composer: contract-driven joins, graph_view seeds, on_federate gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.federation.cypher_executor import execute_domain_cypher
from app.federation.cypher_queries import cypher_components_by_supplier, cypher_impact_by_components
from app.federation.graph_store import GraphStore
from app.graph_viz import build_graph_view
from app.validation.contract_federate import (
    DomainSnapshot,
    FederateQualityReport,
    run_on_federate_quality_gates,
)
from app.validation.contract_loader import get_graph_contract
from domains.registry import GraphId
from ontology.contract.graph_contract import FederationJoin, FederationStep, GraphContract

DEFAULT_SUPPLIER_JOIN = "supplier_to_products"


@dataclass
class FederationComposeResult:
    join_name: str
    contract_version: str
    federated_rows: list[dict[str, Any]] = field(default_factory=list)
    domain_snapshots: list[DomainSnapshot] = field(default_factory=list)
    domain_queries: list[Any] = field(default_factory=list)
    join_plan: list[dict[str, Any]] = field(default_factory=list)
    graph_view: dict[str, Any] = field(default_factory=dict)
    quality: FederateQualityReport | None = None
    passed: bool = True


def read_domain_as_of(store: GraphStore, graph_id: GraphId) -> str | None:
    with store.driver.session(database=store.domain(graph_id).database) as session:
        record = session.run(
            "MATCH (n {graph_id: $graph_id}) WHERE n.as_of IS NOT NULL "
            "RETURN max(n.as_of) AS as_of",
            graph_id=graph_id,
        ).single()
        if record is None:
            return None
        value = record.get("as_of")
        return str(value) if value is not None else None


def join_plan_steps(join: FederationJoin) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for index, step in enumerate(join.steps, start=1):
        steps.append(
            {
                "step": index,
                "graph_id": step.domain,
                "edge": step.edge,
                "direction": step.direction,
                "from": step.from_ref,
                "yields": step.yields,
                "description": (
                    f"{step.domain} {step.edge}"
                    + (f" ({step.direction})" if step.direction else "")
                ),
            }
        )
    return steps


def merge_supplier_to_products_rows(
    supplier_id: str,
    sourcing_rows: list[dict[str, Any]],
    ebom_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sourcing_by_component = {row["component_id"]: row for row in sourcing_rows}
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


def _execute_join_step(
    store: GraphStore,
    step: FederationStep,
    context: dict[str, Any],
) -> Any:
    from app.federation.analysis import DomainQueryResult

    if step.domain == "sourcing" and step.edge == "SUPPLIED_BY" and step.direction == "reverse":
        supplier_id = str(context["supplier_id"])
        cypher = cypher_components_by_supplier()
        rows = execute_domain_cypher(
            store.domain("sourcing"),
            "sourcing",
            cypher,
            parameters={"supplier_id": supplier_id},
        )
        result = DomainQueryResult(
            graph_id="sourcing",
            query_name="components_by_supplier",
            cypher=cypher,
            summary=f"Sourcing graph: {len(rows)} components supplied by {supplier_id}",
            rows=rows,
        )
        context[step.yields] = {row["component_id"] for row in result.rows}
        return result

    if step.domain == "ebom" and step.edge == "USED_IN":
        from_key = step.from_ref or "component_id"
        component_ids = set(context.get(from_key) or [])
        if not component_ids:
            return DomainQueryResult(
                graph_id="ebom",
                query_name="products_by_components",
                cypher="/* skipped: no component_ids */",
                summary="EBOM graph: 0 component-to-product links",
                rows=[],
            )
        cypher = cypher_impact_by_components(component_ids)
        rows = execute_domain_cypher(store.domain("ebom"), "ebom", cypher)
        context[step.yields] = {row["product_id"] for row in rows}
        return DomainQueryResult(
            graph_id="ebom",
            query_name="impact_by_components",
            cypher=cypher,
            summary=f"EBOM graph: {len(rows)} component-to-product links",
            rows=rows,
        )

    raise ValueError(
        f"Unsupported federation step: domain={step.domain}, edge={step.edge}, "
        f"direction={step.direction}"
    )


def _build_domain_snapshots(
    store: GraphStore,
    domain_queries: list[Any],
) -> list[DomainSnapshot]:
    snapshots: list[DomainSnapshot] = []
    seen: set[str] = set()
    for query in domain_queries:
        if query.graph_id in seen:
            continue
        seen.add(query.graph_id)
        snapshots.append(
            DomainSnapshot(
                graph_id=query.graph_id,
                as_of=read_domain_as_of(store, query.graph_id),
                row_count=len(query.rows),
            )
        )
    return snapshots


def _graph_view_for_rows(store: GraphStore, federated_rows: list[dict[str, Any]]) -> dict[str, Any]:
    seeds: set[tuple[str, str]] = set()
    for row in federated_rows:
        supplier_id = row.get("supplier_id")
        component_id = row.get("component_id")
        product_id = row.get("product_id")
        if supplier_id:
            seeds.add(("Supplier", str(supplier_id)))
        if component_id:
            seeds.add(("Component", str(component_id)))
        if product_id:
            seeds.add(("Product", str(product_id)))
    if not seeds:
        return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}
    return build_graph_view(store, seeds, expand_hops=1)


def compose_join(
    store: GraphStore,
    join_name: str,
    *,
    seed: dict[str, Any],
    duckdb_path: str | Path = "data/bom.duckdb",
    duckdb_conn: Any | None = None,
    contract: GraphContract | None = None,
) -> FederationComposeResult:
    """Execute a Graph Contract federation join and apply on_federate quality gates."""
    contract = contract or get_graph_contract()
    join = contract.join_plan(join_name)
    context = dict(seed)
    domain_queries: list[Any] = []

    for step in join.steps:
        domain_queries.append(_execute_join_step(store, step, context))

    component_ids = set(context.get("component_id") or [])
    domain_snapshots = _build_domain_snapshots(store, domain_queries)
    quality = run_on_federate_quality_gates(
        domain_snapshots=domain_snapshots,
        component_ids=component_ids,
        contract=contract,
        duckdb_path=duckdb_path,
        duckdb_conn=duckdb_conn,
    )

    federated_rows: list[dict[str, Any]] = []
    if quality.passed and join_name == DEFAULT_SUPPLIER_JOIN:
        supplier_id = str(seed["supplier_id"])
        sourcing_rows = domain_queries[0].rows if domain_queries else []
        ebom_rows = domain_queries[1].rows if len(domain_queries) > 1 else []
        federated_rows = merge_supplier_to_products_rows(supplier_id, sourcing_rows, ebom_rows)

    graph_view = _graph_view_for_rows(store, federated_rows)

    return FederationComposeResult(
        join_name=join_name,
        contract_version=contract.version,
        federated_rows=federated_rows,
        domain_snapshots=domain_snapshots,
        domain_queries=domain_queries,
        join_plan=join_plan_steps(join),
        graph_view=graph_view,
        quality=quality,
        passed=quality.passed,
    )


def compose_supplier_disruption(
    store: GraphStore,
    supplier_id: str,
    *,
    duckdb_path: str | Path = "data/bom.duckdb",
    duckdb_conn: Any | None = None,
) -> FederationComposeResult:
    """Convenience wrapper for the default supplier → products federation join."""
    return compose_join(
        store,
        DEFAULT_SUPPLIER_JOIN,
        seed={"supplier_id": supplier_id},
        duckdb_path=duckdb_path,
        duckdb_conn=duckdb_conn,
    )
