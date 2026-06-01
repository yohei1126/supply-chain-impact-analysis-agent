from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class AgentRunResult:
    goal: str
    mode: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    llm_notes: str | None = None
    explanation: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    summary_notes: str | None = None
    graph_view: dict[str, Any] = field(default_factory=dict)
    run_report: dict[str, Any] = field(default_factory=dict)
