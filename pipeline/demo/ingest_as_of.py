"""Deterministic demo ingest timestamps per domain graph (production connector IDs)."""

from __future__ import annotations

from app.federation.graph_store import GraphStore
from app.validation.connector_ingest import apply_connector_ingest, build_connector_context
from domains.registry import GraphId
from pipeline.connectors.registry import GRAPH_TO_CONNECTOR

# Within 48h skew window for default federation demos; routing is newest.
DEMO_DOMAIN_AS_OF: dict[GraphId, str] = {
    "sourcing": "2026-06-01T06:00:00Z",
    "ebom": "2026-06-01T07:00:00Z",
    "routing": "2026-06-01T07:30:00Z",
}


def configure_demo_domain_ingest(graph: GraphStore, graph_id: GraphId) -> None:
    connector_id = GRAPH_TO_CONNECTOR[graph_id]
    context = build_connector_context(connector_id, as_of=DEMO_DOMAIN_AS_OF[graph_id])
    apply_connector_ingest(graph, context)


def configure_all_demo_domain_ingest(graph: GraphStore) -> None:
    for graph_id in DEMO_DOMAIN_AS_OF:
        configure_demo_domain_ingest(graph, graph_id)
