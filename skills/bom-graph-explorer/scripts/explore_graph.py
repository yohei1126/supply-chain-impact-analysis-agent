from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.exploration import GraphExplorer
from app.federation.graph_store import LanceGraphStore
from app.hybrid_store import UnifiedBomContextStore
from pipeline.demo.seed import seed_complex_bom


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BOM graph exploration (skill script)")
    parser.add_argument("--mode", required=True, choices=["supplier-impact", "shortest-path", "vector-impact"])
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--supplier-id", default="SUP-001")
    parser.add_argument("--from-component-id", default="COMP-100")
    parser.add_argument("--to-product-id", default="PROD-900")
    parser.add_argument("--query", default="steel frame")
    parser.add_argument("--lancedb-path", default="data/lancedb")
    parser.add_argument("--duckdb-path", default="data/bom.duckdb")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    Path("data").mkdir(parents=True, exist_ok=True)

    graph = LanceGraphStore(lancedb_path=args.lancedb_path)
    unified = UnifiedBomContextStore(
        graph_store=graph,
        duckdb_path=args.duckdb_path,
        lancedb_path=args.lancedb_path,
    )
    explorer = GraphExplorer(graph)

    try:
        if args.seed:
            seed_complex_bom(graph, unified)

        if args.mode == "supplier-impact":
            result = explorer.supplier_impact(args.supplier_id)
            print(json.dumps(result.data, indent=2))
        elif args.mode == "shortest-path":
            result = explorer.supply_path(args.from_component_id, args.to_product_id)
            print(json.dumps(result.data, indent=2))
        else:
            rows = unified.find_supplier_impact_for_query(args.query, top_k=3)
            print(json.dumps(rows, indent=2))
    finally:
        unified.close()


if __name__ == "__main__":
    main()
