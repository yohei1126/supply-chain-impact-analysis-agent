from __future__ import annotations

import re
from typing import Any, Literal

from app.agent.context import BomAgentContext
from app.agent.explain import explain_results_heuristic
from app.agent.llm_client import plan_tool_calls_openai_compat, summarize_run_openai_compat
from app.agent.llm_config import OpenAICompatLLMSettings, load_openai_compat_settings
from app.agent.run_report import build_run_report
from app.agent.telemetry import RunTracer, start_run_tracer
from app.agent.types import AgentRunResult, ToolCall
from app.graph_viz import graph_view_for_run

AgentMode = Literal["tools", "auto", "llm"]

_SUPPLIER_ID = re.compile(r"^SUP-\d+$", re.IGNORECASE)
_COMPONENT_ID = re.compile(r"^COMP-\d+$", re.IGNORECASE)
_PRODUCT_ID = re.compile(r"^PROD-\d+$", re.IGNORECASE)


def _valid_tool_call(call: ToolCall) -> bool:
    if call.name == "bom_supplier_impact":
        supplier_id = str(call.arguments.get("supplier_id", "")).strip().upper()
        return bool(_SUPPLIER_ID.fullmatch(supplier_id))
    if call.name == "bom_supply_path":
        component_id = str(call.arguments.get("from_component_id", "")).strip().upper()
        product_id = str(call.arguments.get("to_product_id", "")).strip().upper()
        return bool(_COMPONENT_ID.fullmatch(component_id) and _PRODUCT_ID.fullmatch(product_id))
    return True


def reconcile_planned_tools(goal: str, planned: list[ToolCall]) -> list[ToolCall]:
    """
    Prefer heuristic plans when the LLM invents invalid demo IDs (e.g. SUP-DE-01).

    Keeps valid explicit LLM plans; falls back to plan_tools_from_goal for indirect
    demo questions that the heuristic handles reliably.
    """
    heuristic = plan_tools_from_goal(goal)
    if not planned:
        return heuristic
    if all(_valid_tool_call(call) for call in planned):
        return planned
    return heuristic or planned


def _retry_empty_supplier_impact(
    goal: str,
    planned: list[ToolCall],
    results: list[dict[str, Any]],
    invoke,
) -> tuple[list[ToolCall], list[dict[str, Any]], str | None]:
    if len(planned) != 1 or planned[0].name != "bom_supplier_impact":
        return planned, results, None
    if results and (results[0].get("data") or []):
        return planned, results, None

    alt = plan_tools_from_goal(goal)
    if not alt or alt == planned:
        return planned, results, None

    note = "Heuristic replan after empty supplier impact"
    return alt, [invoke(alt[0].name, **alt[0].arguments)], note


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

    # Indirect demo scenarios (seed: Euro Brass DE→SUP-002, Drive Shaft→COMP-103, Servo→PROD-901)
    if (
        ("german" in goal_lower or "germany" in goal_lower)
        and "brass" in goal_lower
        and any(w in goal_lower for w in ("supplier", "port", "strike", "disruption", "worry"))
    ):
        return [ToolCall("bom_supplier_impact", {"supplier_id": "SUP-002"})]

    if ("drive shaft" in goal_lower or "driveshaft" in goal_lower) and (
        "servo motor" in goal_lower or "motor drive" in goal_lower
    ):
        return [
            ToolCall(
                "bom_supply_path",
                {"from_component_id": "COMP-103", "to_product_id": "PROD-901"},
            )
        ]

    if "brass" in goal_lower and "valve" in goal_lower:
        return [ToolCall("bom_supplier_impact", {"supplier_id": "SUP-002"})]

    if "steel" in goal_lower or "similar" in goal_lower:
        supplier_match = re.search(r"\b(SUP-\d+)\b", goal, re.IGNORECASE)
        if supplier_match:
            return [
                ToolCall("bom_supplier_impact", {"supplier_id": supplier_match.group(1).upper()})
            ]

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
                planned = reconcile_planned_tools(goal, planned)
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

        planned, results, retry_note = _retry_empty_supplier_impact(
            goal,
            planned,
            results,
            registry.invoke,
        )
        if retry_note:
            llm_notes = f"{llm_notes}; {retry_note}" if llm_notes else retry_note

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
        run_report = build_run_report(goal, mode, planned, results, llm_notes, summary_notes)

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
