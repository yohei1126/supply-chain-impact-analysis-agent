from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pipeline.demo.sample_data import PROCESSES, PRODUCT_PROCESSES

if TYPE_CHECKING:
    from app.federation.graph_store import GraphStore


def seed_nodes(graph: GraphStore) -> int:
    """Load routing-owned process nodes."""
    for process in PROCESSES:
        graph.add_node("Process", process)
    return len(PROCESSES)


def seed_edges(
    graph: GraphStore,
    component_bom: list[dict[str, Any]],
    product_processes: list[tuple[str, str]] | None = None,
) -> int:
    """Load INPUT_OF and PRODUCED_BY edges into the routing domain graph."""
    count = 0
    pairs = product_processes if product_processes is not None else PRODUCT_PROCESSES

    for row in component_bom:
        component_id = row["component"]["id"]
        for process_id in row["processes"]:
            graph.add_edge(
                {
                    "source_label": "Component",
                    "source_id": component_id,
                    "target_label": "Process",
                    "target_id": process_id,
                    "edge_type": "INPUT_OF",
                    "properties": {"qty": 1},
                }
            )
            count += 1

    for product_id, process_id in pairs:
        graph.add_edge(
            {
                "source_label": "Product",
                "source_id": product_id,
                "target_label": "Process",
                "target_id": process_id,
                "edge_type": "PRODUCED_BY",
                "properties": {},
            }
        )
        count += 1
    return count
