from bom_graph.agent.run_report import build_run_report
from bom_graph.agent.runner import ToolCall
from bom_graph.agent.types import AgentRunResult
from bom_graph.agent.user_response import build_user_response


def test_user_response_omits_technical_fields() -> None:
    calls = [ToolCall("bom_supplier_impact", {"supplier_id": "SUP-001"})]
    results = [
        {
            "operation": "supplier_impact",
            "summary": "Downstream impact for supplier SUP-001",
            "data": [
                {
                    "supplier_id": "SUP-001",
                    "component_id": "COMP-100",
                    "component_name": "Frame",
                    "product_id": "PROD-900",
                    "product_name": "Pump",
                    "component_cost": 1500.0,
                }
            ],
        }
    ]
    report = build_run_report(
        "impact SUP-001", "tools", calls, results, "Planned by heuristic", None
    )
    internal = AgentRunResult(
        goal="impact SUP-001",
        mode="tools",
        tool_calls=calls,
        results=results,
        explanation="Goal: x\n\n**bom_supplier_impact** — summary",
        evidence=[{"claim": "c", "tool": "bom_supplier_impact", "pointer": "p", "value": "v"}],
        run_report=report,
        graph_view={"node_count": 2},
    )
    user = build_user_response(internal)
    assert user["goal"] == "impact SUP-001"
    assert "COMP-100" in user["explanation"] or user["findings"]
    assert user["findings"]
    assert user["evidence"]
    assert user["evidence"][0]["claim"]
    assert "tool_calls" not in user
    assert "pointer" not in str(user["evidence"])
