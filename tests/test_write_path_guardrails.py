"""Guardrails: Neo4j graph mutations stay on validated storage write paths."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"

# Only these modules may issue graph write Cypher (CREATE/MERGE/DELETE/DETACH/SET).
ALLOWED_NEO4J_WRITE_MODULES = frozenset(
    {
        "app/storage/neo4j_domain_store.py",
        "app/storage/neo4j_config.py",
    }
)

# Modules that call session.run but only for read-only probes (with runtime write guards).
READ_ONLY_NEO4J_SESSION_MODULES = frozenset(
    {
        "app/federation/cypher_executor.py",
        "app/validation/neo4j_l3_audit.py",
    }
)

WRITE_CYPHER = re.compile(r"\b(CREATE|MERGE|DELETE|DETACH)\b", re.IGNORECASE)


def _iter_app_python_files() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def find_unauthorized_neo4j_write_modules() -> list[str]:
    offenders: list[str] = []
    for path in _iter_app_python_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWED_NEO4J_WRITE_MODULES or rel in READ_ONLY_NEO4J_SESSION_MODULES:
            continue
        text = path.read_text(encoding="utf-8")
        if "session.run" in text and WRITE_CYPHER.search(text):
            offenders.append(rel)
    return offenders


def test_neo4j_writes_only_in_storage_layer() -> None:
    offenders = find_unauthorized_neo4j_write_modules()
    assert not offenders, (
        "Neo4j write Cypher must go through app/storage/neo4j_domain_store.py "
        "(GraphStore.add_node/add_edge). Offenders:\n" + "\n".join(f"  {p}" for p in offenders)
    )
