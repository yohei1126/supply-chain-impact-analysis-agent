from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

import lancedb

from domains.registry import (
    DOMAIN_GRAPHS,
    GraphId,
    graph_for_edge,
    graphs_for_node,
)
from app.storage.domain_store import DomainLanceGraphStore
from ontology.schema import RelationEdge, validate_node_payload


class LanceGraphStore:
    """
    Federated graph facade over three domain LanceDB datasets (ebom, routing, sourcing).

    External API matches the original single-graph store; cross-domain traversals
    federate at query time on shared node IDs.
    """

    def __init__(self, lancedb_path: str = "data/lancedb"):
        self.lancedb_path = lancedb_path
        base = Path(lancedb_path)
        self.domains: dict[GraphId, DomainLanceGraphStore] = {
            graph_id: DomainLanceGraphStore(graph_id, str(base / graph_id))
            for graph_id in DOMAIN_GRAPHS
        }

    def domain(self, graph_id: GraphId) -> DomainLanceGraphStore:
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

    def _node_map(self, graph_ids: tuple[GraphId, ...] | None = None) -> dict[tuple[str, str], dict[str, Any]]:
        ids = graph_ids or tuple(DOMAIN_GRAPHS)
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for graph_id in ids:
            for node in self.domains[graph_id].all_nodes():
                merged[(node["label"], node["id"])] = node["properties"]
        return merged

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
        sourcing_edges = self.domains["sourcing"].all_edges()
        ebom_edges = self.domains["ebom"].all_edges()
        node_map = self._node_map(("ebom", "sourcing"))

        supplied_edges = [
            edge
            for edge in sourcing_edges
            if edge["edge_type"] == "SUPPLIED_BY"
            and edge["target_label"] == "Supplier"
            and edge["target_id"] == supplier_id
        ]

        output: list[dict[str, Any]] = []
        for supplied in supplied_edges:
            component_id = supplied["source_id"]
            component = node_map.get(("Component", component_id), {})

            used_in = [
                edge
                for edge in ebom_edges
                if edge["edge_type"] == "USED_IN"
                and edge["source_label"] == "Component"
                and edge["source_id"] == component_id
                and edge["target_label"] == "Product"
            ]
            for used in used_in:
                product = node_map.get(("Product", used["target_id"]), {})
                output.append(
                    {
                        "supplier_id": supplier_id,
                        "component_id": component_id,
                        "component_name": component.get("name"),
                        "product_id": used["target_id"],
                        "product_name": product.get("name"),
                        "component_cost": component.get("cost"),
                    }
                )
        return sorted(output, key=lambda item: item.get("component_cost") or 0, reverse=True)

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

    # Legacy helpers for callers that read raw tables from the unified path.
    @property
    def db(self) -> Any:
        return lancedb.connect(self.lancedb_path)

    @staticmethod
    def _rows(table: Any) -> list[dict[str, Any]]:
        if hasattr(table, "to_arrow"):
            return [dict(r) for r in table.to_arrow().to_pylist()]
        if hasattr(table, "search"):
            return [dict(r) for r in table.search().limit(100000).to_list()]
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
