from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.component_master_store import ComponentMasterStore
from app.exploration import GraphExplorer
from app.federation.analysis import query_ebom_for_components
from app.federation.graph_store import GraphStore
from app.storage.neo4j_config import reset_neo4j
from pipeline.demo.seed import seed_complex_bom


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BOM graph exploration (skill script)")
    parser.add_argument("--mode", required=True, choices=["supplier-impact", "shortest-path", "vector-impact"])
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--reset", action="store_true", help="Clear Neo4j domain databases before seeding")
    parser.add_argument("--supplier-id", default="SUP-001")
    parser.add_argument("--from-component-id", default="COMP-100")
    parser.add_argument("--to-product-id", default="PROD-900")
    parser.add_argument("--query", default="steel frame")
    parser.add_argument("--duckdb-path", default="data/bom.duckdb")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    Path("data").mkdir(parents=True, exist_ok=True)

    graph = GraphStore()
    component_master = ComponentMasterStore(graph_store=graph, duckdb_path=args.duckdb_path)
    explorer = GraphExplorer(graph)

    try:
        if args.reset:
            reset_neo4j(graph.driver)
            duck = Path(args.duckdb_path)
            if duck.exists():
                duck.unlink()

        if args.seed:
            seed_complex_bom(graph, component_master)

        if args.mode == "supplier-impact":
            result = explorer.supplier_impact(args.supplier_id)
            print(json.dumps(result.data, indent=2))
        elif args.mode == "shortest-path":
            result = explorer.supply_path(args.from_component_id, args.to_product_id)
            print(json.dumps(result.data, indent=2))
        else:
            matches = component_master.search_components(args.query, limit=3)
            rows = []
            for match in matches:
                comp_id = match["id"]
                ebom = query_ebom_for_components(graph, {comp_id})
                rows.append(
                    {
                        "query_component": comp_id,
                        "search_hit": match,
                        "rdb_detail": component_master.get_component_from_rdb(comp_id),
                        "graph_impacts": ebom.rows,
                    }
                )
            print(json.dumps(rows, indent=2))
    finally:
        component_master.close()
        graph.close()


if __name__ == "__main__":
    main()
