from __future__ import annotations

from typing import Any

from app.exploration import GraphExplorer
from app.tools import exploration_tool_definitions, run_exploration_tool


class ToolRegistry:
    """Maps Agent Skill tool names to deterministic app-layer executors."""

    def __init__(self, explorer: GraphExplorer):
        self.explorer = explorer

    def list_tools(self) -> list[dict[str, Any]]:
        return list(exploration_tool_definitions())

    def invoke(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        if tool_name in {"bom_supplier_impact", "bom_supply_path"}:
            return run_exploration_tool(self.explorer, tool_name, **kwargs)
        raise ValueError(f"Unknown tool: {tool_name}")
