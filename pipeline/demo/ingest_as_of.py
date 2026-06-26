"""Deterministic demo ingest timestamps per domain graph."""

from __future__ import annotations

from app.federation.graph_store import GraphStore
from domains.registry import GraphId

# Within 48h skew window for default federation demos; routing is newest.
DEMO_DOMAIN_AS_OF: dict[GraphId, str] = {
    "sourcing": "2026-06-01T06:00:00Z",
    "ebom": "2026-06-01T07:00:00Z",
    "routing": "2026-06-01T07:30:00Z",
}


def configure_demo_domain_ingest(graph: GraphStore, graph_id: GraphId) -> None:
    graph.configure_domain_ingest(
        graph_id,
        as_of=DEMO_DOMAIN_AS_OF[graph_id],
        source_system=f"demo-{graph_id}",
    )


def configure_all_demo_domain_ingest(graph: GraphStore) -> None:
    for graph_id in DEMO_DOMAIN_AS_OF:
        configure_demo_domain_ingest(graph, graph_id)
