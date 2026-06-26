#!/usr/bin/env python3
"""Ingest EBOM domain via the plm-ebom production connector."""

from __future__ import annotations

from pathlib import Path

from app.federation.graph_store import GraphStore
from app.validation.pipeline_gate import require_l3_conformance
from domains.ebom import pipeline as ebom_pipeline
from pipeline.connectors.cli import configure_connector_from_env
from pipeline.connectors.registry import CONNECTOR_PLM_EBOM
from pipeline.demo.sample_data import COMPONENT_BOM


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = GraphStore()
    try:
        configure_connector_from_env(graph, CONNECTOR_PLM_EBOM)
        product_count = ebom_pipeline.seed_nodes(graph)
        for row in COMPONENT_BOM:
            graph.add_node("Component", row["component"])

        edges = ebom_pipeline.seed_edges(graph, COMPONENT_BOM)
        print(
            f"ebom domain ({CONNECTOR_PLM_EBOM}): {product_count} products, {edges} USED_IN edges"
        )
        require_l3_conformance(graph.driver, quiet=True)
    finally:
        graph.close()


if __name__ == "__main__":
    main()
