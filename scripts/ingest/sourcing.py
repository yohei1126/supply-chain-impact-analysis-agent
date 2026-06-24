#!/usr/bin/env python3
"""Demo ingest for the sourcing domain graph (procurement / SRM pipeline)."""

from __future__ import annotations

from pathlib import Path

from app.federation.graph_store import GraphStore
from app.validation.pipeline_gate import require_l3_conformance
from domains.sourcing import pipeline as sourcing_pipeline
from pipeline.demo.sample_data import COMPONENT_BOM


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = GraphStore()
    try:
        supplier_count = sourcing_pipeline.seed_nodes(graph)
        for row in COMPONENT_BOM:
            graph.add_node("Component", row["component"])

        edges = sourcing_pipeline.seed_edges(graph, COMPONENT_BOM)
        print(f"sourcing domain: {supplier_count} supplier nodes, {edges} SUPPLIED_BY edges")
        require_l3_conformance(graph.driver, quiet=True)
    finally:
        graph.close()


if __name__ == "__main__":
    main()
