"""JSON serialization for federation API responses."""

from __future__ import annotations

from typing import Any

from app.federation.analysis import DomainQueryResult, FederatedAnalysis


def domain_query_to_dict(result: DomainQueryResult) -> dict[str, Any]:
    return {
        "graph_id": result.graph_id,
        "query_name": result.query_name,
        "summary": result.summary,
        "row_count": len(result.rows),
        "rows": result.rows,
    }


_DOMAIN_QUERY_META: dict[str, dict[str, str]] = {
    "sourcing": {
        "owner_team": "procurement",
        "edge": "SUPPLIED_BY",
        "edge_pattern": "Component —SUPPLIED_BY→ Supplier",
        "filter": "Supplier.id = {supplier_id}",
        "function": "query_sourcing_for_supplier",
    },
    "ebom": {
        "owner_team": "engineering",
        "edge": "USED_IN",
        "edge_pattern": "Component —USED_IN→ Product",
        "filter": "Component.id IN ({component_ids})",
        "function": "query_ebom_for_components",
    },
    "routing": {
        "owner_team": "manufacturing",
        "edge": "INPUT_OF",
        "edge_pattern": "Component —INPUT_OF→ Process",
        "filter": "Component.id IN ({component_ids})",
        "function": "query_routing_for_components",
    },
}


def build_domain_query_spec(
    graph_id: str,
    *,
    supplier_id: str | None = None,
    component_ids: list[str] | None = None,
    query_name: str | None = None,
) -> dict[str, Any]:
    meta = _DOMAIN_QUERY_META[graph_id]
    params: dict[str, Any] = {}
    if graph_id == "sourcing":
        params["supplier_id"] = supplier_id
        filter_text = meta["filter"].format(supplier_id=supplier_id)
    else:
        ids = component_ids or []
        params["component_ids"] = ids
        filter_text = meta["filter"].format(component_ids=", ".join(ids))

    return {
        "graph_id": graph_id,
        "query_name": query_name,
        "owner_team": meta["owner_team"],
        "edge": meta["edge"],
        "edge_pattern": meta["edge_pattern"],
        "filter": filter_text,
        "function": meta["function"],
        "parameters": params,
        "scope": "single domain graph — Python scan of LanceDB tables, no Cypher",
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
    }
