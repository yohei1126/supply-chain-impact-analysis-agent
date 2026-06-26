"""Production connector ingest context (L4 P5): pinned graph_contract_version per adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.federation.graph_store import GraphStore
from app.validation.contract_loader import get_graph_contract
from app.validation.ingest_metadata import normalize_as_of, utc_as_of_iso
from domains.bundles import get_domain_bundle
from domains.registry import GraphId
from pipeline.connectors.registry import ConnectorSpec, get_connector_spec


class IngestContractVersionError(ValueError):
    """Raised when a connector's pinned contract version does not match the live Graph Contract."""


class ConnectorSourceSystemError(ValueError):
    """Raised when source_system is not allowed for the target domain bundle."""


@dataclass(frozen=True, slots=True)
class ConnectorIngestContext:
    """Metadata stamped on every node written by one connector batch."""

    connector_id: str
    graph_id: GraphId
    source_system: str
    as_of: str
    graph_contract_version: str

    def validate(self) -> None:
        spec = get_connector_spec(self.connector_id)
        if spec.graph_id != self.graph_id:
            raise ValueError(
                f"connector {self.connector_id!r} targets graph {spec.graph_id!r}, "
                f"not {self.graph_id!r}"
            )
        if spec.source_system != self.source_system:
            raise ConnectorSourceSystemError(
                f"connector {self.connector_id!r} requires source_system "
                f"{spec.source_system!r}, got {self.source_system!r}"
            )
        bundle = get_domain_bundle(self.graph_id)
        if self.source_system not in bundle.source_systems:
            raise ConnectorSourceSystemError(
                f"source_system {self.source_system!r} is not listed for graph "
                f"{self.graph_id!r} ({sorted(bundle.source_systems)})"
            )
        live_version = get_graph_contract().version
        if self.graph_contract_version != live_version:
            raise IngestContractVersionError(
                f"connector {self.connector_id!r} pins graph_contract_version "
                f"{self.graph_contract_version!r} but live Graph Contract is {live_version!r}. "
                "Re-test the connector against the new contract or bump the pinned version."
            )


def build_connector_context(
    connector_id: str,
    *,
    as_of: str | datetime | None = None,
    graph_contract_version: str | None = None,
) -> ConnectorIngestContext:
    """Build a validated ingest context for a registered production connector."""
    spec = get_connector_spec(connector_id)
    resolved_as_of = utc_as_of_iso() if as_of is None else normalize_as_of(as_of)
    resolved_version = (
        get_graph_contract().version if graph_contract_version is None else graph_contract_version
    )
    context = ConnectorIngestContext(
        connector_id=spec.connector_id,
        graph_id=spec.graph_id,
        source_system=spec.source_system,
        as_of=resolved_as_of,
        graph_contract_version=resolved_version,
    )
    context.validate()
    return context


def apply_connector_ingest(graph: GraphStore, context: ConnectorIngestContext) -> None:
    """Configure a domain store for writes from one connector batch."""
    context.validate()
    graph.configure_domain_ingest(
        context.graph_id,
        as_of=context.as_of,
        source_system=context.source_system,
        graph_contract_version=context.graph_contract_version,
    )


def connector_context_from_spec(
    spec: ConnectorSpec,
    *,
    as_of: str | datetime,
    graph_contract_version: str | None = None,
) -> ConnectorIngestContext:
    return build_connector_context(
        spec.connector_id,
        as_of=as_of,
        graph_contract_version=graph_contract_version,
    )


__all__ = [
    "ConnectorIngestContext",
    "ConnectorSourceSystemError",
    "IngestContractVersionError",
    "apply_connector_ingest",
    "build_connector_context",
    "connector_context_from_spec",
]
