#!/usr/bin/env python3
"""Demo ingest for the routing domain graph (manufacturing / MES pipeline)."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.federation.graph_store import LanceGraphStore
from domains.routing import pipeline as routing_pipeline
from pipeline.demo.sample_data import COMPONENT_BOM, PRODUCT_PROCESSES, PRODUCTS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest demo data into the routing domain graph")
    parser.add_argument("--lancedb-path", default="data/lancedb")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = LanceGraphStore(lancedb_path=args.lancedb_path)

    process_count = routing_pipeline.seed_nodes(graph)
    for product in PRODUCTS:
        graph.add_node("Product", product)

    for row in COMPONENT_BOM:
        graph.add_node("Component", row["component"])

    edges = routing_pipeline.seed_edges(graph, COMPONENT_BOM, PRODUCT_PROCESSES)
    print(f"routing domain: {process_count} process nodes, {edges} routing edges")


if __name__ == "__main__":
    main()
