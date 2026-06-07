from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from ontology.schema import ComponentNode


class ComponentMasterStore:
    """Component master in DuckDB with validated graph replication on write."""

    def __init__(
        self,
        graph_store: Any,
        duckdb_path: str = "data/bom.duckdb",
    ):
        self.graph_store = graph_store

        Path("data").mkdir(parents=True, exist_ok=True)
        self.duck = duckdb.connect(duckdb_path)
        self._init_duckdb()

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
        node = ComponentNode(**payload)
        component = node.model_dump()
        component_id = component["id"]

        self.graph_store.add_node("Component", component)

        self.duck.execute(
            """
            INSERT INTO components AS c (id, name, material, cost)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                material = excluded.material,
                cost = excluded.cost
            """,
            [component_id, component["name"], component["material"], component["cost"]],
        )

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

    def search_components(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Deterministic text search over component master (replaces demo vector search)."""
        pattern = f"%{query.strip()}%"
        rows = self.duck.execute(
            """
            SELECT id, name, material, cost
            FROM components
            WHERE name ILIKE ? OR material ILIKE ?
            ORDER BY id
            LIMIT ?
            """,
            [pattern, pattern, limit],
        ).fetchall()
        return [
            {"id": row[0], "name": row[1], "material": row[2], "cost": row[3]} for row in rows
        ]

    def search_components_by_material(self, material: str, *, limit: int = 10) -> list[dict[str, Any]]:
        return self.search_components(material, limit=limit)


# Backward-compatible alias during migration.
UnifiedBomContextStore = ComponentMasterStore
