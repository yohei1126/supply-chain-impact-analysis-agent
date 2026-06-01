from __future__ import annotations

import re
from typing import Any

from bom_graph.agent.types import AgentRunResult


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
            "Try one of the examples on the left, such as supplier impact for SUP-002."
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


def build_user_response(result: AgentRunResult) -> dict[str, Any]:
    report = result.run_report or {}
    return {
        "goal": result.goal,
        "explanation": build_user_explanation(result),
        "findings": build_user_findings(report),
        "evidence": build_user_evidence(result),
        "graph_view": result.graph_view,
    }
