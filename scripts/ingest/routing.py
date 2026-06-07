#!/usr/bin/env python3
"""Demo ingest for the routing domain graph (manufacturing / MES pipeline)."""

from __future__ import annotations

from pathlib import Path

from app.federation.graph_store import GraphStore
from domains.routing import pipeline as routing_pipeline
from pipeline.demo.sample_data import COMPONENT_BOM, PRODUCT_PROCESSES, PRODUCTS


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = GraphStore()
    try:
        process_count = routing_pipeline.seed_nodes(graph)
        for product in PRODUCTS:
            graph.add_node("Product", product)

        for row in COMPONENT_BOM:
            graph.add_node("Component", row["component"])

        edges = routing_pipeline.seed_edges(graph, COMPONENT_BOM, PRODUCT_PROCESSES)
        print(f"routing domain: {process_count} process nodes, {edges} routing edges")
    finally:
        graph.close()


if __name__ == "__main__":
    main()
