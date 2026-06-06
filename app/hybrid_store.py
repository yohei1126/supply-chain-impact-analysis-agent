from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import duckdb
import lancedb
import numpy as np

from app.storage.lance_util import lancedb_table_names
from ontology.schema import ComponentNode


def text_to_embedding(text: str, dims: int = 16) -> list[float]:
    """
    Lightweight demo embedding: map text to a fixed-length vector via SHA256
    so runs are reproducible without an external model.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    arr = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
    arr = arr[:dims]
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr.tolist()
    return (arr / norm).tolist()


class UnifiedBomContextStore:
    """Unified access to RDB (DuckDB), vector store (LanceDB), and graph (LanceGraph)."""

    def __init__(
        self,
        graph_store: Any,
        duckdb_path: str = "data/bom.duckdb",
        lancedb_path: str = "data/lancedb",
        vector_table_name: str = "component_vectors",
    ):
        self.graph_store = graph_store

        Path("data").mkdir(parents=True, exist_ok=True)
        self.duck = duckdb.connect(duckdb_path)
        self._init_duckdb()

        self.lance = lancedb.connect(lancedb_path)
        self.vector_table_name = vector_table_name
        if vector_table_name in lancedb_table_names(self.lance):
            self.vector_table = self.lance.open_table(vector_table_name)
        else:
            self.vector_table = self.lance.create_table(
                vector_table_name,
                data=[
                    {
                        "id": "__seed__",
                        "name": "seed",
                        "material": "seed",
                        "text": "seed",
                        "vector": text_to_embedding("seed"),
                    }
                ],
            )
            self.vector_table.delete("id = '__seed__'")

    def close(self) -> None:
        self.duck.close()

    def _init_duckdb(self) -> None:
        self.duck.execute(
            """
            CREATE TABLE IF NOT EXISTS components (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                material VARCHAR NOT NULL,
                cost DOUBLE NOT NULL
            )
            """
        )

    def upsert_component(self, payload: dict[str, Any]) -> None:
        # SSOT validation (schema.py)
        node = ComponentNode(**payload)
        component = node.model_dump()
        component_id = component["id"]

        # GraphDB
        self.graph_store.add_node("Component", component)

        # RDB
        self.duck.execute(
            """
            INSERT INTO components AS c (id, name, material, cost)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                material = excluded.material,
                cost = excluded.cost
            """,
            [component["id"], component["name"], component["material"], component["cost"]],
        )

        # VectorDB
        text = f"{component['name']} material:{component['material']} cost:{component['cost']}"
        vector = text_to_embedding(text)
        self.vector_table.delete(f"id = '{component_id}'")
        self.vector_table.add(
            [
                {
                    "id": component["id"],
                    "name": component["name"],
                    "material": component["material"],
                    "text": text,
                    "vector": vector,
                }
            ]
        )

    def vector_search_components(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        query_vec = text_to_embedding(query)
        rows = self.vector_table.search(query_vec).limit(top_k).to_list()
        return [dict(r) for r in rows]

    def get_component_from_rdb(self, component_id: str) -> dict[str, Any] | None:
        row = self.duck.execute(
            "SELECT id, name, material, cost FROM components WHERE id = ?",
            [component_id],
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "material": row[2],
            "cost": row[3],
        }

    def find_supplier_impact_for_query(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        Hybrid flow:
        1) LanceDB — similar component candidates (vector search)
        2) DuckDB — enrich with component attributes
        3) Graph — supplier / product impact traversal
        """
        similar = self.vector_search_components(query, top_k=top_k)
        output: list[dict[str, Any]] = []

        for item in similar:
            component_id = item["id"]
            detail = self.get_component_from_rdb(component_id)
            if not detail:
                continue

            impacts = self.graph_store.impacted_products_by_supplier("SUP-001")
            impacts = [x for x in impacts if x.get("component_id") == component_id]
            output.append(
                {
                    "query_component": component_id,
                    "vector_hit": item,
                    "rdb_detail": detail,
                    "graph_impacts": impacts,
                }
            )
        return output
