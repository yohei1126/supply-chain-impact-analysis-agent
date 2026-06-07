from __future__ import annotations

from typing import Any, TYPE_CHECKING

from pipeline.demo.sample_data import SUPPLIERS

if TYPE_CHECKING:
    from app.federation.graph_store import GraphStore


def seed_nodes(graph: GraphStore) -> int:
    """Load sourcing-owned supplier nodes."""
    for supplier in SUPPLIERS:
        graph.add_node("Supplier", supplier)
    return len(SUPPLIERS)


def seed_edges(graph: GraphStore, component_bom: list[dict[str, Any]]) -> int:
    """Load SUPPLIED_BY edges into the sourcing domain graph."""
    count = 0
    for row in component_bom:
        component_id = row["component"]["id"]
        graph.add_edge(
            {
                "source_label": "Component",
                "source_id": component_id,
                "target_label": "Supplier",
                "target_id": row["supplier"],
                "edge_type": "SUPPLIED_BY",
                "properties": {"lead_time_days": row.get("lead_time_days", 14)},
            }
        )
        count += 1
    return count
