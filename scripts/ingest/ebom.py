#!/usr/bin/env python3
"""Demo ingest for the EBOM domain graph (engineering / PLM pipeline)."""

from __future__ import annotations

from pathlib import Path

from app.federation.graph_store import GraphStore
from domains.ebom import pipeline as ebom_pipeline
from pipeline.demo.sample_data import COMPONENT_BOM


def main() -> None:
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = GraphStore()
    try:
        product_count = ebom_pipeline.seed_nodes(graph)
        for row in COMPONENT_BOM:
            graph.add_node("Component", row["component"])

        edges = ebom_pipeline.seed_edges(graph, COMPONENT_BOM)
        print(f"ebom domain: {product_count} product nodes, {edges} USED_IN edges")
    finally:
        graph.close()


if __name__ == "__main__":
    main()
