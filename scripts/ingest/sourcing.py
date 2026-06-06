#!/usr/bin/env python3
"""Demo ingest for the sourcing domain graph (procurement / SRM pipeline)."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.federation.graph_store import LanceGraphStore
from domains.sourcing import pipeline as sourcing_pipeline
from pipeline.demo.sample_data import COMPONENT_BOM


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest demo data into the sourcing domain graph")
    parser.add_argument("--lancedb-path", default="data/lancedb")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    Path("data").mkdir(parents=True, exist_ok=True)
    graph = LanceGraphStore(lancedb_path=args.lancedb_path)

    supplier_count = sourcing_pipeline.seed_nodes(graph)
    for row in COMPONENT_BOM:
        graph.add_node("Component", row["component"])

    edges = sourcing_pipeline.seed_edges(graph, COMPONENT_BOM)
    print(f"sourcing domain: {supplier_count} supplier nodes, {edges} SUPPLIED_BY edges")


if __name__ == "__main__":
    main()
