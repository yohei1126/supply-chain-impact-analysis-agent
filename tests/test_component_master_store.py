from app.component_master_store import ComponentMasterStore
from app.federation.graph_store import GraphStore


def test_upsert_component_updates_rdb_and_graph(graph_store: GraphStore, tmp_path) -> None:
    store = ComponentMasterStore(
        graph_store=graph_store,
        duckdb_path=str(tmp_path / "bom.duckdb"),
    )
    try:
        store.upsert_component(
            {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0}
        )

        rdb_row = store.get_component_from_rdb("COMP-100")
        assert rdb_row is not None
        assert rdb_row["name"] == "Frame"

        matches = store.search_components("steel", limit=3)
        ids = [r["id"] for r in matches]
        assert "COMP-100" in ids

        graph_nodes = graph_store._all_nodes()
        assert any(n["id"] == "COMP-100" and n["label"] == "Component" for n in graph_nodes)
    finally:
        store.close()


def test_search_components_by_material(graph_store: GraphStore, tmp_path) -> None:
    store = ComponentMasterStore(
        graph_store=graph_store,
        duckdb_path=str(tmp_path / "bom.duckdb"),
    )
    try:
        store.upsert_component(
            {"id": "COMP-200", "name": "Valve", "material": "Brass", "cost": 90.0}
        )
        rows = store.search_components_by_material("brass")
        assert any(row["id"] == "COMP-200" for row in rows)
    finally:
        store.close()
