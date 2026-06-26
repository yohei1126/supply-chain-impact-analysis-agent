"""G* agent/tool grounding evaluation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.context import BomAgentContext
from app.agent.grounding import (
    AGENT_GROUNDING_BENCHMARKS,
    collect_ground_tokens,
    evaluate_agent_run,
    evaluate_grounding,
    export_grounding_report,
)
from app.agent.runner import BomAutonomousAgent, ToolCall
from app.federation.graph_store import GraphStore
from pipeline.demo.load_domains import load_all_domains_separately
from tests.conftest import populate_duckdb_master

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def agent_context(graph_store: GraphStore, tmp_path):
    load_all_domains_separately(graph_store)
    duckdb_path = tmp_path / "bom.duckdb"
    populate_duckdb_master(graph_store, duckdb_path)
    ctx = BomAgentContext.create(
        repo_root=REPO_ROOT,
        duckdb_path=str(duckdb_path),
        graph=graph_store,
    )
    yield ctx
    ctx.close()


def test_collect_ground_tokens_from_tool_results() -> None:
    calls = [ToolCall("bom_supplier_impact", {"supplier_id": "SUP-002"})]
    results = [
        {
            "operation": "supplier_impact",
            "data": [
                {
                    "supplier_id": "SUP-002",
                    "component_id": "COMP-101",
                    "product_id": "PROD-900",
                }
            ],
        }
    ]
    tokens = collect_ground_tokens(calls, results)
    assert "SUP-002" in tokens
    assert "COMP-101" in tokens
    assert "PROD-900" in tokens


def test_evaluate_grounding_rejects_hallucinated_entity_ids() -> None:
    calls = [ToolCall("bom_supplier_impact", {"supplier_id": "SUP-001"})]
    results = [
        {
            "operation": "supplier_impact",
            "data": [{"supplier_id": "SUP-001", "component_id": "COMP-100"}],
        }
    ]
    report = evaluate_grounding(
        tool_calls=calls,
        results=results,
        explanation="Supplier SUP-999 affects pump production.",
        evidence=[
            {
                "claim": "SUP-999 supplies COMP-100.",
                "tool": "bom_supplier_impact",
                "pointer": "results[].data[0]",
                "value": "SUP-999",
            }
        ],
    )
    assert not report.passed
    assert any(v.check_id == "narrative_entity_ids_grounded" for v in report.violations)
    assert any(v.check_id == "evidence_values_grounded" for v in report.violations)


def test_evaluate_grounding_accepts_heuristic_evidence() -> None:
    calls = [ToolCall("bom_supplier_impact", {"supplier_id": "SUP-001"})]
    results = [
        {
            "operation": "supplier_impact",
            "data": [
                {
                    "supplier_id": "SUP-001",
                    "component_id": "COMP-100",
                    "component_name": "Frame",
                    "product_id": "PROD-900",
                    "product_name": "Pump",
                }
            ],
        }
    ]
    report = evaluate_grounding(
        tool_calls=calls,
        results=results,
        explanation="Frame (COMP-100) is used in Pump (PROD-900) via SUP-001.",
        findings=["Frame (COMP-100) → Pump (PROD-900)"],
        evidence=[
            {
                "claim": "Frame (COMP-100) is used in Pump (PROD-900) via supplier SUP-001.",
                "tool": "bom_supplier_impact",
                "pointer": "results[].data[].component_id=COMP-100",
                "value": "COMP-100",
            }
        ],
    )
    assert report.passed, report.violations


@pytest.mark.parametrize("case", AGENT_GROUNDING_BENCHMARKS, ids=lambda c: c["id"])
def test_agent_benchmarks_are_grounded(agent_context: BomAgentContext, case: dict) -> None:
    agent = BomAutonomousAgent(agent_context)
    result = agent.run(case["goal"], mode="tools")
    assert result.tool_calls
    assert result.tool_calls[0].name == case["expected_tool"]
    assert result.tool_calls[0].arguments == case["expected_args"]
    assert len(result.results[0].get("data") or []) >= case["min_rows"]

    report = evaluate_agent_run(result)
    assert report.passed, report.violations
    payload = export_grounding_report(report)
    assert payload["passed"] is True


def test_supplier_impact_reuses_open_duckdb_connection(agent_context: BomAgentContext) -> None:
    """Regression: federate quality gates must not open a second DuckDB handle."""
    result = agent_context.tools.invoke("bom_supplier_impact", supplier_id="SUP-002")
    assert result.get("data")


def test_runner_falls_back_when_llm_summary_is_ungrounded(
    agent_context: BomAgentContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agent.llm_config import OpenAICompatLLMSettings

    def fake_summarize(*_args, **_kwargs):
        return (
            "Critical exposure through supplier SUP-999 across all plants.",
            [
                {
                    "claim": "SUP-999 disrupts every product line.",
                    "tool": "bom_supplier_impact",
                    "pointer": "results[].data[0]",
                    "value": "SUP-999",
                }
            ],
        )

    monkeypatch.setattr(
        "app.agent.runner.summarize_run_openai_compat",
        fake_summarize,
    )
    settings = OpenAICompatLLMSettings(
        api_base="http://llm.test",
        api_key="test-key",
        model="test-model",
        gateway="test-gateway",
    )

    agent = BomAutonomousAgent(agent_context)
    result = agent.run(
        "Analyze supplier impact for SUP-002",
        mode="auto",
        llm_settings=settings,
        tool_calls=[ToolCall("bom_supplier_impact", {"supplier_id": "SUP-002"})],
    )

    report = evaluate_agent_run(result)
    assert report.passed, report.violations
    assert result.summary_notes
    assert "grounding fallback" in result.summary_notes
    assert "SUP-999" not in (result.explanation or "")
