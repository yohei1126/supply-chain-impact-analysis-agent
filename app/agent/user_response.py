from __future__ import annotations

import re
from typing import Any

from app.agent.types import AgentRunResult


def _strip_markdown_bold(text: str) -> str:
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", text)


def build_user_findings(run_report: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for execution in run_report.get("executions", []):
        headline = execution.get("result_summary")
        if headline:
            findings.append(str(headline))
        for line in execution.get("highlights") or []:
            item = str(line)
            if item not in findings:
                findings.append(item)
    return findings


def build_user_explanation(result: AgentRunResult) -> str:
    report = result.run_report or {}
    if not report.get("executions"):
        return (
            "We could not analyze that question. "
            "Try one of the indirect examples on the left, such as a supplier disruption described by country and material."
        )

    explanation = (result.explanation or "").strip()
    if explanation and not explanation.startswith("Goal:"):
        return _strip_markdown_bold(explanation)

    parts: list[str] = []
    for execution in report.get("executions", []):
        summary = execution.get("result_summary")
        if summary:
            parts.append(str(summary))
        for line in execution.get("highlights") or []:
            parts.append(f"• {line}")
    return "\n\n".join(parts)


def build_user_evidence(result: AgentRunResult) -> list[dict[str, str]]:
    """User-facing evidence: grounded claims only (no tool names or JSON paths)."""
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in result.evidence or []:
        claim = str(row.get("claim", "")).strip()
        if not claim or claim in seen:
            continue
        seen.add(claim)
        items.append({"claim": claim})
    return items


def build_user_cypher_executions(result: AgentRunResult) -> list[dict[str, Any]]:
    """Cypher steps run by agent tools (user-visible; mirrors federation domain steps)."""
    executions: list[dict[str, Any]] = []
    for call, payload in zip(result.tool_calls, result.results):
        steps = list(payload.get("cypher_queries") or [])
        if not steps:
            primary = (payload.get("cypher") or "").strip()
            if primary:
                steps = [
                    {
                        "graph_id": "",
                        "query_name": payload.get("operation", call.name),
                        "cypher": primary,
                    }
                ]
        if not steps:
            continue
        executions.append(
            {
                "tool": call.name,
                "operation": payload.get("operation", call.name),
                "summary": payload.get("summary", ""),
                "ontology_source": payload.get("ontology_source", ""),
                "steps": steps,
            }
        )
    return executions


def build_user_run_summary(result: AgentRunResult) -> dict[str, Any]:
    report = result.run_report or {}
    planning = report.get("planning", {})
    return {
        "planner": planning.get("planner") or result.llm_notes or "unknown",
        "tools": [call.name for call in result.tool_calls],
        "tool_count": len(result.tool_calls),
    }


def build_user_response(result: AgentRunResult) -> dict[str, Any]:
    report = result.run_report or {}
    return {
        "goal": result.goal,
        "explanation": build_user_explanation(result),
        "findings": build_user_findings(report),
        "evidence": build_user_evidence(result),
        "graph_view": result.graph_view,
        "cypher_executions": build_user_cypher_executions(result),
        "run_summary": build_user_run_summary(result),
    }
