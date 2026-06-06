from __future__ import annotations

import re
from typing import Any, Literal

from app.agent.context import BomAgentContext
from app.graph_viz import graph_view_for_run

from app.agent.explain import explain_results_heuristic
from app.agent.llm_client import plan_tool_calls_openai_compat, summarize_run_openai_compat
from app.agent.llm_config import OpenAICompatLLMSettings, load_openai_compat_settings
from app.agent.registry import ToolRegistry
from app.agent.run_report import build_run_report
from app.agent.telemetry import RunTracer, start_run_tracer
from app.agent.types import AgentRunResult, ToolCall

AgentMode = Literal["tools", "auto", "llm"]


def plan_tools_from_goal(goal: str) -> list[ToolCall]:
    """Lightweight planner without LLM (suitable for tests and offline agents)."""
    goal_lower = goal.lower()

    supplier_match = re.search(r"\b(SUP-\d+)\b", goal, re.IGNORECASE)
    if supplier_match and ("impact" in goal_lower or "supplier" in goal_lower):
        return [ToolCall("bom_supplier_impact", {"supplier_id": supplier_match.group(1).upper()})]

    comp_match = re.search(r"\b(COMP-\d+)\b", goal, re.IGNORECASE)
    prod_match = re.search(r"\b(PROD-\d+)\b", goal, re.IGNORECASE)
    if comp_match and prod_match and ("path" in goal_lower or "route" in goal_lower):
        return [
            ToolCall(
                "bom_supply_path",
                {
                    "from_component_id": comp_match.group(1).upper(),
                    "to_product_id": prod_match.group(1).upper(),
                },
            )
        ]

    if "steel" in goal_lower or "vector" in goal_lower or "similar" in goal_lower:
        query = goal.strip()
        return [ToolCall("bom_hybrid_query", {"query": query, "top_k": 3})]

    return []


def _planner_note(settings: OpenAICompatLLMSettings) -> str:
    if settings.gateway:
        return f"Planned by LLM ({settings.gateway})"
    return "Planned by LLM"


class BomAutonomousAgent:
    """
    Autonomous agent runtime wired to Agent Skills (prompt) and app tools.
    """

    def __init__(self, context: BomAgentContext):
        self.context = context

    def run(
        self,
        goal: str,
        *,
        mode: AgentMode = "auto",
        tool_calls: list[ToolCall] | None = None,
        llm_settings: OpenAICompatLLMSettings | None = None,
        summarize: bool = True,
        tracer: RunTracer | None = None,
    ) -> AgentRunResult:
        registry = self.context.tools
        system_prompt = self.context.system_prompt()
        planned = tool_calls or []
        llm_notes: str | None = None
        run_tracer = tracer or start_run_tracer(goal, mode)

        settings = llm_settings or load_openai_compat_settings()

        if not planned:
            if mode == "llm" or (mode == "auto" and settings.configured):
                if not settings.configured:
                    raise ValueError(
                        "LLM mode requires OPENAI_API_BASE and OPENAI_API_KEY "
                        "(or LLM_GATEWAY_BASE / LLM_GATEWAY_API_KEY)"
                    )
                planned = plan_tool_calls_openai_compat(
                    goal,
                    system_prompt,
                    registry.list_tools(),
                    settings=settings,
                    tracer=run_tracer,
                )
                llm_notes = _planner_note(settings)
            else:
                planned = plan_tools_from_goal(goal)
                llm_notes = "Planned by heuristic"

        run_tracer.record_planning(
            llm_notes,
            planned,
            system_prompt_chars=len(system_prompt),
        )

        results: list[dict[str, Any]] = []
        for call in planned:
            results.append(registry.invoke(call.name, **call.arguments))

        explanation: str | None = None
        evidence: list[dict[str, Any]] = []
        summary_notes: str | None = None

        if summarize and planned:
            try:
                if settings.configured:
                    explanation, evidence = summarize_run_openai_compat(
                        goal,
                        planned,
                        results,
                        settings=settings,
                        tracer=run_tracer,
                    )
                    summary_notes = (
                        f"Summary by LLM ({settings.gateway})"
                        if settings.gateway
                        else "Summary by LLM"
                    )
                else:
                    explanation, evidence = explain_results_heuristic(goal, planned, results)
                    summary_notes = "Summary by heuristic (set OPENAI_* for LLM narrative)"
            except RuntimeError as exc:
                explanation, evidence = explain_results_heuristic(goal, planned, results)
                summary_notes = f"LLM summary failed, heuristic fallback: {exc}"

        graph_view = graph_view_for_run(registry.explorer.store, planned, results)
        run_report = build_run_report(
            goal, mode, planned, results, llm_notes, summary_notes
        )

        result = AgentRunResult(
            goal=goal,
            mode=mode,
            tool_calls=planned,
            results=results,
            llm_notes=llm_notes,
            explanation=explanation,
            evidence=evidence,
            summary_notes=summary_notes,
            graph_view=graph_view,
            run_report=run_report,
        )
        run_tracer.emit_run(result)
        return result
