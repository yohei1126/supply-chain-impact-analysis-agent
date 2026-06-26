"""Deterministic G* grounding checks: answers must cite tool JSON only."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.agent.types import AgentRunResult, ToolCall
from app.agent.user_response import build_user_response

ENTITY_ID = re.compile(r"\b(SUP|COMP|PROD|PROC)-\d+\b", re.IGNORECASE)


@dataclass
class GroundingViolation:
    check_id: str
    description: str
    sample: dict[str, Any] = field(default_factory=dict)


@dataclass
class GroundingReport:
    passed: bool
    checks_run: list[str] = field(default_factory=list)
    violations: list[GroundingViolation] = field(default_factory=list)


AGENT_GROUNDING_BENCHMARKS: list[dict[str, Any]] = [
    {
        "id": "sup001-explicit",
        "goal": "supplier impact SUP-001",
        "expected_tool": "bom_supplier_impact",
        "expected_args": {"supplier_id": "SUP-001"},
        "min_rows": 1,
    },
    {
        "id": "sup002-explicit",
        "goal": "Analyze supplier impact for SUP-002",
        "expected_tool": "bom_supplier_impact",
        "expected_args": {"supplier_id": "SUP-002"},
        "min_rows": 1,
    },
    {
        "id": "sup002-indirect-german-brass",
        "goal": (
            "Our German brass supplier might face a port strike next month. "
            "Which finished products and component parts should we worry about?"
        ),
        "expected_tool": "bom_supplier_impact",
        "expected_args": {"supplier_id": "SUP-002"},
        "min_rows": 1,
    },
    {
        "id": "supply-path-drive-shaft",
        "goal": (
            "Trace how the drive shaft part connects to the servo motor finished good "
            "through our BOM."
        ),
        "expected_tool": "bom_supply_path",
        "expected_args": {"from_component_id": "COMP-103", "to_product_id": "PROD-901"},
        "min_rows": 1,
    },
]


def _normalize_token(value: Any) -> str:
    text = str(value).strip()
    if ENTITY_ID.fullmatch(text):
        return text.upper()
    return text


def _iter_scalars(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_scalars(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_scalars(item)
    elif value is not None:
        yield value


def collect_ground_tokens(
    tool_calls: list[ToolCall],
    results: list[dict[str, Any]],
) -> set[str]:
    """Flatten tool arguments and result payloads into a grounding vocabulary."""
    tokens: set[str] = set()
    for call in tool_calls:
        for value in call.arguments.values():
            token = _normalize_token(value)
            if token:
                tokens.add(token)
    for result in results:
        for scalar in _iter_scalars(result):
            token = _normalize_token(scalar)
            if token:
                tokens.add(token)
            for entity_id in ENTITY_ID.findall(str(scalar)):
                tokens.add(entity_id.upper())
    return tokens


def extract_entity_ids(text: str) -> set[str]:
    return {match.group(0).upper() for match in ENTITY_ID.finditer(text)}


def _value_is_grounded(value: str, tokens: set[str]) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    upper = candidate.upper()
    if upper in tokens or candidate in tokens:
        return True
    return any(
        upper in token.upper() or token.upper() in upper for token in tokens if len(token) >= 3
    )


def _check_entity_ids_in_text(
    text: str,
    tokens: set[str],
    *,
    check_id: str,
    label: str,
) -> GroundingViolation | None:
    mentioned = extract_entity_ids(text)
    if not mentioned:
        return None
    hallucinated = sorted(entity for entity in mentioned if entity not in tokens)
    if not hallucinated:
        return None
    return GroundingViolation(
        check_id=check_id,
        description=f"{label} mentions entity IDs not present in tool output",
        sample={"text": text[:240], "hallucinated_ids": hallucinated},
    )


def evaluate_grounding(
    *,
    tool_calls: list[ToolCall],
    results: list[dict[str, Any]],
    explanation: str | None = None,
    findings: list[str] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> GroundingReport:
    """Verify narrative and evidence are supported by executed tool JSON."""
    checks_run = [
        "tool_results_present",
        "evidence_when_data_present",
        "evidence_values_grounded",
        "narrative_entity_ids_grounded",
    ]
    violations: list[GroundingViolation] = []
    tokens = collect_ground_tokens(tool_calls, results)
    data_rows = sum(len(result.get("data") or []) for result in results)

    if tool_calls and data_rows == 0:
        violations.append(
            GroundingViolation(
                check_id="tool_results_present",
                description="Tools ran but returned no data rows to ground claims",
                sample={"tool_count": len(tool_calls)},
            )
        )

    evidence = evidence or []
    if data_rows > 0 and not evidence:
        violations.append(
            GroundingViolation(
                check_id="evidence_when_data_present",
                description="Tool data exists but evidence[] is empty",
                sample={"data_rows": data_rows},
            )
        )

    tool_names = {call.name for call in tool_calls}
    for index, row in enumerate(evidence):
        tool = str(row.get("tool", "")).strip()
        if tool and tool not in tool_names:
            violations.append(
                GroundingViolation(
                    check_id="evidence_values_grounded",
                    description=f"evidence[{index}] references unknown tool {tool}",
                    sample={"row": row},
                )
            )
        value = str(row.get("value", "")).strip()
        if value and not _value_is_grounded(value, tokens):
            violations.append(
                GroundingViolation(
                    check_id="evidence_values_grounded",
                    description=f"evidence[{index}] value is not present in tool output",
                    sample={"row": row},
                )
            )
        claim = str(row.get("claim", "")).strip()
        claim_check = _check_entity_ids_in_text(
            claim,
            tokens,
            check_id="evidence_values_grounded",
            label=f"evidence[{index}] claim",
        )
        if claim_check is not None:
            violations.append(claim_check)

    for label, text in (
        ("explanation", explanation or ""),
        *[(f"findings[{index}]", item) for index, item in enumerate(findings or [])],
    ):
        narrative_check = _check_entity_ids_in_text(
            text,
            tokens,
            check_id="narrative_entity_ids_grounded",
            label=label,
        )
        if narrative_check is not None:
            violations.append(narrative_check)

    return GroundingReport(
        passed=not violations,
        checks_run=checks_run,
        violations=violations,
    )


def evaluate_agent_run(result: AgentRunResult) -> GroundingReport:
    """Evaluate internal + user-facing fields for G* grounding."""
    user = build_user_response(result)
    return evaluate_grounding(
        tool_calls=result.tool_calls,
        results=result.results,
        explanation=user["explanation"],
        findings=user["findings"],
        evidence=result.evidence,
    )


def export_grounding_report(report: GroundingReport) -> dict[str, Any]:
    return {
        "format": "bom-grounding-report",
        "version": 1,
        "passed": report.passed,
        "checks_run": list(report.checks_run),
        "violations": [
            {
                "check_id": item.check_id,
                "description": item.description,
                "sample": item.sample,
            }
            for item in report.violations
        ],
    }


__all__ = [
    "AGENT_GROUNDING_BENCHMARKS",
    "GroundingReport",
    "GroundingViolation",
    "collect_ground_tokens",
    "evaluate_agent_run",
    "evaluate_grounding",
    "export_grounding_report",
    "extract_entity_ids",
]
