from __future__ import annotations

from typing import Any

from app.storage.neo4j_config import DEFAULT_DATABASE
from domains.registry import GraphId, assert_edge_allowed_in_graph, assert_node_allowed_in_graph
from ontology.schema import RelationEdge, validate_node_payload

try:
    from neo4j import Driver
except ImportError:  # pragma: no cover
    Driver = Any  # type: ignore[misc, assignment]


class Neo4jDomainStore:
    """Single-domain graph store using graph_id property within the default Neo4j database."""

    def __init__(self, graph_id: GraphId, driver: Driver):
        self.graph_id = graph_id
        self.driver = driver
        self.database = DEFAULT_DATABASE

    def all_nodes(self) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (n {graph_id: $graph_id}) "
                "RETURN labels(n) AS labels, properties(n) AS props",
                graph_id=self.graph_id,
            )
            out: list[dict[str, Any]] = []
            for record in result:
                labels = list(record["labels"])
                props = dict(record["props"])
                label = labels[0] if labels else "Unknown"
                out.append(
                    {
                        "graph_id": self.graph_id,
                        "id": props.get("id", ""),
                        "label": label,
                        "properties": props,
                    }
                )
            return out

    def all_edges(self) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (s {graph_id: $graph_id})-[r]->(t {graph_id: $graph_id})
                RETURN
                  labels(s)[0] AS source_label,
                  s.id AS source_id,
                  labels(t)[0] AS target_label,
                  t.id AS target_id,
                  type(r) AS edge_type,
                  properties(r) AS properties
                """,
                graph_id=self.graph_id,
            )
            out: list[dict[str, Any]] = []
            for record in result:
                out.append(
                    {
                        "graph_id": self.graph_id,
                        "source_label": record["source_label"],
                        "source_id": record["source_id"],
                        "target_label": record["target_label"],
                        "target_id": record["target_id"],
                        "edge_type": record["edge_type"],
                        "properties": dict(record["properties"] or {}),
                    }
                )
            return out

    def add_node(self, node_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert_node_allowed_in_graph(self.graph_id, node_type)  # type: ignore[arg-type]
        node = validate_node_payload(node_type, payload)
        row = node.model_dump()
        label = row.pop("label")
        node_id = row["id"]
        row["graph_id"] = self.graph_id

        with self.driver.session(database=self.database) as session:
            session.run(
                f"MERGE (n:{label} {{id: $id, graph_id: $graph_id}}) SET n += $props",
                id=node_id,
                graph_id=self.graph_id,
                props=row,
            )
        return {"graph_id": self.graph_id, "labels": [label], "node": {**row, "id": node_id}}

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

        rel_props = row.get("properties") or {}
        with self.driver.session(database=self.database) as session:
            session.run(
                f"""
                MATCH (s:{row["source_label"]} {{id: $source_id, graph_id: $graph_id}})
                MATCH (t:{row["target_label"]} {{id: $target_id, graph_id: $graph_id}})
                MERGE (s)-[r:{row["edge_type"]}]->(t)
                SET r = $props
                """,
                source_id=row["source_id"],
                target_id=row["target_id"],
                graph_id=self.graph_id,
                props=rel_props,
            )
        return {"graph_id": self.graph_id, "edge_type": row["edge_type"], "edge": row}
