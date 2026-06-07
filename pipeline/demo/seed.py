"""Orchestrate demo seeding across three domain pipelines."""

from __future__ import annotations

from typing import Any

from app.component_master_store import ComponentMasterStore
from app.federation.graph_store import GraphStore
from domains.ebom import pipeline as ebom_pipeline
from domains.routing import pipeline as routing_pipeline
from domains.sourcing import pipeline as sourcing_pipeline
from pipeline.demo.sample_data import (
    COMPONENT_BOM,
    PROCESSES,
    PRODUCT_PROCESSES,
    PRODUCTS,
    SUPPLIERS,
)


def seed_complex_bom(
    graph: GraphStore,
    component_master: ComponentMasterStore | None = None,
) -> dict[str, int]:
    """
    Load demo BOM data through domain-owned pipelines into three Neo4j databases.

    Order: domain nodes → shared components (master + graph replication) → domain edges.
    """
    sourcing_pipeline.seed_nodes(graph)
    ebom_pipeline.seed_nodes(graph)
    routing_pipeline.seed_nodes(graph)

    for row in COMPONENT_BOM:
        component = row["component"]
        if component_master is not None:
            component_master.upsert_component(component)
        else:
            graph.add_node("Component", component)

    sourcing_pipeline.seed_edges(graph, COMPONENT_BOM)
    ebom_pipeline.seed_edges(graph, COMPONENT_BOM)
    routing_pipeline.seed_edges(graph, COMPONENT_BOM, PRODUCT_PROCESSES)

    return {
        "suppliers": len(SUPPLIERS),
        "products": len(PRODUCTS),
        "processes": len(PROCESSES),
        "components": len(COMPONENT_BOM),
    }


def seed_domain_only(
    graph: GraphStore,
    graph_id: str,
    component_bom: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Run a single domain pipeline (for ingest scripts and tests)."""
    rows = component_bom if component_bom is not None else COMPONENT_BOM
    if graph_id == "sourcing":
        nodes = sourcing_pipeline.seed_nodes(graph)
        edges = sourcing_pipeline.seed_edges(graph, rows)
    elif graph_id == "ebom":
        nodes = ebom_pipeline.seed_nodes(graph)
        edges = ebom_pipeline.seed_edges(graph, rows)
    elif graph_id == "routing":
        nodes = routing_pipeline.seed_nodes(graph)
        edges = routing_pipeline.seed_edges(graph, rows, PRODUCT_PROCESSES)
    else:
        raise ValueError(f"Unknown graph_id: {graph_id}")
    return {"nodes": nodes, "edges": edges}
