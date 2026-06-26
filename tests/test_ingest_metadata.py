"""Tests for ingest-time as_of and graph metadata stamping."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.federation.composer import read_domain_as_of
from app.validation.ingest_metadata import (
    normalize_as_of,
    ontology_payload_from_stored_properties,
    stamp_node_properties,
    utc_as_of_iso,
)
from ontology.schema import ComponentNode
from pipeline.demo.ingest_as_of import DEMO_DOMAIN_AS_OF
from pipeline.demo.load_domains import load_all_domains_separately


def test_utc_as_of_iso_uses_z_suffix() -> None:
    assert utc_as_of_iso(at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)) == "2026-06-01T08:00:00Z"


def test_normalize_as_of_accepts_z_and_offset() -> None:
    assert normalize_as_of("2026-06-01T08:00:00Z") == "2026-06-01T08:00:00Z"
    assert normalize_as_of("2026-06-01T08:00:00+00:00") == "2026-06-01T08:00:00Z"


def test_stamp_node_properties_adds_contract_metadata() -> None:
    stamped = stamp_node_properties(
        {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1200.0},
        graph_id="sourcing",
        as_of="2026-06-01T08:00:00Z",
        source_system="demo-sourcing",
    )
    assert stamped["as_of"] == "2026-06-01T08:00:00Z"
    assert stamped["graph_contract_version"] == "1.0.0"
    assert stamped["source_system"] == "demo-sourcing"
    assert stamped["graph_id"] == "sourcing"


def test_ontology_payload_from_stored_properties_strips_metadata() -> None:
    props = stamp_node_properties(
        {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1200.0},
        graph_id="ebom",
        as_of="2026-06-01T08:00:00Z",
        source_system="demo-ebom",
    )
    payload = ontology_payload_from_stored_properties(props)
    node = ComponentNode(**payload)
    assert node.id == "COMP-100"


@pytest.mark.usefixtures("graph_store")
def test_load_domains_stamps_as_of_on_nodes(graph_store) -> None:
    load_all_domains_separately(graph_store)
    for graph_id, expected in DEMO_DOMAIN_AS_OF.items():
        assert read_domain_as_of(graph_store, graph_id) == expected
