from __future__ import annotations

from typing import Any, TYPE_CHECKING

from pipeline.demo.sample_data import PRODUCTS

if TYPE_CHECKING:
    from app.federation.graph_store import LanceGraphStore


def seed_nodes(graph: LanceGraphStore) -> int:
    """Load EBOM-owned product nodes (also replicated into routing by the facade)."""
    for product in PRODUCTS:
        graph.add_node("Product", product)
    return len(PRODUCTS)


def seed_edges(graph: LanceGraphStore, component_bom: list[dict[str, Any]]) -> int:
    """Load USED_IN edges into the ebom domain graph."""
    count = 0
    for row in component_bom:
        component_id = row["component"]["id"]
        for product_id in row["products"]:
            graph.add_edge(
                {
                    "source_label": "Component",
                    "source_id": component_id,
                    "target_label": "Product",
                    "target_id": product_id,
                    "edge_type": "USED_IN",
                    "properties": {},
                }
            )
            count += 1
    return count
