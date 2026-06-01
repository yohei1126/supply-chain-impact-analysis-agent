from __future__ import annotations

from typing import Any

from bom_graph.exploration import GraphExplorer
from bom_graph.hybrid_store import UnifiedBomContextStore
from bom_graph.tools import exploration_tool_definitions, run_exploration_tool


class ToolRegistry:
    """Maps Agent Skill tool names to deterministic bom_graph executors."""

    def __init__(
        self,
        explorer: GraphExplorer,
        hybrid: UnifiedBomContextStore | None = None,
    ):
        self.explorer = explorer
        self.hybrid = hybrid

    def list_tools(self) -> list[dict[str, Any]]:
        tools = list(exploration_tool_definitions())
        if self.hybrid is not None:
            tools.append(
                {
                    "name": "bom_hybrid_query",
                    "description": (
                        "Vector search over components, enrich with RDB, then graph impact analysis."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "top_k": {"type": "integer", "default": 3},
                        },
                        "required": ["query"],
                    },
                }
            )
        return tools

    def invoke(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        if tool_name in {"bom_supplier_impact", "bom_supply_path"}:
            return run_exploration_tool(self.explorer, tool_name, **kwargs)
        if tool_name == "bom_hybrid_query":
            if self.hybrid is None:
                raise ValueError("Hybrid store is not configured")
            rows = self.hybrid.find_supplier_impact_for_query(
                kwargs["query"],
                top_k=int(kwargs.get("top_k", 3)),
            )
            return {
                "operation": "bom_hybrid_query",
                "summary": f"Hybrid pipeline for query: {kwargs['query']}",
                "data": rows,
            }
        raise ValueError(f"Unknown tool: {tool_name}")
