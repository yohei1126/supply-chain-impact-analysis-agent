from __future__ import annotations

from typing import Any

from app.agent.types import ToolCall


def explain_results_heuristic(
    goal: str,
    tool_calls: list[ToolCall],
    results: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Deterministic summary when no LLM gateway is configured."""
    if not results:
        return (
            "No tools were executed. Try a goal that mentions SUP-xxx, COMP-xxx/PROD-xxx, or a supplier/part description.",
            [],
        )

    evidence: list[dict[str, Any]] = []
    lines: list[str] = [f"Goal: {goal}", ""]

    for call, result in zip(tool_calls, results):
        op = result.get("operation", call.name)
        summary = result.get("summary", "")
        data = result.get("data") or []
        lines.append(f"**{call.name}** — {summary}")

        if op == "supplier_impact" and data:
            for row in data[:5]:
                claim = (
                    f"{row.get('component_name')} ({row.get('component_id')}) is used in "
                    f"{row.get('product_name')} ({row.get('product_id')}) via supplier "
                    f"{row.get('supplier_id')}."
                )
                lines.append(f"- {claim}")
                evidence.append(
                    {
                        "claim": claim,
                        "tool": call.name,
                        "pointer": f"results[].data[].component_id={row.get('component_id')}",
                        "value": row.get("component_id"),
                    }
                )
        elif op == "supply_path" and data:
            path = data[0]
            nodes = path.get("nodes") or []
            rels = path.get("relationships") or []
            node_ids = " -> ".join(n["id"] for n in nodes)
            claim = f"Shortest allowed path: {node_ids} ({' / '.join(rels)})."
            lines.append(f"- {claim}")
            evidence.append(
                {
                    "claim": claim,
                    "tool": call.name,
                    "pointer": "results[].data[0].nodes",
                    "value": node_ids,
                }
            )
        lines.append("")

    return "\n".join(lines).strip(), evidence
