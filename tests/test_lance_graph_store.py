import pytest

from app.federation.graph_store import LanceGraphStore


def _seed_graph(store: LanceGraphStore) -> None:
    store.add_node(
        "Supplier",
        {"id": "SUP-001", "company_name": "Nihon Steel", "country": "JP", "risk_level": "High"},
    )
    store.add_node("Product", {"id": "PROD-900", "name": "Industrial Pump", "version": "v1"})
    store.add_node(
        "Process",
        {"id": "PROC-20", "name": "Heat Treatment", "work_center": "WC-7", "cycle_time_min": 35.0},
    )
    store.add_node("Component", {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0})

    store.add_edge(
        {
            "source_label": "Component",
            "source_id": "COMP-100",
            "target_label": "Supplier",
            "target_id": "SUP-001",
            "edge_type": "SUPPLIED_BY",
            "properties": {"lead_time_days": 14},
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
    store.add_edge(
        {
            "source_label": "Product",
            "source_id": "PROD-900",
            "target_label": "Process",
            "target_id": "PROC-20",
            "edge_type": "PRODUCED_BY",
            "properties": {},
        }
    )


def test_add_edge_requires_existing_nodes(tmp_path) -> None:
    store = LanceGraphStore(lancedb_path=str(tmp_path / "lancedb"))
    with pytest.raises(ValueError):
        store.add_edge(
            {
                "source_label": "Component",
                "source_id": "COMP-X",
                "target_label": "Supplier",
                "target_id": "SUP-X",
                "edge_type": "SUPPLIED_BY",
                "properties": {},
            }
        )


def test_impacted_products_by_supplier(tmp_path) -> None:
    store = LanceGraphStore(lancedb_path=str(tmp_path / "lancedb"))
    _seed_graph(store)

    rows = store.impacted_products_by_supplier("SUP-001")
    assert len(rows) == 1
    assert rows[0]["component_id"] == "COMP-100"
    assert rows[0]["product_id"] == "PROD-900"


def test_shortest_supply_path(tmp_path) -> None:
    store = LanceGraphStore(lancedb_path=str(tmp_path / "lancedb"))
    _seed_graph(store)

    rows = store.shortest_supply_path("COMP-100", "PROD-900")
    assert len(rows) == 1
    assert rows[0]["relationships"] == ["USED_IN"]
