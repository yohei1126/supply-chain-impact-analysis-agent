from __future__ import annotations

from collections import deque
from typing import Any

from domains.registry import (
    DOMAIN_GRAPHS,
    GraphId,
    graph_for_edge,
    graphs_for_node,
)
from app.storage.neo4j_config import ensure_domain_databases, get_driver
from app.storage.neo4j_domain_store import Neo4jDomainStore
from ontology.schema import RelationEdge, validate_node_payload

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    Driver = Any  # type: ignore[misc, assignment]


class GraphStore:
    """
    Federated graph facade over three domain Neo4j databases (ebom, routing, sourcing).

    External API matches the original store; cross-domain traversals federate at query
    time on shared node IDs.
    """

    def __init__(
        self,
        driver: Driver | None = None,
        *,
        uri: str | None = None,
        auth: tuple[str, str] | None = None,
    ):
        self.driver = driver or get_driver(uri=uri, auth=auth)
        ensure_domain_databases(self.driver)
        self.domains: dict[GraphId, Neo4jDomainStore] = {
            graph_id: Neo4jDomainStore(graph_id, self.driver) for graph_id in DOMAIN_GRAPHS
        }

    def close(self) -> None:
        self.driver.close()

    def domain(self, graph_id: GraphId) -> Neo4jDomainStore:
        return self.domains[graph_id]

    def add_node(self, node_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        validate_node_payload(node_type, payload)
        target_graphs = graphs_for_node(node_type)  # type: ignore[arg-type]
        result: dict[str, Any] | None = None
        for graph_id in target_graphs:
            result = self.domains[graph_id].add_node(node_type, payload)
        if result is None:
            raise ValueError(f"Unknown node type: {node_type}")
        return result

    def add_edge(self, payload: dict[str, Any]) -> dict[str, Any]:
        edge = RelationEdge(**payload)
        graph_id = graph_for_edge(edge.edge_type)
        return self.domains[graph_id].add_edge(payload)

    def _edges_for_types(
        self,
        edge_types: set[str],
        graph_ids: tuple[GraphId, ...],
    ) -> list[dict[str, Any]]:
        edges: list[dict[str, Any]] = []
        for graph_id in graph_ids:
            for edge in self.domains[graph_id].all_edges():
                if edge["edge_type"] in edge_types:
                    edges.append(edge)
        return edges

    def impacted_products_by_supplier(self, supplier_id: str) -> list[dict[str, Any]]:
        from app.federation.analysis import federated_impact_rows

        return federated_impact_rows(self, supplier_id)

    def shortest_supply_path(self, from_component_id: str, to_product_id: str) -> list[dict[str, Any]]:
        path_edge_types = {"USED_IN", "INPUT_OF", "PRODUCED_BY"}
        edges = self._edges_for_types(path_edge_types, ("ebom", "routing"))

        adjacency: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
        for edge in edges:
            src = (edge["source_label"], edge["source_id"])
            dst = (edge["target_label"], edge["target_id"])
            adjacency.setdefault(src, []).append((dst[0], dst[1], edge["edge_type"]))

        start = ("Component", from_component_id)
        goal = ("Product", to_product_id)

        queue = deque([(start, [start], [])])
        visited = {start}
        while queue:
            current, path_nodes, path_rels = queue.popleft()
            if current == goal:
                nodes = [{"labels": [label], "id": node_id} for label, node_id in path_nodes]
                return [{"nodes": nodes, "relationships": path_rels}]

            for next_label, next_id, rel in adjacency.get(current, []):
                nxt = (next_label, next_id)
                if nxt in visited:
                    continue
                visited.add(nxt)
                queue.append((nxt, path_nodes + [nxt], path_rels + [rel]))
        return []

    def _all_nodes(self) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for graph_id in DOMAIN_GRAPHS:
            for node in self.domains[graph_id].all_nodes():
                nodes.append(
                    {
                        "id": node["id"],
                        "label": node["label"],
                        "graph_id": node.get("graph_id", graph_id),
                        "properties": node["properties"],
                    }
                )
        return nodes

    def _all_edges(self) -> list[dict[str, Any]]:
        edges: list[dict[str, Any]] = []
        for graph_id in DOMAIN_GRAPHS:
            for edge in self.domains[graph_id].all_edges():
                item = dict(edge)
                item.setdefault("graph_id", graph_id)
                edges.append(item)
        return edges


# Backward-compatible alias for imports that still reference LanceGraphStore.
LanceGraphStore = GraphStore
