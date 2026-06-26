from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.federation.analysis import federated_impact_rows, query_sourcing_for_supplier
from app.federation.cypher_executor import execute_domain_cypher
from app.federation.cypher_queries import (
    ONTOLOGY_SOURCE,
    cypher_direct_supply_path,
    cypher_impact_by_components,
)

ExplorationMode = Literal["supplier_impact", "supply_path"]


@dataclass
class CypherStep:
    graph_id: str
    query_name: str
    cypher: str


@dataclass
class ExplorationResult:
    operation: str
    summary: str
    data: list[dict[str, Any]]
    ontology_source: str = ONTOLOGY_SOURCE
    cypher: str = ""
    cypher_queries: list[CypherStep] = field(default_factory=list)


class GraphExplorer:
    """
    Framework-facing graph exploration API.

    Domain queries are generated from ontology/schema.py and executed via Neo4j Cypher.
    Agent Skill prose lives under skills/bom-graph-explorer/.
    """

    def __init__(
        self,
        store: Any,
        *,
        duckdb_path: str = "data/bom.duckdb",
        duckdb_conn: Any | None = None,
    ):
        self.store = store
        self.duckdb_path = duckdb_path
        self.duckdb_conn = duckdb_conn

    def supplier_impact(self, supplier_id: str) -> ExplorationResult:
        supplier_id = supplier_id.strip()
        sourcing = query_sourcing_for_supplier(self.store, supplier_id)
        component_ids = {row["component_id"] for row in sourcing.rows}
        steps = [
            CypherStep("sourcing", sourcing.query_name, sourcing.cypher),
        ]
        if component_ids:
            impact_cypher = cypher_impact_by_components(component_ids)
            steps.append(CypherStep("ebom", "impact_products_by_components", impact_cypher))

        rows = federated_impact_rows(
            self.store,
            supplier_id,
            duckdb_path=self.duckdb_path,
            duckdb_conn=self.duckdb_conn,
        )
        return ExplorationResult(
            operation="supplier_impact",
            summary=f"Downstream impact for supplier {supplier_id} (Cypher on sourcing → ebom)",
            data=rows,
            cypher=steps[0].cypher if steps else "",
            cypher_queries=steps,
        )

    def supply_path(self, from_component_id: str, to_product_id: str) -> ExplorationResult:
        from_component_id = from_component_id.strip()
        to_product_id = to_product_id.strip()
        cypher = cypher_direct_supply_path(from_component_id, to_product_id)
        steps = [
            CypherStep("ebom", "direct_component_product_link", cypher),
        ]

        direct_rows = execute_domain_cypher(
            self.store.domain("ebom"),
            "ebom",
            cypher,
        )
        if direct_rows:
            return ExplorationResult(
                operation="supply_path",
                summary=(
                    f"Direct USED_IN path from {from_component_id} to {to_product_id} (ebom Cypher)"
                ),
                data=[
                    {
                        "nodes": [
                            {"labels": ["Component"], "id": from_component_id},
                            {"labels": ["Product"], "id": to_product_id},
                        ],
                        "relationships": [direct_rows[0].get("edge_type", "USED_IN")],
                    }
                ],
                cypher=cypher,
                cypher_queries=steps,
            )

        # Fall back to federated BFS across ebom + routing when no direct USED_IN link exists.
        fallback = self.store.shortest_supply_path(from_component_id, to_product_id)
        steps.append(
            CypherStep(
                "federated",
                "shortest_path_bfs_fallback",
                "/* no direct USED_IN link; Python BFS over ebom+routing "
                "(USED_IN, INPUT_OF, PRODUCED_BY) */",
            )
        )
        return ExplorationResult(
            operation="supply_path",
            summary=(
                f"Multi-hop path from {from_component_id} to {to_product_id} "
                f"(BFS fallback after ebom Cypher returned no rows)"
            ),
            data=fallback,
            cypher=cypher,
            cypher_queries=steps,
        )

    def run(self, mode: ExplorationMode, **kwargs: Any) -> ExplorationResult:
        if mode == "supplier_impact":
            return self.supplier_impact(kwargs["supplier_id"])
        if mode == "supply_path":
            return self.supply_path(kwargs["from_component_id"], kwargs["to_product_id"])
        raise ValueError(f"Unknown exploration mode: {mode}")
