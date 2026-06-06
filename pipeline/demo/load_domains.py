"""Load validated domain datasets into separate LanceDB graph paths."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.federation.graph_store import LanceGraphStore
from domains.registry import GraphId
from pipeline.demo.domain_datasets import DomainDataset, build_all_domain_datasets


def reset_lancedb(lancedb_path: str | Path) -> None:
    path = Path(lancedb_path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def load_domain_dataset(graph: LanceGraphStore, dataset: DomainDataset) -> dict[str, int]:
    """Write one domain dataset into its Lance path (ontology-validated rows only)."""
    store = graph.domain(dataset.graph_id)
    for node in dataset.nodes:
        store.add_node(node.label, node.payload)
    edge_count = 0
    for edge in dataset.edges:
        store.add_edge(edge)
        edge_count += 1
    return {"nodes": len(dataset.nodes), "edges": edge_count}


def load_all_domains_separately(
    graph: LanceGraphStore,
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
