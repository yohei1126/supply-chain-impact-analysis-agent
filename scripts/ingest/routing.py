#!/usr/bin/env python3
"""Demo ingest for the routing domain graph (manufacturing / MES pipeline)."""

from __future__ import annotations

from pathlib import Path

from app.federation.graph_store import GraphStore
from app.validation.pipeline_gate import require_l3_conformance
from domains.routing import pipeline as routing_pipeline
from pipeline.demo.ingest_as_of import configure_demo_domain_ingest
from pipeline.demo.sample_data import COMPONENT_BOM, PRODUCT_PROCESSES, PRODUCTS


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = GraphStore()
    try:
        configure_demo_domain_ingest(graph, "routing")
        process_count = routing_pipeline.seed_nodes(graph)
        for product in PRODUCTS:
            graph.add_node("Product", product)

        for row in COMPONENT_BOM:
            graph.add_node("Component", row["component"])

        edges = routing_pipeline.seed_edges(graph, COMPONENT_BOM, PRODUCT_PROCESSES)
        print(f"routing domain: {process_count} process nodes, {edges} routing edges")
        require_l3_conformance(graph.driver, quiet=True)
    finally:
        graph.close()


if __name__ == "__main__":
    main()
