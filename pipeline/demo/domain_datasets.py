"""Per-domain synthetic dataset builders with ontology validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import ValidationError

from domains.registry import GraphId
from ontology.schema import RelationEdge, validate_node_payload
from pipeline.demo.sample_data import (
    COMPONENT_BOM,
    PROCESSES,
    PRODUCT_PROCESSES,
    PRODUCTS,
    SUPPLIERS,
)

GraphIdLiteral = Literal["ebom", "routing", "sourcing"]


@dataclass(frozen=True)
class DomainNode:
    label: str
    payload: dict[str, Any]


@dataclass
class DomainDataset:
    graph_id: GraphIdLiteral
    owner_team: str
    nodes: list[DomainNode] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)

    def validate(self) -> list[str]:
        """Run Pydantic validators; return human-readable errors (empty if ok)."""
        errors: list[str] = []
        for node in self.nodes:
            try:
                validate_node_payload(node.label, node.payload)
            except (ValidationError, ValueError) as exc:
                errors.append(f"{self.graph_id} node {node.label}:{node.payload.get('id')}: {exc}")
        for edge in self.edges:
            try:
                RelationEdge(**edge)
            except (ValidationError, ValueError) as exc:
                errors.append(f"{self.graph_id} edge {edge.get('edge_type')}: {exc}")
        return errors


def _component_nodes(component_bom: list[dict[str, Any]]) -> list[DomainNode]:
    return [DomainNode("Component", row["component"]) for row in component_bom]


def build_sourcing_dataset(
    component_bom: list[dict[str, Any]] | None = None,
) -> DomainDataset:
    """Procurement-owned slice: suppliers, bridge components, SUPPLIED_BY."""
    rows = component_bom if component_bom is not None else COMPONENT_BOM
    dataset = DomainDataset(graph_id="sourcing", owner_team="procurement")
    dataset.nodes.extend(DomainNode("Supplier", supplier) for supplier in SUPPLIERS)
    dataset.nodes.extend(_component_nodes(rows))
    for row in rows:
        dataset.edges.append(
            {
                "source_label": "Component",
                "source_id": row["component"]["id"],
                "target_label": "Supplier",
                "target_id": row["supplier"],
                "edge_type": "SUPPLIED_BY",
                "properties": {"lead_time_days": row.get("lead_time_days", 14)},
            }
        )
    return dataset


def build_ebom_dataset(
    component_bom: list[dict[str, Any]] | None = None,
) -> DomainDataset:
    """Engineering-owned slice: products, bridge components, USED_IN."""
    rows = component_bom if component_bom is not None else COMPONENT_BOM
    dataset = DomainDataset(graph_id="ebom", owner_team="engineering")
    dataset.nodes.extend(DomainNode("Product", product) for product in PRODUCTS)
    dataset.nodes.extend(_component_nodes(rows))
    for row in rows:
        component_id = row["component"]["id"]
        for product_id in row["products"]:
            dataset.edges.append(
                {
                    "source_label": "Component",
                    "source_id": component_id,
                    "target_label": "Product",
                    "target_id": product_id,
                    "edge_type": "USED_IN",
                    "properties": {},
                }
            )
    return dataset


def build_routing_dataset(
    component_bom: list[dict[str, Any]] | None = None,
    product_processes: list[tuple[str, str]] | None = None,
) -> DomainDataset:
    """Manufacturing-owned slice: processes, products, components, routing edges."""
    rows = component_bom if component_bom is not None else COMPONENT_BOM
    pairs = product_processes if product_processes is not None else PRODUCT_PROCESSES
    dataset = DomainDataset(graph_id="routing", owner_team="manufacturing")
    dataset.nodes.extend(DomainNode("Process", process) for process in PROCESSES)
    dataset.nodes.extend(DomainNode("Product", product) for product in PRODUCTS)
    dataset.nodes.extend(_component_nodes(rows))
    for row in rows:
        component_id = row["component"]["id"]
        for process_id in row["processes"]:
            dataset.edges.append(
                {
                    "source_label": "Component",
                    "source_id": component_id,
                    "target_label": "Process",
                    "target_id": process_id,
                    "edge_type": "INPUT_OF",
                    "properties": {"qty": 1},
                }
            )
    for product_id, process_id in pairs:
        dataset.edges.append(
            {
                "source_label": "Product",
                "source_id": product_id,
                "target_label": "Process",
                "target_id": process_id,
                "edge_type": "PRODUCED_BY",
                "properties": {},
            }
        )
    return dataset


def build_all_domain_datasets(
    component_bom: list[dict[str, Any]] | None = None,
) -> dict[GraphId, DomainDataset]:
    rows = component_bom if component_bom is not None else COMPONENT_BOM
    return {
        "sourcing": build_sourcing_dataset(rows),
        "ebom": build_ebom_dataset(rows),
        "routing": build_routing_dataset(rows),
    }


def validate_all_datasets(datasets: dict[GraphId, DomainDataset]) -> dict[str, list[str]]:
    return {graph_id: ds.validate() for graph_id, ds in datasets.items()}


def dataset_summary(dataset: DomainDataset) -> dict[str, Any]:
    node_counts: dict[str, int] = {}
    for node in dataset.nodes:
        node_counts[node.label] = node_counts.get(node.label, 0) + 1
    edge_counts: dict[str, int] = {}
    for edge in dataset.edges:
        edge_counts[edge["edge_type"]] = edge_counts.get(edge["edge_type"], 0) + 1
    return {
        "graph_id": dataset.graph_id,
        "owner_team": dataset.owner_team,
        "nodes": node_counts,
        "edges": edge_counts,
    }
