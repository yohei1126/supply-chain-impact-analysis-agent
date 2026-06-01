from bom_graph.hybrid_store import UnifiedBomContextStore, text_to_embedding
from bom_graph.lance_graph_store import LanceGraphStore


def test_text_to_embedding_is_deterministic() -> None:
    a = text_to_embedding("steel frame")
    b = text_to_embedding("steel frame")
    c = text_to_embedding("brass valve")
    assert a == b
    assert a != c
    assert len(a) == 16


def test_upsert_component_updates_rdb_and_vector_and_graph(tmp_path) -> None:
    graph = LanceGraphStore(lancedb_path=str(tmp_path / "lancedb"))
    store = UnifiedBomContextStore(
        graph_store=graph,
        duckdb_path=str(tmp_path / "bom.duckdb"),
        lancedb_path=str(tmp_path / "lancedb"),
    )
    try:
        store.upsert_component({"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0})

        rdb_row = store.get_component_from_rdb("COMP-100")
        assert rdb_row is not None
        assert rdb_row["name"] == "Frame"

        vector_rows = store.vector_search_components("steel frame", top_k=3)
        ids = [r["id"] for r in vector_rows]
        assert "COMP-100" in ids

        graph_nodes = graph._all_nodes()
        assert any(n["id"] == "COMP-100" and n["label"] == "Component" for n in graph_nodes)
    finally:
        store.close()


def test_find_supplier_impact_for_query(tmp_path) -> None:
    graph = LanceGraphStore(lancedb_path=str(tmp_path / "lancedb"))
    store = UnifiedBomContextStore(
        graph_store=graph,
        duckdb_path=str(tmp_path / "bom.duckdb"),
        lancedb_path=str(tmp_path / "lancedb"),
    )
    try:
        graph.add_node(
            "Supplier",
            {"id": "SUP-001", "company_name": "Nihon Steel", "country": "JP", "risk_level": "High"},
        )
        graph.add_node("Product", {"id": "PROD-900", "name": "Industrial Pump", "version": "v1"})
        store.upsert_component({"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0})
        graph.add_edge(
            {
                "source_label": "Component",
                "source_id": "COMP-100",
                "target_label": "Supplier",
                "target_id": "SUP-001",
                "edge_type": "SUPPLIED_BY",
                "properties": {"lead_time_days": 14},
            }
        )
        graph.add_edge(
            {
                "source_label": "Component",
                "source_id": "COMP-100",
                "target_label": "Product",
                "target_id": "PROD-900",
                "edge_type": "USED_IN",
                "properties": {},
            }
        )

        rows = store.find_supplier_impact_for_query("steel frame", top_k=2)
        assert rows
        assert rows[0]["query_component"] == "COMP-100"
        assert rows[0]["graph_impacts"]
    finally:
        store.close()
