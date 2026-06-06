from app.agent.run_report import build_run_report
from app.agent.types import ToolCall


def test_run_report_supplier_impact() -> None:
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
        "supplier impact SUP-001",
        "tools",
        calls,
        results,
        "Planned by heuristic",
        "Summary by heuristic",
    )

    assert len(report["skills"]) == 2
    assert report["planning"]["mode"] == "tools"
    assert report["executions"][0]["tool"] == "bom_supplier_impact"
    assert "SUP-001" in report["executions"][0]["query_description"]
    assert "LanceGraph" in report["executions"][0]["stores"][0]
    assert report["executions"][0]["row_count"] == 1
    assert report["executions"][0]["highlights"]


def test_run_report_empty_tools() -> None:
    report = build_run_report("hello world", "tools", [], [], "Planned by heuristic", None)
    assert report["executions"] == []
    assert report["planning"]["tool_count"] == 0
