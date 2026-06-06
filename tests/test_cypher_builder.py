"""Tests for ontology-driven Cypher generation."""

from __future__ import annotations

import pytest

from ontology.cypher_builder import QUERY_SPECS, build_query_by_name
from ontology.schema import ALLOWED_EDGES
from app.federation.cypher_queries import (
    cypher_components_by_supplier,
    cypher_products_by_components,
)


def test_query_specs_align_with_allowed_edges() -> None:
    for spec in QUERY_SPECS.values():
        assert spec.edge_type in ALLOWED_EDGES


def test_components_by_supplier_cypher() -> None:
    cypher = build_query_by_name("components_by_supplier")
    assert "SUPPLIED_BY" in cypher
    assert "$supplier_id" in cypher
    assert "Component" in cypher and "Supplier" in cypher


def test_products_by_components_cypher() -> None:
    cypher = build_query_by_name("products_by_components", component_ids_literal="'COMP-100'")
    assert "USED_IN" in cypher
    assert "COMP-100" in cypher


def test_domain_validation_rejects_wrong_graph() -> None:
    from domains.registry import assert_edge_allowed_in_graph

    with pytest.raises(ValueError):
        assert_edge_allowed_in_graph("ebom", "SUPPLIED_BY")  # type: ignore[arg-type]


def test_direct_component_product_link_cypher() -> None:
    cypher = build_query_by_name(
        "direct_component_product_link",
        source_id="COMP-103",
        target_id="PROD-901",
    )
    assert "USED_IN" in cypher
    assert "COMP-103" in cypher and "PROD-901" in cypher


def test_app_layer_wraps_ontology() -> None:
    cypher = cypher_components_by_supplier()
    assert "MATCH" in cypher
    wrapped = cypher_products_by_components({"COMP-103"})
    assert "COMP-103" in wrapped
