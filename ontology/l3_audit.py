"""L3 post-load audit check definitions (Cypher only; no Neo4j driver)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ontology.schema import ALLOWED_EDGES, EdgeType, NodeLabel

NODE_LABELS: tuple[NodeLabel, ...] = ("Component", "Process", "Supplier", "Product")
EDGE_TYPES: tuple[EdgeType, ...] = tuple(ALLOWED_EDGES.keys())


@dataclass(frozen=True)
class L3Check:
    """One conformance probe. Cypher must RETURN rows for each violation (empty = pass)."""

    check_id: str
    description: str
    cypher: str
    parameters: dict[str, Any] | None = None


def _edge_pair_predicate() -> str:
    """Cypher boolean expression: true when (s,r,t) matches ontology edge semantics."""
    clauses: list[str] = []
    for edge_type, (source_label, target_label) in ALLOWED_EDGES.items():
        clauses.append(
            f"(edge_type = '{edge_type}' "
            f"AND labels(s)[0] = '{source_label}' "
            f"AND labels(t)[0] = '{target_label}')"
        )
    return " OR ".join(clauses)


def ontology_l3_checks() -> list[L3Check]:
    """Global ontology checks independent of per-domain registry."""
    edge_predicate = _edge_pair_predicate()
    return [
        L3Check(
            check_id="unknown_node_label",
            description="Node label is not in the ontology vocabulary",
            cypher=(
                "MATCH (n) "
                "WHERE n.graph_id IS NOT NULL "
                "AND NOT labels(n)[0] IN $allowed_labels "
                "RETURN labels(n)[0] AS label, n.id AS id, n.graph_id AS graph_id "
                "LIMIT $sample_limit"
            ),
            parameters={"allowed_labels": list(NODE_LABELS), "sample_limit": 50},
        ),
        L3Check(
            check_id="missing_node_id",
            description="Node with graph_id is missing a non-empty id property",
            cypher=(
                "MATCH (n) "
                "WHERE n.graph_id IS NOT NULL "
                "AND (n.id IS NULL OR n.id = '') "
                "RETURN labels(n)[0] AS label, n.graph_id AS graph_id "
                "LIMIT $sample_limit"
            ),
            parameters={"sample_limit": 50},
        ),
        L3Check(
            check_id="duplicate_node_key",
            description="Duplicate (label, id, graph_id) node keys",
            cypher=(
                "MATCH (n) "
                "WHERE n.graph_id IS NOT NULL AND n.id IS NOT NULL AND n.id <> '' "
                "WITH labels(n)[0] AS label, n.id AS id, n.graph_id AS graph_id, count(*) AS c "
                "WHERE c > 1 "
                "RETURN label, id, graph_id, c "
                "LIMIT $sample_limit"
            ),
            parameters={"sample_limit": 50},
        ),
        L3Check(
            check_id="unknown_edge_type",
            description="Relationship type is not in the ontology edge vocabulary",
            cypher=(
                "MATCH (s)-[r]->(t) "
                "WHERE s.graph_id IS NOT NULL AND t.graph_id = s.graph_id "
                "AND NOT type(r) IN $allowed_edge_types "
                "RETURN type(r) AS edge_type, labels(s)[0] AS source_label, s.id AS source_id, "
                "labels(t)[0] AS target_label, t.id AS target_id, s.graph_id AS graph_id "
                "LIMIT $sample_limit"
            ),
            parameters={"allowed_edge_types": list(EDGE_TYPES), "sample_limit": 50},
        ),
        L3Check(
            check_id="invalid_edge_endpoints",
            description="Edge endpoints do not match ALLOWED_EDGES for the relationship type",
            cypher=(
                "MATCH (s)-[r]->(t) "
                "WHERE s.graph_id IS NOT NULL AND t.graph_id = s.graph_id "
                "AND type(r) IN $allowed_edge_types "
                "WITH s, t, type(r) AS edge_type "
                f"WHERE NOT ({edge_predicate}) "
                "RETURN edge_type, labels(s)[0] AS source_label, s.id AS source_id, "
                "labels(t)[0] AS target_label, t.id AS target_id, s.graph_id AS graph_id "
                "LIMIT $sample_limit"
            ),
            parameters={"allowed_edge_types": list(EDGE_TYPES), "sample_limit": 50},
        ),
        L3Check(
            check_id="cross_graph_edge",
            description="Relationship connects nodes with different graph_id values",
            cypher=(
                "MATCH (s)-[r]->(t) "
                "WHERE s.graph_id IS NOT NULL AND t.graph_id IS NOT NULL "
                "AND s.graph_id <> t.graph_id "
                "RETURN type(r) AS edge_type, s.graph_id AS source_graph_id, "
                "t.graph_id AS target_graph_id, s.id AS source_id, t.id AS target_id "
                "LIMIT $sample_limit"
            ),
            parameters={"sample_limit": 50},
        ),
    ]


def domain_l3_checks(
    graph_id: str,
    allowed_nodes: set[str],
    allowed_edges: set[str],
) -> list[L3Check]:
    """Per-graph_id registry checks (domain partition)."""
    return [
        L3Check(
            check_id=f"domain_node_{graph_id}",
            description=f"Node label not allowed in graph {graph_id}",
            cypher=(
                "MATCH (n {graph_id: $graph_id}) "
                "WHERE NOT labels(n)[0] IN $allowed_nodes "
                "RETURN labels(n)[0] AS label, n.id AS id "
                "LIMIT $sample_limit"
            ),
            parameters={
                "graph_id": graph_id,
                "allowed_nodes": sorted(allowed_nodes),
                "sample_limit": 50,
            },
        ),
        L3Check(
            check_id=f"domain_edge_{graph_id}",
            description=f"Edge type not allowed in graph {graph_id}",
            cypher=(
                "MATCH (s {graph_id: $graph_id})-[r]->(t {graph_id: $graph_id}) "
                "WHERE NOT type(r) IN $allowed_edges "
                "RETURN type(r) AS edge_type, labels(s)[0] AS source_label, s.id AS source_id, "
                "labels(t)[0] AS target_label, t.id AS target_id "
                "LIMIT $sample_limit"
            ),
            parameters={
                "graph_id": graph_id,
                "allowed_edges": sorted(allowed_edges),
                "sample_limit": 50,
            },
        ),
    ]


def all_l3_checks(domain_graphs: Mapping[str, Mapping[str, set[str]]]) -> list[L3Check]:
    checks = list(ontology_l3_checks())
    for graph_id, spec in domain_graphs.items():
        checks.extend(
            domain_l3_checks(
                graph_id,
                allowed_nodes=set(spec["nodes"]),
                allowed_edges=set(spec["edges"]),
            )
        )
    return checks


__all__ = [
    "L3Check",
    "all_l3_checks",
    "domain_l3_checks",
    "ontology_l3_checks",
]
