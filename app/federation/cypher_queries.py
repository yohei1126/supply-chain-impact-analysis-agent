"""Domain-scoped Cypher generation: ontology recipes + domain registry validation."""

from __future__ import annotations

from domains.registry import GraphId, assert_edge_allowed_in_graph
from app.federation.cypher_executor import cypher_string_list
from ontology.cypher_builder import QUERY_SPECS, build_query, build_query_by_name
from ontology.schema import EdgeType

ONTOLOGY_SOURCE = "ontology/schema.py + ontology/cypher_builder.py"


def _assert_query_in_domain(graph_id: GraphId, query_name: str) -> EdgeType:
    spec = QUERY_SPECS[query_name]
    assert_edge_allowed_in_graph(graph_id, spec.edge_type)
    return spec.edge_type


def cypher_components_by_supplier() -> str:
    _assert_query_in_domain("sourcing", "components_by_supplier")
    return build_query_by_name("components_by_supplier")


def cypher_products_by_components(component_ids: set[str]) -> str:
    _assert_query_in_domain("ebom", "products_by_components")
    return build_query_by_name(
        "products_by_components",
        component_ids_literal=cypher_string_list(component_ids),
    )


def cypher_processes_by_components(component_ids: set[str]) -> str:
    _assert_query_in_domain("routing", "processes_by_components")
    return build_query_by_name(
        "processes_by_components",
        component_ids_literal=cypher_string_list(component_ids),
    )


def cypher_supplier_counts(component_ids: set[str]) -> str:
    _assert_query_in_domain("sourcing", "supplier_counts_by_components")
    return build_query_by_name(
        "supplier_counts_by_components",
        component_ids_literal=cypher_string_list(component_ids),
    )


def cypher_impact_by_components(component_ids: set[str]) -> str:
    _assert_query_in_domain("ebom", "impact_products_by_components")
    return build_query_by_name(
        "impact_products_by_components",
        component_ids_literal=cypher_string_list(component_ids),
    )


def cypher_direct_supply_path(from_component_id: str, to_product_id: str) -> str:
    _assert_query_in_domain("ebom", "direct_component_product_link")
    return build_query_by_name(
        "direct_component_product_link",
        source_id=from_component_id.strip(),
        target_id=to_product_id.strip(),
    )
