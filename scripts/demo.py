from __future__ import annotations

from app.exploration import GraphExplorer
from app.federation.graph_store import LanceGraphStore
from pipeline.demo.seed import seed_complex_bom
from ontology.schema import export_schema_bundle
from app.tools import exploration_tool_definitions, run_exploration_tool

from demo_interactive import explain, prompt, section, show, wait


def main() -> None:
    section(
        "BOM Graph demo (LanceGraph + exploration tools)",
        intro=(
            "Load a multi-product sample BOM on LanceDB, then try agent tool definitions\n"
            "and two graph exploration operations."
        ),
    )
    wait()

    store = LanceGraphStore(lancedb_path="data/lancedb")
    counts = seed_complex_bom(store)
    explorer = GraphExplorer(store)

    explain(
        "Seeded complex BOM:\n"
        f"  {counts['suppliers']} suppliers, {counts['products']} products, "
        f"{counts['components']} components, {counts['processes']} processes\n"
        "  Example chain: SUP-002 -> COMP-106 (Copper Winding) -> PROD-901 (Servo Motor)"
    )
    wait("Press Enter after reviewing seeded data")

    tools = exploration_tool_definitions()
    show(
        "Agent tool definitions",
        tools,
        commentary=(
            "Function names and JSON schemas for an external LLM to call.\n"
            "bom_supplier_impact: downstream impact of a supplier disruption\n"
            "bom_supply_path: shortest allowed path from component to product"
        ),
    )
    wait()

    bundle = export_schema_bundle()
    show(
        "Schema bundle (truncated)",
        str(bundle)[:400] + "\n...",
        commentary=(
            "Pydantic-derived JSON for prompts.\n"
            "Production agents should treat skills/bom-ontology/assets/ontology.json as canonical."
        ),
    )
    wait()

    supplier_id = prompt("supplier_id to analyze", "SUP-002")
    impact = run_exploration_tool(explorer, "bom_supplier_impact", supplier_id=supplier_id)
    show("supplier_impact result", impact, commentary=_explain_supplier_impact(impact))
    wait()

    from_id = prompt("Path start component_id", "COMP-103")
    to_id = prompt("Path end product_id", "PROD-901")
    path = run_exploration_tool(
        explorer,
        "bom_supply_path",
        from_component_id=from_id,
        to_product_id=to_id,
    )
    show("supply_path result", path, commentary=_explain_supply_path(path))

    section(
        "Demo complete",
        intro="Reseed: uv run python scripts/seed_complex_bom.py --reset",
    )


def _explain_supplier_impact(result: dict) -> str:
    rows = result.get("data") or []
    if not rows:
        return (
            "No downstream impact found for this supplier.\n"
            "Check supplier_id and that the graph has SUPPLIED_BY -> USED_IN paths."
        )
    lines = [
        f"Summary: {result.get('summary', '')}",
        f"{len(rows)} component-to-product pairs depend on this supplier.",
    ]
    for row in rows:
        lines.append(
            f"  - {row.get('component_name')} ({row.get('component_id')}) "
            f"-> product {row.get('product_name')} ({row.get('product_id')})"
        )
    lines.append(
        "In manufacturing BOMs, this view shows how procurement risk propagates to finished goods."
    )
    return "\n".join(lines)


def _explain_supply_path(result: dict) -> str:
    data = (result.get("data") or [{}])[0]
    nodes = data.get("nodes") or []
    rels = data.get("relationships") or []
    if not nodes:
        return "No allowed path from the given component to the product."
    path = " -> ".join(f"{n['id']}({','.join(n['labels'])})" for n in nodes)
    return (
        f"Summary: {result.get('summary', '')}\n"
        f"Shortest path: {path}\n"
        f"Relationships: {' -> '.join(rels)}\n"
        "Typical ontology pattern: Component connects to Product via USED_IN."
    )


if __name__ == "__main__":
    main()
