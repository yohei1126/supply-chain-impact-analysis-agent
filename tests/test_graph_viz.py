from app.agent.runner import ToolCall
from app.graph_viz import build_graph_view, extract_seed_keys, graph_view_for_run
from app.federation.graph_store import LanceGraphStore


def _seed_mini_graph(store: LanceGraphStore) -> None:
    store.add_node(
        "Supplier",
        {"id": "SUP-001", "company_name": "Nihon Steel", "country": "JP", "risk_level": "High"},
    )
    store.add_node(
        "Component",
        {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0},
    )
    store.add_node("Product", {"id": "PROD-900", "name": "Industrial Pump", "version": "v1"})
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


def test_extract_seed_keys_supplier_impact() -> None:
    calls = [ToolCall("bom_supplier_impact", {"supplier_id": "SUP-001"})]
    results = [
        {
            "operation": "supplier_impact",
            "data": [
                {
                    "supplier_id": "SUP-001",
                    "component_id": "COMP-100",
                    "product_id": "PROD-900",
                }
            ],
        }
    ]
    seeds = extract_seed_keys(calls, results)
    assert ("Supplier", "SUP-001") in seeds
    assert ("Component", "COMP-100") in seeds
    assert ("Product", "PROD-900") in seeds


def test_graph_view_for_run(tmp_path) -> None:
    store = LanceGraphStore(lancedb_path=str(tmp_path / "lancedb"))
    _seed_mini_graph(store)
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
    view = graph_view_for_run(store, calls, results)
    assert view["node_count"] >= 3
    assert view["edge_count"] >= 2
    ids = {n["id"] for n in view["nodes"]}
    assert "Component:COMP-100" in ids
    assert "Product:PROD-900" in ids
