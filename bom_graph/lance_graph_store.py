from __future__ import annotations

from collections import deque
import json
from typing import Any

import lancedb

from bom_graph.schema import RelationEdge, validate_node_payload


def lancedb_table_names(db: Any) -> list[str]:
    """Normalize LanceDB list_tables() across client versions."""
    names = db.list_tables()
    if isinstance(names, list):
        return names
    tables = getattr(names, "tables", None)
    if tables is not None:
        return list(tables)
    return list(names)


class LanceGraphStore:
    """
    Lightweight graph store: keeps nodes/edges tables on LanceDB and runs traversals in-process.
    """

    def __init__(self, lancedb_path: str = "data/lancedb"):
        self.db = lancedb.connect(lancedb_path)

        if "graph_nodes" in lancedb_table_names(self.db):
            self.nodes = self.db.open_table("graph_nodes")
        else:
            self.nodes = self.db.create_table(
                "graph_nodes",
                data=[{"id": "__seed__", "label": "Seed", "properties_json": "{}"}],
            )
            self.nodes.delete("id = '__seed__'")

        if "graph_edges" in lancedb_table_names(self.db):
            self.edges = self.db.open_table("graph_edges")
        else:
            self.edges = self.db.create_table(
                "graph_edges",
                data=[
                    {
                        "source_id": "__seed__",
                        "source_label": "Seed",
                        "target_id": "__seed__",
                        "target_label": "Seed",
                        "edge_type": "SEED",
                        "properties_json": "{}",
                    }
                ],
            )
            self.edges.delete("source_id = '__seed__'")

    @staticmethod
    def _rows(table: Any) -> list[dict[str, Any]]:
        if hasattr(table, "to_arrow"):
            return [dict(r) for r in table.to_arrow().to_pylist()]
        # Fallback for older/newer client differences
        if hasattr(table, "search"):
            return [dict(r) for r in table.search().limit(100000).to_list()]
        return []

    def _all_nodes(self) -> list[dict[str, Any]]:
        rows = self._rows(self.nodes)
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "label": r["label"],
                    "properties": json.loads(r.get("properties_json", "{}")),
                }
            )
        return out

    def _all_edges(self) -> list[dict[str, Any]]:
        rows = self._rows(self.edges)
        out: list[dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            item["properties"] = json.loads(item.get("properties_json", "{}"))
            out.append(item)
        return out

    def add_node(self, node_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        node = validate_node_payload(node_type, payload)
        row = node.model_dump()
        label = row.pop("label")

        self.nodes.delete(f"id = '{row['id']}'")
        self.nodes.add(
            [{"id": row["id"], "label": label, "properties_json": json.dumps(row, ensure_ascii=False)}]
        )
        return {"labels": [label], "node": row}

    def add_edge(self, payload: dict[str, Any]) -> dict[str, Any]:
        edge = RelationEdge(**payload)
        row = edge.model_dump()

        node_index = {(n["label"], n["id"]) for n in self._all_nodes()}
        if (row["source_label"], row["source_id"]) not in node_index:
            raise ValueError(f"source node does not exist: {row['source_label']}:{row['source_id']}")
        if (row["target_label"], row["target_id"]) not in node_index:
            raise ValueError(f"target node does not exist: {row['target_label']}:{row['target_id']}")

        delete_expr = (
            f"source_id = '{row['source_id']}' "
            f"AND source_label = '{row['source_label']}' "
            f"AND target_id = '{row['target_id']}' "
            f"AND target_label = '{row['target_label']}' "
            f"AND edge_type = '{row['edge_type']}'"
        )
        self.edges.delete(delete_expr)
        row_to_write = dict(row)
        row_to_write["properties_json"] = json.dumps(row["properties"], ensure_ascii=False)
        del row_to_write["properties"]
        self.edges.add([row_to_write])
        return {"edge_type": row["edge_type"], "edge": row}

    def impacted_products_by_supplier(self, supplier_id: str) -> list[dict[str, Any]]:
        nodes = self._all_nodes()
        edges = self._all_edges()
        node_map = {(n["label"], n["id"]): n["properties"] for n in nodes}

        supplied_edges = [
            e
            for e in edges
            if e["edge_type"] == "SUPPLIED_BY" and e["target_label"] == "Supplier" and e["target_id"] == supplier_id
        ]

        output: list[dict[str, Any]] = []
        for se in supplied_edges:
            component_id = se["source_id"]
            component = node_map.get(("Component", component_id), {})

            used_in = [
                e
                for e in edges
                if e["edge_type"] == "USED_IN"
                and e["source_label"] == "Component"
                and e["source_id"] == component_id
                and e["target_label"] == "Product"
            ]
            for ue in used_in:
                product = node_map.get(("Product", ue["target_id"]), {})
                output.append(
                    {
                        "supplier_id": supplier_id,
                        "component_id": component_id,
                        "component_name": component.get("name"),
                        "product_id": ue["target_id"],
                        "product_name": product.get("name"),
                        "component_cost": component.get("cost"),
                    }
                )
        return sorted(output, key=lambda x: x.get("component_cost") or 0, reverse=True)

    def shortest_supply_path(self, from_component_id: str, to_product_id: str) -> list[dict[str, Any]]:
        edges = self._all_edges()
        adjacency: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
        for e in edges:
            if e["edge_type"] not in {"USED_IN", "INPUT_OF", "PRODUCED_BY"}:
                continue
            src = (e["source_label"], e["source_id"])
            dst = (e["target_label"], e["target_id"])
            adjacency.setdefault(src, []).append((dst[0], dst[1], e["edge_type"]))

        start = ("Component", from_component_id)
        goal = ("Product", to_product_id)

        queue = deque([(start, [start], [])])
        visited = {start}
        while queue:
            current, path_nodes, path_rels = queue.popleft()
            if current == goal:
                nodes = [{"labels": [lbl], "id": node_id} for lbl, node_id in path_nodes]
                return [{"nodes": nodes, "relationships": path_rels}]

            for next_lbl, next_id, rel in adjacency.get(current, []):
                nxt = (next_lbl, next_id)
                if nxt in visited:
                    continue
                visited.add(nxt)
                queue.append((nxt, path_nodes + [nxt], path_rels + [rel]))
        return []
