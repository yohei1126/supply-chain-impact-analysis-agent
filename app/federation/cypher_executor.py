"""Execute Cypher queries against domain Neo4j databases."""

from __future__ import annotations

import re
from typing import Any

from app.storage.neo4j_domain_store import Neo4jDomainStore
from domains.registry import GraphId

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _validate_id(value: str) -> str:
    if not _ID_PATTERN.match(value):
        raise ValueError(f"Invalid graph id: {value!r}")
    return value


def cypher_string_list(ids: set[str] | list[str]) -> str:
    return ", ".join(f"'{_validate_id(item)}'" for item in sorted(set(ids)))


def execute_domain_cypher(
    domain: Neo4jDomainStore,
    graph_id: GraphId,
    cypher: str,
    *,
    parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    params = dict(parameters or {})
    params.setdefault("graph_id", graph_id)
    with domain.driver.session(database=domain.database) as session:
        result = session.run(cypher, params)
        return [record.data() for record in result]


def pydict_to_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    if not result:
        return []
    keys = list(result.keys())
    if not keys:
        return []
    length = len(result[keys[0]])
    return [{key: result[key][index] for key in keys} for index in range(length)]
