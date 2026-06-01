from __future__ import annotations

from typing import Any

from bom_graph.agent.types import ToolCall

LOADED_SKILLS: list[dict[str, str]] = [
    {
        "name": "bom-ontology",
        "role": "Schema constraints and published ontology.json (loaded into the agent system prompt).",
    },
    {
        "name": "bom-graph-explorer",
        "role": "Exploration workflows and tool-selection guidance (loaded into the system prompt).",
    },
]


def _describe_query(tool_name: str, arguments: dict[str, Any]) -> str:
    if tool_name == "bom_supplier_impact":
        supplier_id = arguments.get("supplier_id", "?")
        return (
            f"Graph traversal on LanceGraph: find components with SUPPLIED_BY → "
            f"Supplier {supplier_id}, then products with USED_IN from each component."
        )
    if tool_name == "bom_supply_path":
        comp = arguments.get("from_component_id", "?")
        prod = arguments.get("to_product_id", "?")
        return (
            f"Graph BFS on LanceGraph: shortest path Component {comp} → Product {prod} "
            f"using USED_IN, INPUT_OF, and PRODUCED_BY edges only."
        )
    if tool_name == "bom_hybrid_query":
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 3)
        return (
            f"Hybrid pipeline: (1) LanceDB vector search top-{top_k} for text {query!r}, "
            f"(2) DuckDB SELECT on components by id, "
            f"(3) LanceGraph supplier-impact rows filtered by component id."
        )
    return f"Invoke {tool_name} with {arguments}"


def _stores_for_tool(tool_name: str) -> list[str]:
    if tool_name == "bom_supplier_impact":
        return ["LanceGraph (graph_nodes, graph_edges)"]
    if tool_name == "bom_supply_path":
        return ["LanceGraph (graph_nodes, graph_edges)"]
    if tool_name == "bom_hybrid_query":
        return [
            "LanceDB (component_vectors)",
            "DuckDB (components)",
            "LanceGraph (graph_nodes, graph_edges)",
        ]
    return []


def _summarize_result(tool_name: str, result: dict[str, Any]) -> tuple[str, list[str], int | None]:
    op = result.get("operation", tool_name)
    data = result.get("data") or []
    summary = result.get("summary") or ""
    highlights: list[str] = []

    if op in {"supplier_impact", "bom_supplier_impact"} or tool_name == "bom_supplier_impact":
        count = len(data)
        if not data:
            return summary or "No impacted component/product rows.", highlights, 0
        for row in data[:5]:
            highlights.append(
                f"{row.get('component_name')} ({row.get('component_id')}) → "
                f"{row.get('product_name')} ({row.get('product_id')}) "
                f"[cost {row.get('component_cost')}]"
            )
        rest = count - len(highlights)
        headline = f"{count} impacted component→product row(s) for supplier {data[0].get('supplier_id')}."
        if rest > 0:
            headline += f" Showing top {len(highlights)} by cost."
        return headline, highlights, count

    if op in {"supply_path", "bom_supply_path"} or tool_name == "bom_supply_path":
        if not data:
            return summary or "No path found between the given component and product.", highlights, 0
        path = data[0]
        nodes = path.get("nodes") or []
        rels = path.get("relationships") or []
        node_ids = " → ".join(n["id"] for n in nodes)
        highlights.append(f"Path: {node_ids}")
        if rels:
            highlights.append(f"Edges: {' / '.join(rels)}")
        return f"Shortest path found ({len(nodes)} nodes).", highlights, 1

    if op == "bom_hybrid_query" or tool_name == "bom_hybrid_query":
        count = len(data)
        if not data:
            return summary or "No vector hits returned for the query.", highlights, 0
        for row in data[:3]:
            comp = row.get("query_component")
            detail = row.get("rdb_detail") or {}
            impacts = row.get("graph_impacts") or []
            highlights.append(
                f"{comp}: {detail.get('name')} ({detail.get('material')}, "
                f"cost {detail.get('cost')}) — {len(impacts)} graph impact row(s)"
            )
        return f"{count} hybrid pipeline result(s) for query.", highlights, count

    return summary or "Tool completed.", highlights, len(data) if isinstance(data, list) else None


def build_run_report(
    goal: str,
    mode: str,
    tool_calls: list[ToolCall],
    results: list[dict[str, Any]],
    llm_notes: str | None,
    summary_notes: str | None,
) -> dict[str, Any]:
    """Structured run narrative: skills, planner, per-tool query/result."""
    executions: list[dict[str, Any]] = []
    for call, result in zip(tool_calls, results):
        headline, highlights, row_count = _summarize_result(call.name, result)
        executions.append(
            {
                "tool": call.name,
                "arguments": call.arguments,
                "query_description": _describe_query(call.name, call.arguments),
                "stores": _stores_for_tool(call.name),
                "operation": result.get("operation", call.name),
                "result_summary": headline,
                "highlights": highlights,
                "row_count": row_count,
            }
        )

    planner = llm_notes or "No tools planned"
    if not tool_calls:
        planner = llm_notes or "No matching tools for this goal (try example queries or configure LLM)."

    return {
        "skills": list(LOADED_SKILLS),
        "planning": {
            "goal": goal,
            "mode": mode,
            "planner": planner,
            "summary_source": summary_notes,
            "tool_count": len(tool_calls),
        },
        "executions": executions,
    }
