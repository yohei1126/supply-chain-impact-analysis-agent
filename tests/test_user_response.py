from app.agent.run_report import build_run_report
from app.agent.runner import ToolCall
from app.agent.types import AgentRunResult
from app.agent.user_response import build_user_response


def test_user_response_omits_technical_fields() -> None:
    calls = [ToolCall("bom_supplier_impact", {"supplier_id": "SUP-001"})]
    results = [
        {
            "operation": "supplier_impact",
            "summary": "Downstream impact for supplier SUP-001",
            "ontology_source": "ontology/schema.py + ontology/cypher_builder.py",
            "cypher": "MATCH (c:Component)-[:SUPPLIED_BY]->(s:Supplier {id: $supplier_id})",
            "cypher_queries": [
                {
                    "graph_id": "sourcing",
                    "query_name": "components_by_supplier",
                    "cypher": "MATCH (c:Component)-[:SUPPLIED_BY]->(s:Supplier {id: $supplier_id})",
                },
                {
                    "graph_id": "ebom",
                    "query_name": "impact_products_by_components",
                    "cypher": "MATCH (c:Component)-[:USED_IN]->(p:Product)",
                },
            ],
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
    assert user["cypher_executions"]
    assert user["cypher_executions"][0]["tool"] == "bom_supplier_impact"
    assert len(user["cypher_executions"][0]["steps"]) == 2
    assert user["cypher_executions"][0]["steps"][0]["graph_id"] == "sourcing"
