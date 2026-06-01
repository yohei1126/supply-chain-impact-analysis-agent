from __future__ import annotations

import os
from typing import Any, Protocol

from bom_graph.agent.types import AgentRunResult, ToolCall


class RunTracer(Protocol):
    def record_generation(
        self,
        name: str,
        model: str,
        input_messages: list[dict[str, str]],
        output_text: str,
    ) -> None: ...

    def record_planning(
        self,
        planner: str | None,
        tool_calls: list[ToolCall],
        *,
        system_prompt_chars: int,
    ) -> None: ...

    def emit_run(self, result: AgentRunResult) -> None: ...

    def flush(self) -> None: ...


class NullRunTracer:
    def record_generation(
        self,
        name: str,
        model: str,
        input_messages: list[dict[str, str]],
        output_text: str,
    ) -> None:
        return None

    def record_planning(
        self,
        planner: str | None,
        tool_calls: list[ToolCall],
        *,
        system_prompt_chars: int,
    ) -> None:
        return None

    def emit_run(self, result: AgentRunResult) -> None:
        return None

    def flush(self) -> None:
        return None


def langfuse_configured() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def _langfuse_client() -> Any | None:
    if not langfuse_configured():
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        return None

    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")
    kwargs: dict[str, Any] = {
        "public_key": os.getenv("LANGFUSE_PUBLIC_KEY"),
        "secret_key": os.getenv("LANGFUSE_SECRET_KEY"),
    }
    if host:
        kwargs["host"] = host
    return Langfuse(**kwargs)


class LangfuseRunTracer:
    """Send planner, tool, and LLM details to Langfuse (not shown in the user UI)."""

    def __init__(self, goal: str, mode: str) -> None:
        self._client = _langfuse_client()
        self._root: Any | None = None
        if self._client is not None:
            self._root = self._client.start_observation(
                name="bom-agent-run",
                as_type="agent",
                input={"goal": goal, "mode": mode},
                metadata={"tags": ["bom-graph-agent"]},
            )

    def record_generation(
        self,
        name: str,
        model: str,
        input_messages: list[dict[str, str]],
        output_text: str,
    ) -> None:
        if self._root is None:
            return
        generation = self._root.start_observation(
            name=name,
            as_type="generation",
            model=model,
            input=input_messages,
        )
        generation.update(output=output_text)
        generation.end()

    def record_planning(
        self,
        planner: str | None,
        tool_calls: list[ToolCall],
        *,
        system_prompt_chars: int,
    ) -> None:
        if self._root is None:
            return
        span = self._root.start_observation(
            name="planning",
            as_type="span",
            input={"planner": planner, "system_prompt_chars": system_prompt_chars},
        )
        span.update(
            output={
                "tool_calls": [
                    {"name": call.name, "arguments": call.arguments} for call in tool_calls
                ]
            }
        )
        span.end()

    def emit_run(self, result: AgentRunResult) -> None:
        if self._root is None:
            return

        report = result.run_report or {}
        for index, (call, tool_result, execution) in enumerate(
            zip(result.tool_calls, result.results, report.get("executions", []))
        ):
            tool_span = self._root.start_observation(
                name=f"tool:{call.name}",
                as_type="tool",
                input={
                    "arguments": call.arguments,
                    "query_description": execution.get("query_description"),
                    "stores": execution.get("stores"),
                },
                metadata={"index": index},
            )
            tool_span.update(
                output={
                    "operation": tool_result.get("operation"),
                    "summary": tool_result.get("summary"),
                    "result_summary": execution.get("result_summary"),
                    "highlights": execution.get("highlights"),
                    "row_count": execution.get("row_count"),
                    "data": tool_result.get("data"),
                }
            )
            tool_span.end()

        self._root.update(
            output={
                "explanation": result.explanation,
                "evidence": result.evidence,
                "graph_view": {
                    "node_count": (result.graph_view or {}).get("node_count"),
                    "edge_count": (result.graph_view or {}).get("edge_count"),
                },
            },
            metadata={
                "run_report": report,
                "llm_notes": result.llm_notes,
                "summary_notes": result.summary_notes,
                "tool_results": result.results,
            },
        )
        self._root.end()

    def flush(self) -> None:
        if self._client is not None:
            self._client.flush()


def start_run_tracer(goal: str, mode: str) -> RunTracer:
    if not langfuse_configured():
        return NullRunTracer()
    client = _langfuse_client()
    if client is None:
        return NullRunTracer()
    return LangfuseRunTracer(goal=goal, mode=mode)
