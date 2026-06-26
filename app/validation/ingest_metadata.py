"""Ingest-time graph metadata stamped on Neo4j nodes (outside L1 Pydantic models)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.validation.contract_loader import get_graph_contract
from domains.registry import GraphId

NODE_STORAGE_PROPERTY_KEYS: frozenset[str] = frozenset(
    {
        "graph_id",
        "as_of",
        "graph_contract_version",
        "source_system",
    }
)


def utc_as_of_iso(*, at: datetime | None = None) -> str:
    """Return an ISO-8601 UTC timestamp with Z suffix."""
    moment = at or datetime.now(tz=timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_as_of(value: str | datetime) -> str:
    if isinstance(value, datetime):
        return utc_as_of_iso(at=value)
    text = value.strip()
    if text.endswith("Z"):
        return text
    if "+" in text or text.endswith("UTC"):
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return utc_as_of_iso(at=parsed)
    return f"{text}Z" if "T" in text else f"{text}T00:00:00Z"


def ontology_payload_from_stored_properties(props: dict[str, Any]) -> dict[str, Any]:
    """Strip storage metadata before Pydantic ontology validation."""
    return {k: v for k, v in props.items() if k not in NODE_STORAGE_PROPERTY_KEYS}


def stamp_node_properties(
    props: dict[str, Any],
    *,
    graph_id: GraphId,
    as_of: str,
    source_system: str | None = None,
    graph_contract_version: str | None = None,
) -> dict[str, Any]:
    """Attach ingest metadata to validated ontology node properties."""
    stamped = dict(props)
    stamped["graph_id"] = graph_id
    stamped["as_of"] = normalize_as_of(as_of)
    stamped["graph_contract_version"] = graph_contract_version or get_graph_contract().version
    if source_system:
        stamped["source_system"] = source_system
    return stamped
