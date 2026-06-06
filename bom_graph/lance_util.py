from __future__ import annotations

from typing import Any


def lancedb_table_names(db: Any) -> list[str]:
    """Normalize LanceDB list_tables() across client versions."""
    names = db.list_tables()
    if isinstance(names, list):
        return names
    tables = getattr(names, "tables", None)
    if tables is not None:
        return list(tables)
    return list(names)
