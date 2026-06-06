from __future__ import annotations

from typing import Literal

from ontology.schema import EdgeType, NodeLabel

GraphId = Literal["ebom", "routing", "sourcing"]

DOMAIN_GRAPHS: dict[GraphId, dict[str, set[str]]] = {
    "ebom": {
        "nodes": {"Component", "Product"},
        "edges": {"USED_IN"},
    },
    "routing": {
        "nodes": {"Component", "Process", "Product"},
        "edges": {"INPUT_OF", "PRODUCED_BY"},
    },
    "sourcing": {
        "nodes": {"Component", "Supplier"},
        "edges": {"SUPPLIED_BY"},
    },
}

EDGE_TO_GRAPH: dict[EdgeType, GraphId] = {
    "USED_IN": "ebom",
    "SUPPLIED_BY": "sourcing",
    "INPUT_OF": "routing",
    "PRODUCED_BY": "routing",
}

NODE_TO_GRAPHS: dict[NodeLabel, tuple[GraphId, ...]] = {
    "Component": ("ebom", "routing", "sourcing"),
    "Product": ("ebom", "routing"),
    "Process": ("routing",),
    "Supplier": ("sourcing",),
}


def graph_for_edge(edge_type: EdgeType) -> GraphId:
    return EDGE_TO_GRAPH[edge_type]


def graphs_for_node(node_type: NodeLabel) -> tuple[GraphId, ...]:
    return NODE_TO_GRAPHS[node_type]


def assert_edge_allowed_in_graph(graph_id: GraphId, edge_type: EdgeType) -> None:
    if edge_type not in DOMAIN_GRAPHS[graph_id]["edges"]:
        raise ValueError(f"edge {edge_type} is not allowed in graph {graph_id}")


def assert_node_allowed_in_graph(graph_id: GraphId, node_type: NodeLabel) -> None:
    if node_type not in DOMAIN_GRAPHS[graph_id]["nodes"]:
        raise ValueError(f"node type {node_type} is not allowed in graph {graph_id}")
