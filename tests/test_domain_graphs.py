import pytest

from app.federation.graph_store import GraphStore
from domains.registry import graph_for_edge


def _seed_graph(store: GraphStore) -> None:
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


def test_component_replicated_in_three_domain_stores(graph_store: GraphStore) -> None:
    graph_store.add_node("Component", {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0})

    for graph_id in ("ebom", "routing", "sourcing"):
        nodes = graph_store.domain(graph_id).all_nodes()
        assert any(n["id"] == "COMP-100" and n["label"] == "Component" for n in nodes)


def test_edges_live_in_single_domain_store(graph_store: GraphStore) -> None:
    _seed_graph(graph_store)

    assert len(graph_store.domain("sourcing").all_edges()) == 1
    assert graph_store.domain("sourcing").all_edges()[0]["edge_type"] == "SUPPLIED_BY"

    assert len(graph_store.domain("ebom").all_edges()) == 1
    assert graph_store.domain("ebom").all_edges()[0]["edge_type"] == "USED_IN"

    assert len(graph_store.domain("routing").all_edges()) == 1
    assert graph_store.domain("routing").all_edges()[0]["edge_type"] == "PRODUCED_BY"


def test_domain_edge_rejected_in_wrong_store(graph_store: GraphStore) -> None:
    domain = graph_store.domain("ebom")
    domain.add_node("Component", {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0})
    domain.add_node("Product", {"id": "PROD-900", "name": "Pump", "version": "v1"})

    with pytest.raises(ValueError, match="not allowed in graph ebom"):
        domain.add_edge(
            {
                "source_label": "Component",
                "source_id": "COMP-100",
                "target_label": "Supplier",
                "target_id": "SUP-001",
                "edge_type": "SUPPLIED_BY",
                "properties": {},
            }
        )


def test_graph_for_edge_mapping() -> None:
    assert graph_for_edge("USED_IN") == "ebom"
    assert graph_for_edge("SUPPLIED_BY") == "sourcing"
    assert graph_for_edge("INPUT_OF") == "routing"


def test_federated_traversal_matches_prior_behavior(graph_store: GraphStore) -> None:
    _seed_graph(graph_store)

    impact = graph_store.impacted_products_by_supplier("SUP-001")
    assert len(impact) == 1
    assert impact[0]["product_id"] == "PROD-900"

    path = graph_store.shortest_supply_path("COMP-100", "PROD-900")
    assert path[0]["relationships"] == ["USED_IN"]
