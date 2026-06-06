from __future__ import annotations

from typing import Any

from app.exploration import GraphExplorer


def exploration_tool_definitions() -> list[dict[str, Any]]:
    """
    OpenAPI-style tool metadata for agent frameworks (LangGraph, MCP adapters, etc.).
    Behavioral guidance belongs in the Agent Skill package, not here.
    """
    return [
        {
            "name": "bom_supplier_impact",
            "description": "List components and products impacted by a supplier disruption.",
            "parameters": {
                "type": "object",
                "properties": {"supplier_id": {"type": "string"}},
                "required": ["supplier_id"],
            },
        },
        {
            "name": "bom_supply_path",
            "description": "Find the shortest allowed path from a component to a product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_component_id": {"type": "string"},
                    "to_product_id": {"type": "string"},
                },
                "required": ["from_component_id", "to_product_id"],
            },
        },
    ]


def run_exploration_tool(explorer: GraphExplorer, tool_name: str, **kwargs: Any) -> dict[str, Any]:
    if tool_name == "bom_supplier_impact":
        result = explorer.supplier_impact(kwargs["supplier_id"])
    elif tool_name == "bom_supply_path":
        result = explorer.supply_path(kwargs["from_component_id"], kwargs["to_product_id"])
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

    return {
        "operation": result.operation,
        "summary": result.summary,
        "data": result.data,
    }
