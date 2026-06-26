"""Load validated domain datasets into separate Neo4j databases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.federation.graph_store import GraphStore
from app.storage.neo4j_config import reset_neo4j
from domains.registry import GraphId
from pipeline.demo.domain_datasets import DomainDataset, build_all_domain_datasets
from pipeline.demo.ingest_as_of import configure_demo_domain_ingest

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    Driver = Any  # type: ignore[misc, assignment]


def reset_graph_data(driver: Driver, graph_ids: tuple[GraphId, ...] | None = None) -> None:
    reset_neo4j(driver, graph_ids)


def reset_lancedb(lancedb_path: str | Path) -> None:
    """Deprecated: kept for script compatibility; clears Neo4j domain databases instead."""
    del lancedb_path  # unused — graph data lives in Neo4j
    graph = GraphStore()
    try:
        reset_neo4j(graph.driver)
    finally:
        graph.close()


def load_domain_dataset(graph: GraphStore, dataset: DomainDataset) -> dict[str, int]:
    """Write one domain dataset into its Neo4j database (ontology-validated rows only)."""
    configure_demo_domain_ingest(graph, dataset.graph_id)
    store = graph.domain(dataset.graph_id)
    for node in dataset.nodes:
        store.add_node(node.label, node.payload)
    edge_count = 0
    for edge in dataset.edges:
        store.add_edge(edge)
        edge_count += 1
    return {"nodes": len(dataset.nodes), "edges": edge_count}


def load_all_domains_separately(
    graph: GraphStore,
    *,
    component_bom: list[dict[str, Any]] | None = None,
) -> dict[GraphId, dict[str, int]]:
    """Generate, validate, and load each domain graph independently."""
    datasets = build_all_domain_datasets(component_bom)
    for graph_id, dataset in datasets.items():
        errors = dataset.validate()
        if errors:
            raise ValueError(f"{graph_id} validation failed: {errors[0]}")
    stats: dict[GraphId, dict[str, int]] = {}
    for graph_id, dataset in datasets.items():
        stats[graph_id] = load_domain_dataset(graph, dataset)
    return stats
