"""Tests for production connector ingest metadata (L4 P5)."""

from __future__ import annotations

import pytest

from app.validation.connector_ingest import (
    ConnectorSourceSystemError,
    IngestContractVersionError,
    apply_connector_ingest,
    build_connector_context,
)
from pipeline.connectors.registry import (
    CONNECTOR_PLM_EBOM,
    CONNECTOR_SRM_SOURCING,
    connector_for_graph,
    get_connector_spec,
)


def test_connector_registry_maps_domains_to_source_systems() -> None:
    assert get_connector_spec(CONNECTOR_PLM_EBOM).source_system == "PLM"
    assert connector_for_graph("routing").source_system == "MES"
    assert connector_for_graph("sourcing").source_system == "SRM"


def test_build_connector_context_pins_live_contract_version() -> None:
    context = build_connector_context(
        CONNECTOR_SRM_SOURCING,
        as_of="2026-06-01T06:00:00Z",
    )
    assert context.graph_id == "sourcing"
    assert context.source_system == "SRM"
    assert context.graph_contract_version == "1.0.0"
    context.validate()


def test_build_connector_context_rejects_stale_contract_version() -> None:
    with pytest.raises(IngestContractVersionError):
        build_connector_context(
            CONNECTOR_PLM_EBOM,
            as_of="2026-06-01T07:00:00Z",
            graph_contract_version="0.9.0",
        )


def test_build_connector_context_rejects_wrong_source_system_in_context() -> None:
    context = build_connector_context(
        CONNECTOR_PLM_EBOM,
        as_of="2026-06-01T07:00:00Z",
    )
    bad = context.__class__(
        connector_id=context.connector_id,
        graph_id=context.graph_id,
        source_system="SRM",
        as_of=context.as_of,
        graph_contract_version=context.graph_contract_version,
    )
    with pytest.raises(ConnectorSourceSystemError):
        bad.validate()


def test_apply_connector_ingest_configures_domain_store(graph_store) -> None:
    context = build_connector_context(
        CONNECTOR_PLM_EBOM,
        as_of="2026-06-01T07:00:00Z",
    )
    apply_connector_ingest(graph_store, context)
    store = graph_store.domain("ebom")
    graph_store.add_node(
        "Product",
        {"id": "PROD-P5", "name": "Test Product", "version": "v1"},
    )
    nodes = store.all_nodes()
    product = next(n for n in nodes if n["id"] == "PROD-P5")
    props = product["properties"]
    assert props["source_system"] == "PLM"
    assert props["graph_contract_version"] == "1.0.0"
    assert props["as_of"] == "2026-06-01T07:00:00Z"
