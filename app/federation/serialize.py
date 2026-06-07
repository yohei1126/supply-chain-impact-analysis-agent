"""JSON serialization for federation API responses."""

from __future__ import annotations

from typing import Any

from app.federation.analysis import DomainQueryResult, FederatedAnalysis


def domain_query_to_dict(result: DomainQueryResult) -> dict[str, Any]:
    return {
        "graph_id": result.graph_id,
        "query_name": result.query_name,
        "cypher": result.cypher,
        "summary": result.summary,
        "row_count": len(result.rows),
        "rows": result.rows,
    }


def build_domain_query_spec(
    result: DomainQueryResult,
    *,
    supplier_id: str | None = None,
    component_ids: list[str] | None = None,
) -> dict[str, Any]:
    owner_teams = {
        "sourcing": "procurement",
        "ebom": "engineering",
        "routing": "manufacturing",
    }
    params: dict[str, Any] = {}
    if result.graph_id == "sourcing":
        params["supplier_id"] = supplier_id
    else:
        params["component_ids"] = component_ids or []

    return {
        "graph_id": result.graph_id,
        "query_name": result.query_name,
        "owner_team": owner_teams[result.graph_id],
        "engine": "neo4j",
        "language": "Cypher",
        "ontology_source": "ontology/schema.py",
        "query_spec": result.query_name,
        "parameters": params,
        "scope": "single domain Neo4j database",
        "cypher": result.cypher,
    }


def federated_analysis_to_dict(analysis: FederatedAnalysis) -> dict[str, Any]:
    return {
        "scenario": analysis.scenario,
        "supplier_id": analysis.supplier_id,
        "impact_score": analysis.impact_score,
        "domain_queries": [domain_query_to_dict(q) for q in analysis.domain_queries],
        "federated_rows": analysis.federated_rows,
        "problems": [
            {
                "severity": p.severity,
                "category": p.category,
                "message": p.message,
                "evidence": p.evidence,
            }
            for p in analysis.problems
        ],
        "mitigations": [
            {
                "priority": m.priority,
                "action": m.action,
                "owner_team": m.owner_team,
                "evidence": m.evidence,
            }
            for m in analysis.mitigations
        ],
        "join_plan": [
            {
                "step": 1,
                "graph_id": "sourcing",
                "edge": "SUPPLIED_BY",
                "bridge": "component_id",
                "description": "Components supplied by the disrupted supplier",
            },
            {
                "step": 2,
                "graph_id": "ebom",
                "edge": "USED_IN",
                "bridge": "component_id",
                "description": "Finished goods that use those components",
            },
            {
                "step": 3,
                "graph_id": "routing",
                "edge": "INPUT_OF",
                "bridge": "component_id",
                "description": "Manufacturing processes consuming those components",
            },
        ],
        "federation_note": (
            "Each step runs Cypher on its domain Neo4j database; "
            "results are joined in Python on Component.id."
        ),
    }
