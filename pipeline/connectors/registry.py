"""Production connector registry (L4 P5): graph_id, source_system, contract version pinning."""

from __future__ import annotations

from dataclasses import dataclass

from domains.registry import GraphId

CONNECTOR_PLM_EBOM = "plm-ebom"
CONNECTOR_MES_ROUTING = "mes-routing"
CONNECTOR_SRM_SOURCING = "srm-sourcing"


@dataclass(frozen=True, slots=True)
class ConnectorSpec:
    """One enterprise ingest adapter bound to a domain graph."""

    connector_id: str
    graph_id: GraphId
    source_system: str
    description: str


CONNECTOR_REGISTRY: dict[str, ConnectorSpec] = {
    CONNECTOR_PLM_EBOM: ConnectorSpec(
        connector_id=CONNECTOR_PLM_EBOM,
        graph_id="ebom",
        source_system="PLM",
        description="PLM export → EBOM domain (Component, Product, USED_IN)",
    ),
    CONNECTOR_MES_ROUTING: ConnectorSpec(
        connector_id=CONNECTOR_MES_ROUTING,
        graph_id="routing",
        source_system="MES",
        description="MES / ERP-PP export → routing domain (Process, INPUT_OF, PRODUCED_BY)",
    ),
    CONNECTOR_SRM_SOURCING: ConnectorSpec(
        connector_id=CONNECTOR_SRM_SOURCING,
        graph_id="sourcing",
        source_system="SRM",
        description="SRM export → sourcing domain (Supplier, SUPPLIED_BY)",
    ),
}

GRAPH_TO_CONNECTOR: dict[GraphId, str] = {
    spec.graph_id: spec.connector_id for spec in CONNECTOR_REGISTRY.values()
}


def get_connector_spec(connector_id: str) -> ConnectorSpec:
    try:
        return CONNECTOR_REGISTRY[connector_id]
    except KeyError as exc:
        known = ", ".join(sorted(CONNECTOR_REGISTRY))
        raise KeyError(f"Unknown connector_id {connector_id!r}; known: {known}") from exc


def connector_for_graph(graph_id: GraphId) -> ConnectorSpec:
    return get_connector_spec(GRAPH_TO_CONNECTOR[graph_id])


__all__ = [
    "CONNECTOR_MES_ROUTING",
    "CONNECTOR_PLM_EBOM",
    "CONNECTOR_REGISTRY",
    "CONNECTOR_SRM_SOURCING",
    "GRAPH_TO_CONNECTOR",
    "ConnectorSpec",
    "connector_for_graph",
    "get_connector_spec",
]
