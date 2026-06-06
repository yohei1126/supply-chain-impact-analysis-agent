from app.agent.explain import explain_results_heuristic
from app.agent.runner import ToolCall


def test_heuristic_supplier_impact_explanation() -> None:
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
                    "product_name": "Industrial Pump",
                    "component_cost": 1500.0,
                }
            ],
        }
    ]
    explanation, evidence = explain_results_heuristic("impact SUP-001", calls, results)
    assert "COMP-100" in explanation
    assert "PROD-900" in explanation
    assert len(evidence) >= 1
    assert evidence[0]["tool"] == "bom_supplier_impact"
