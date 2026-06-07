#!/usr/bin/env python3
"""
Seed ontology-validated synthetic BOM data (Neo4j graph + DuckDB component master).

All nodes and edges pass Pydantic validators from ontology/schema.py:
  - add_node() -> validate_node_payload()
  - add_edge() -> RelationEdge (allowed edge pairs)
  - upsert_component() -> ComponentNode

Dataset orchestration: pipeline/demo/seed.py (seed_complex_bom).

Usage:
  uv run python scripts/seed_complex_bom.py --reset
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.component_master_store import ComponentMasterStore
from app.federation.graph_store import GraphStore
from app.storage.neo4j_config import reset_neo4j
from pipeline.demo.seed import seed_complex_bom


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed complex manufacturing BOM demo data")
    parser.add_argument("--duckdb-path", default="data/bom.duckdb")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear Neo4j domain databases and DuckDB file before seeding",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    Path("data").mkdir(parents=True, exist_ok=True)

    graph = GraphStore()
    try:
        if args.reset:
            reset_neo4j(graph.driver)
            duck = Path(args.duckdb_path)
            if duck.exists():
                duck.unlink()

        component_master = ComponentMasterStore(
            graph_store=graph,
            duckdb_path=args.duckdb_path,
        )
        try:
            counts = seed_complex_bom(graph, component_master)
            print("Seeded complex BOM:", counts)
            print("  suppliers: SUP-001..003")
            print("  products:  PROD-900 (Pump), PROD-901 (Motor), PROD-902 (Manifold)")
            print("  components: COMP-100..111 (12 parts)")
        finally:
            component_master.close()
    finally:
        graph.close()


if __name__ == "__main__":
    main()
