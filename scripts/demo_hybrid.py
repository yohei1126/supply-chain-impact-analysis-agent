from __future__ import annotations

import os

from app.hybrid_store import UnifiedBomContextStore
from app.federation.graph_store import LanceGraphStore
from pipeline.demo.seed import seed_complex_bom

from demo_interactive import explain, prompt, section, show, wait


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def main() -> None:
    section(
        "Hybrid BOM demo (Vector + RDB + Graph)",
        intro=(
            "Walk through LanceDB (vectors) + DuckDB (attributes) + LanceGraph (relationships)\n"
            "via UnifiedBomContextStore on a 12-component, 3-product BOM."
        ),
    )
    wait()

    graph = LanceGraphStore(lancedb_path=env("LANCEDB_PATH", "data/lancedb"))
    unified = UnifiedBomContextStore(graph_store=graph)

    try:
        counts = seed_complex_bom(graph, unified)
        explain(
            f"Seeded {counts['components']} components across {counts['products']} products "
            f"and {counts['suppliers']} suppliers."
        )
        wait("Press Enter after seeding")

        query = prompt("Vector search query (natural language)", "motor shaft steel")
        vector_hits = unified.vector_search_components(query, top_k=3)
        show("1) Vector search (LanceDB)", vector_hits, commentary=_explain_vector_hits(vector_hits, query))
        wait()

        detail = unified.get_component_from_rdb(vector_hits[0]["id"]) if vector_hits else None
        show("2) RDB enrichment (DuckDB)", detail, commentary=_explain_rdb(detail))
        wait()

        supplier_id = prompt("supplier_id for graph traversal", "SUP-001")
        graph_rows = graph.impacted_products_by_supplier(supplier_id)
        show(
            "3) Graph traversal (LanceGraph)",
            graph_rows[:8],
            commentary=_explain_graph_rows(graph_rows, supplier_id),
        )
        wait()

        pipeline_query = prompt("Unified pipeline query", "brass valve seal")
        top_k = int(prompt("Unified pipeline top_k", "4") or "4")
        all_rows = unified.find_supplier_impact_for_query(pipeline_query, top_k=top_k)
        show(
            "Unified: vector -> rdb -> graph",
            all_rows,
            commentary=_explain_pipeline(all_rows, pipeline_query),
        )

        section(
            "Demo complete",
            intro="Reseed fresh data: uv run python scripts/seed_complex_bom.py --reset",
        )
    finally:
        unified.close()


def _explain_vector_hits(hits: list[dict], query: str) -> str:
    if not hits:
        return f"No components in the vector index are close to query '{query}'."
    lines = [
        f"Mapped natural-language query '{query}' to a fixed-size SHA256-based vector and searched LanceDB.",
        f"Top {len(hits)} hits (lower _distance is closer):",
    ]
    for i, h in enumerate(hits, 1):
        lines.append(
            f"  {i}. {h.get('name')} ({h.get('id')}) material={h.get('material')} distance={h.get('_distance', 0):.3f}"
        )
    lines.append(
        "Embeddings are built from component name/material text as a stand-in for semantic search."
    )
    return "\n".join(lines)


def _explain_rdb(detail: dict | None) -> str:
    if not detail:
        return "Could not load the top vector hit from DuckDB."
    return (
        f"Loaded normalized attributes for component {detail.get('id')} from the RDB.\n"
        f"  name={detail.get('name')} material={detail.get('material')} cost={detail.get('cost')}\n"
        "Graph stores relationships; RDB is suited for attributes and aggregations."
    )


def _explain_graph_rows(rows: list[dict], supplier_id: str) -> str:
    if not rows:
        return f"No impact paths from supplier {supplier_id} to products."
    lines = [
        f"Graph walk: components SUPPLIED_BY {supplier_id} -> products via USED_IN",
        f"Impact rows: {len(rows)}",
    ]
    for row in rows[:8]:
        lines.append(
            f"  - {row.get('component_name')} -> {row.get('product_name')} (cost={row.get('component_cost')})"
        )
    if len(rows) > 8:
        lines.append(f"  ...and {len(rows) - 8} more")
    return "\n".join(lines)


def _explain_pipeline(rows: list[dict], query: str) -> str:
    if not rows:
        return f"Unified pipeline returned no rows for query '{query}'."
    lines = [
        "Each record bundles vector_hit -> rdb_detail -> graph_impacts for one query.",
        f"Processed {len(rows)} component candidates for '{query}'.",
    ]
    for row in rows:
        hit = row.get("vector_hit") or {}
        impacts = row.get("graph_impacts") or []
        lines.append(
            f"  - {hit.get('name')} ({row.get('query_component')}): "
            f"RDB cost={(row.get('rdb_detail') or {}).get('cost')}, "
            f"graph impacts={len(impacts)}"
        )
    lines.append(
        "Flow: narrow candidates with vectors, enrich attributes in RDB, assess procurement risk on the graph."
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
