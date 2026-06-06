"""Execute Cypher queries against domain Lance graphs via lance-graph."""

from __future__ import annotations

import re
from typing import Any

import pyarrow as pa
from lance_graph import CypherQuery, GraphConfig

from app.storage.domain_store import DomainLanceGraphStore
from domains.registry import GraphId

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

DOMAIN_NODE_LABELS: dict[GraphId, tuple[str, ...]] = {
    "sourcing": ("Component", "Supplier"),
    "ebom": ("Component", "Product"),
    "routing": ("Component", "Process", "Product"),
}

DOMAIN_EDGE_TYPES: dict[GraphId, tuple[str, ...]] = {
    "sourcing": ("SUPPLIED_BY",),
    "ebom": ("USED_IN",),
    "routing": ("INPUT_OF", "PRODUCED_BY"),
}

EDGE_OPTIONAL_PROPERTIES: dict[str, tuple[str, ...]] = {
    "SUPPLIED_BY": ("lead_time_days",),
    "USED_IN": (),
    "INPUT_OF": (),
    "PRODUCED_BY": (),
}


def _validate_id(value: str) -> str:
    if not _ID_PATTERN.match(value):
        raise ValueError(f"Invalid graph id: {value!r}")
    return value


def cypher_string_list(ids: set[str] | list[str]) -> str:
    return ", ".join(f"'{_validate_id(item)}'" for item in sorted(set(ids)))


def pydict_to_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    if not result:
        return []
    keys = list(result.keys())
    if not keys:
        return []
    length = len(result[keys[0]])
    return [{key: result[key][index] for key in keys} for index in range(length)]


def _nodes_table(domain: DomainLanceGraphStore, label: str) -> pa.Table:
    rows: list[dict[str, Any]] = []
    for node in domain.all_nodes():
        if node["label"] != label:
            continue
        rows.append({"id": node["id"], **node["properties"]})
    if not rows:
        return pa.table({"id": pa.array([], type=pa.string())})
    return pa.Table.from_pylist(rows)


def _edges_table(domain: DomainLanceGraphStore, edge_type: str) -> pa.Table:
    rows: list[dict[str, Any]] = []
    for edge in domain.all_edges():
        if edge["edge_type"] != edge_type:
            continue
        row = {
            "source_id": edge["source_id"],
            "target_id": edge["target_id"],
            **(edge.get("properties") or {}),
        }
        for prop in EDGE_OPTIONAL_PROPERTIES.get(edge_type, ()):
            row.setdefault(prop, None)
        rows.append(row)
    base_fields: dict[str, Any] = {
        "source_id": pa.array([], type=pa.string()),
        "target_id": pa.array([], type=pa.string()),
    }
    for prop in EDGE_OPTIONAL_PROPERTIES.get(edge_type, ()):
        base_fields[prop] = pa.array([], type=pa.int64())
    if not rows:
        return pa.table(base_fields)
    return pa.Table.from_pylist(rows)


def build_domain_datasets(domain: DomainLanceGraphStore, graph_id: GraphId) -> dict[str, pa.Table]:
    datasets: dict[str, pa.Table] = {}
    for label in DOMAIN_NODE_LABELS[graph_id]:
        datasets[label] = _nodes_table(domain, label)
    for edge_type in DOMAIN_EDGE_TYPES[graph_id]:
        datasets[edge_type] = _edges_table(domain, edge_type)
    return datasets


def build_graph_config(graph_id: GraphId) -> GraphConfig:
    builder = GraphConfig.builder()
    for label in DOMAIN_NODE_LABELS[graph_id]:
        builder = builder.with_node_label(label, "id")
    for edge_type in DOMAIN_EDGE_TYPES[graph_id]:
        builder = builder.with_relationship(edge_type, "source_id", "target_id")
    return builder.build()


def execute_domain_cypher(
    domain: DomainLanceGraphStore,
    graph_id: GraphId,
    cypher: str,
    *,
    parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = build_graph_config(graph_id)
    datasets = build_domain_datasets(domain, graph_id)
    query = CypherQuery(cypher).with_config(config)
    if parameters:
        for name, value in parameters.items():
            query = query.with_parameter(name, value)
    result = query.execute(datasets)
    return pydict_to_rows(result.to_pydict())
