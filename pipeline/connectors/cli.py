"""CLI helpers for domain ingest scripts."""

from __future__ import annotations

import os

from app.federation.graph_store import GraphStore
from app.validation.connector_ingest import apply_connector_ingest, build_connector_context


def configure_connector_from_env(graph: GraphStore, connector_id: str) -> None:
    """Apply production connector ingest metadata (optional CONNECTOR_AS_OF env)."""
    as_of = os.getenv("CONNECTOR_AS_OF")
    context = build_connector_context(
        connector_id,
        as_of=as_of if as_of else None,
    )
    apply_connector_ingest(graph, context)
