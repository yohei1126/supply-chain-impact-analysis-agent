from app.exploration import GraphExplorer
from app.federation.graph_store import GraphStore
from app.tools import exploration_tool_definitions, run_exploration_tool


def _seed(store: GraphStore) -> None:
    store.add_node(
        "Supplier",
        {"id": "SUP-001", "company_name": "Nihon Steel", "country": "JP", "risk_level": "High"},
    )
    store.add_node("Product", {"id": "PROD-900", "name": "Industrial Pump", "version": "v1"})
    store.add_node("Component", {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0})
    store.add_edge(
        {
            "source_label": "Component",
            "source_id": "COMP-100",
            "target_label": "Supplier",
            "target_id": "SUP-001",
            "edge_type": "SUPPLIED_BY",
            "properties": {},
        }
    )
    store.add_edge(
        {
            "source_label": "Component",
            "source_id": "COMP-100",
            "target_label": "Product",
            "target_id": "PROD-900",
            "edge_type": "USED_IN",
            "properties": {},
        }
    )


def test_exploration_tool_definitions_shape() -> None:
    tools = exploration_tool_definitions()
    names = {t["name"] for t in tools}
    assert names == {"bom_supplier_impact", "bom_supply_path"}


def test_run_exploration_tool_supplier_impact(graph_store: GraphStore) -> None:
    _seed(graph_store)
    explorer = GraphExplorer(graph_store)

    payload = run_exploration_tool(explorer, "bom_supplier_impact", supplier_id="SUP-001")
    assert payload["operation"] == "supplier_impact"
    assert payload["data"]
    assert payload["data"][0]["component_id"] == "COMP-100"
    assert "cypher" in payload
    assert "MATCH" in payload["cypher"]
    assert payload["cypher_queries"]
