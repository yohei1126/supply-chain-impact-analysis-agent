#!/usr/bin/env python3
"""Ingest routing domain via the mes-routing production connector."""

from __future__ import annotations

from pathlib import Path

from app.federation.graph_store import GraphStore
from app.validation.pipeline_gate import require_l3_conformance
from domains.routing import pipeline as routing_pipeline
from pipeline.connectors.cli import configure_connector_from_env
from pipeline.connectors.registry import CONNECTOR_MES_ROUTING
from pipeline.demo.sample_data import COMPONENT_BOM, PRODUCT_PROCESSES, PRODUCTS


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = GraphStore()
    try:
        configure_connector_from_env(graph, CONNECTOR_MES_ROUTING)
        process_count = routing_pipeline.seed_nodes(graph)
        for product in PRODUCTS:
            graph.add_node("Product", product)

        for row in COMPONENT_BOM:
            graph.add_node("Component", row["component"])

        edges = routing_pipeline.seed_edges(graph, COMPONENT_BOM, PRODUCT_PROCESSES)
        print(
            f"routing domain ({CONNECTOR_MES_ROUTING}): "
            f"{process_count} processes, {edges} routing edges"
        )
        require_l3_conformance(graph.driver, quiet=True)
    finally:
        graph.close()


if __name__ == "__main__":
    main()
