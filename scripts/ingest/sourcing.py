#!/usr/bin/env python3
"""Ingest sourcing domain via the srm-sourcing production connector."""

from __future__ import annotations

from pathlib import Path

from app.federation.graph_store import GraphStore
from app.validation.pipeline_gate import require_l3_conformance
from domains.sourcing import pipeline as sourcing_pipeline
from pipeline.connectors.cli import configure_connector_from_env
from pipeline.connectors.registry import CONNECTOR_SRM_SOURCING
from pipeline.demo.sample_data import COMPONENT_BOM


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = GraphStore()
    try:
        configure_connector_from_env(graph, CONNECTOR_SRM_SOURCING)
        supplier_count = sourcing_pipeline.seed_nodes(graph)
        for row in COMPONENT_BOM:
            graph.add_node("Component", row["component"])

        edges = sourcing_pipeline.seed_edges(graph, COMPONENT_BOM)
        print(
            f"sourcing domain ({CONNECTOR_SRM_SOURCING}): "
            f"{supplier_count} suppliers, {edges} SUPPLIED_BY edges"
        )
        require_l3_conformance(graph.driver, quiet=True)
    finally:
        graph.close()


if __name__ == "__main__":
    main()
