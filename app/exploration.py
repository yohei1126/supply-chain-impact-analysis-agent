from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ExplorationMode = Literal["supplier_impact", "supply_path"]


@dataclass
class ExplorationResult:
    operation: str
    summary: str
    data: list[dict[str, Any]]


class GraphExplorer:
    """
    Framework-facing graph exploration API.

    Domain rules and agent instructions live in the distributable Agent Skill
    under `skills/bom-graph-explorer/`, not in this module.
    """

    def __init__(self, store: Any):
        self.store = store

    def supplier_impact(self, supplier_id: str) -> ExplorationResult:
        rows = self.store.impacted_products_by_supplier(supplier_id)
        return ExplorationResult(
            operation="supplier_impact",
            summary=f"Downstream impact for supplier {supplier_id}",
            data=rows,
        )

    def supply_path(self, from_component_id: str, to_product_id: str) -> ExplorationResult:
        rows = self.store.shortest_supply_path(from_component_id, to_product_id)
        return ExplorationResult(
            operation="supply_path",
            summary=f"Shortest path from {from_component_id} to {to_product_id}",
            data=rows,
        )

    def run(self, mode: ExplorationMode, **kwargs: Any) -> ExplorationResult:
        if mode == "supplier_impact":
            return self.supplier_impact(kwargs["supplier_id"])
        if mode == "supply_path":
            return self.supply_path(kwargs["from_component_id"], kwargs["to_product_id"])
        raise ValueError(f"Unknown exploration mode: {mode}")
