from __future__ import annotations

import json
from typing import Any

import lancedb

from domains.registry import GraphId, assert_edge_allowed_in_graph, assert_node_allowed_in_graph
from app.storage.lance_util import lancedb_table_names
from ontology.schema import RelationEdge, validate_node_payload


class DomainLanceGraphStore:
    """Single-domain graph store backed by one LanceDB dataset."""

    def __init__(self, graph_id: GraphId, lancedb_path: str):
        self.graph_id = graph_id
        self.lancedb_path = lancedb_path
        self.db = lancedb.connect(lancedb_path)

        if "graph_nodes" in lancedb_table_names(self.db):
            self.nodes = self.db.open_table("graph_nodes")
        else:
            self.nodes = self.db.create_table(
                "graph_nodes",
                data=[
                    {
                        "graph_id": graph_id,
                        "id": "__seed__",
                        "label": "Seed",
                        "properties_json": "{}",
                    }
                ],
            )
            self.nodes.delete("id = '__seed__'")

        if "graph_edges" in lancedb_table_names(self.db):
            self.edges = self.db.open_table("graph_edges")
        else:
            self.edges = self.db.create_table(
                "graph_edges",
                data=[
                    {
                        "graph_id": graph_id,
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
        if hasattr(table, "search"):
            return [dict(r) for r in table.search().limit(100000).to_list()]
        return []

    def all_nodes(self) -> list[dict[str, Any]]:
        rows = self._rows(self.nodes)
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "graph_id": row.get("graph_id", self.graph_id),
                    "id": row["id"],
                    "label": row["label"],
                    "properties": json.loads(row.get("properties_json", "{}")),
                }
            )
        return out

    def all_edges(self) -> list[dict[str, Any]]:
        rows = self._rows(self.edges)
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["properties"] = json.loads(item.pop("properties_json", "{}"))
            item.setdefault("graph_id", self.graph_id)
            out.append(item)
        return out

    def add_node(self, node_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert_node_allowed_in_graph(self.graph_id, node_type)  # type: ignore[arg-type]
        node = validate_node_payload(node_type, payload)
        row = node.model_dump()
        label = row.pop("label")

        self.nodes.delete(f"id = '{row['id']}'")
        self.nodes.add(
            [
                {
                    "graph_id": self.graph_id,
                    "id": row["id"],
                    "label": label,
                    "properties_json": json.dumps(row, ensure_ascii=False),
                }
            ]
        )
        return {"graph_id": self.graph_id, "labels": [label], "node": row}

    def add_edge(self, payload: dict[str, Any]) -> dict[str, Any]:
        edge = RelationEdge(**payload)
        row = edge.model_dump()
        assert_edge_allowed_in_graph(self.graph_id, row["edge_type"])

        node_index = {(n["label"], n["id"]) for n in self.all_nodes()}
        if (row["source_label"], row["source_id"]) not in node_index:
            raise ValueError(
                f"source node does not exist in {self.graph_id}: "
                f"{row['source_label']}:{row['source_id']}"
            )
        if (row["target_label"], row["target_id"]) not in node_index:
            raise ValueError(
                f"target node does not exist in {self.graph_id}: "
                f"{row['target_label']}:{row['target_id']}"
            )

        delete_expr = (
            f"source_id = '{row['source_id']}' "
            f"AND source_label = '{row['source_label']}' "
            f"AND target_id = '{row['target_id']}' "
            f"AND target_label = '{row['target_label']}' "
            f"AND edge_type = '{row['edge_type']}'"
        )
        self.edges.delete(delete_expr)
        row_to_write = dict(row)
        row_to_write["graph_id"] = self.graph_id
        row_to_write["properties_json"] = json.dumps(row["properties"], ensure_ascii=False)
        del row_to_write["properties"]
        self.edges.add([row_to_write])
        return {"graph_id": self.graph_id, "edge_type": row["edge_type"], "edge": row}
