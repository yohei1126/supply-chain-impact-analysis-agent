#!/usr/bin/env python3
"""
Seed ontology-validated synthetic BOM data (graph + vector + RDB).

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
import shutil
from pathlib import Path

from app.federation.graph_store import LanceGraphStore
from app.hybrid_store import UnifiedBomContextStore
from pipeline.demo.seed import seed_complex_bom

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed complex manufacturing BOM demo data")
    parser.add_argument("--lancedb-path", default="data/lancedb")
    parser.add_argument("--duckdb-path", default="data/bom.duckdb")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete LanceDB directory and DuckDB file before seeding",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    Path("data").mkdir(parents=True, exist_ok=True)

    if args.reset:
        lance_dir = Path(args.lancedb_path)
        if lance_dir.exists():
            shutil.rmtree(lance_dir)
        duck = Path(args.duckdb_path)
        if duck.exists():
            duck.unlink()

    graph = LanceGraphStore(lancedb_path=args.lancedb_path)
    unified = UnifiedBomContextStore(
        graph_store=graph,
        duckdb_path=args.duckdb_path,
        lancedb_path=args.lancedb_path,
    )
    try:
        counts = seed_complex_bom(graph, unified)
        print("Seeded complex BOM:", counts)
        print("  suppliers: SUP-001..003")
        print("  products:  PROD-900 (Pump), PROD-901 (Motor), PROD-902 (Manifold)")
        print("  components: COMP-100..111 (12 parts)")
    finally:
        unified.close()


if __name__ == "__main__":
    main()
