"""Organization-owned domain slices (ebom, routing, sourcing).

Each domain packages its bundle metadata, ingest pipeline, and (future) domain tools.
Shared schema and federation live in `ontology/` and `app/federation/`.
"""

from domains.registry import (
    DOMAIN_GRAPHS,
    EDGE_TO_GRAPH,
    NODE_TO_GRAPHS,
    GraphId,
    assert_edge_allowed_in_graph,
    assert_node_allowed_in_graph,
    graph_for_edge,
    graphs_for_node,
)

__all__ = [
    "DOMAIN_GRAPHS",
    "EDGE_TO_GRAPH",
    "GraphId",
    "NODE_TO_GRAPHS",
    "assert_edge_allowed_in_graph",
    "assert_node_allowed_in_graph",
    "graph_for_edge",
    "graphs_for_node",
]
