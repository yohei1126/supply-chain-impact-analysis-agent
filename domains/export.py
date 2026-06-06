"""Export graph-context and query-catalog bundles for Agent Skills (generated JSON)."""

from __future__ import annotations

from typing import Any

from domains.registry import DOMAIN_GRAPHS, EDGE_TO_GRAPH
from ontology.cypher_builder import QUERY_SPECS, export_query_spec_entry
from ontology.schema import ALLOWED_EDGES

FEDERATION_RECIPES: dict[str, dict[str, Any]] = {
    "supplier_disruption_impact": {
        "description": "Components supplied by a disrupted supplier to affected finished goods.",
        "steps": ["components_by_supplier", "impact_products_by_components"],
        "bridge": "component_id",
    },
    "supplier_disruption_with_routing": {
        "description": "Supplier impact extended with manufacturing processes consuming affected components.",
        "steps": [
            "components_by_supplier",
            "impact_products_by_components",
            "processes_by_components",
        ],
        "bridge": "component_id",
    },
}

CYPHER_ENGINE_PROFILE: dict[str, Any] = {
    "engine": "lance-graph",
    "dialect_notes": [
        "Cypher subset only — not full Neo4j.",
        "No shortestPath(); use direct edge match or multi-hop outside Cypher.",
        "List parameters such as IN $ids may be unsupported; embed component id literals when required.",
        "One domain graph per execute call (sourcing, ebom, or routing).",
    ],
    "composition_rules": [
        "Every MATCH edge type must appear in ontology.json edges.allowed_pairs with correct direction.",
        "Restrict edges to the target graph_id listed in graph-context.json domains.",
        "Join federated steps in application logic on identity.bridges (Component.id).",
        "Prefer named queries from query-catalog.json before inventing ad-hoc patterns.",
    ],
}


def export_graph_context_bundle() -> dict[str, Any]:
    domains: dict[str, Any] = {}
    for graph_id, spec in DOMAIN_GRAPHS.items():
        edges: dict[str, dict[str, str]] = {}
        for edge_type in sorted(spec["edges"]):
            source_label, target_label = ALLOWED_EDGES[edge_type]  # type: ignore[index]
            edges[edge_type] = {"from": source_label, "to": target_label}
        domains[graph_id] = {
            "graph_id": graph_id,
            "nodes": sorted(spec["nodes"]),
            "edges": edges,
        }

    return {
        "identity": {
            "master_entity": "Component",
            "master_key": "id",
            "bridges": [
                {
                    "entity": "Component",
                    "key": "id",
                    "graphs": ["ebom", "routing", "sourcing"],
                    "rule": "same_id_same_real_world_part",
                },
                {
                    "entity": "Product",
                    "key": "id",
                    "graphs": ["ebom", "routing"],
                    "rule": "same_id_same_finished_good",
                },
            ],
        },
        "domains": domains,
        "federation": {
            "joins": [
                {
                    "name": name,
                    **recipe,
                }
                for name, recipe in FEDERATION_RECIPES.items()
            ],
        },
        "meta": {
            "format": "bom-graph-context-bundle",
            "version": 1,
            "source": "domains/registry.py + ontology/schema.py",
            "contract": "ontology/contract/graph_context.yaml",
            "note": "Generated file. Do not edit by hand; run scripts/sync_ontology.py",
        },
    }


def export_query_catalog() -> dict[str, Any]:
    queries: dict[str, Any] = {}
    for name, spec in QUERY_SPECS.items():
        entry = export_query_spec_entry(spec)
        entry["graph_id"] = EDGE_TO_GRAPH[spec.edge_type]
        queries[name] = entry

    return {
        "queries": queries,
        "federation_recipes": FEDERATION_RECIPES,
        "meta": {
            "format": "bom-query-catalog",
            "version": 1,
            "source": "ontology/cypher_builder.py + domains/registry.py",
            "note": "Generated file. Do not edit by hand; run scripts/sync_ontology.py",
        },
    }


def export_cypher_engine_profile() -> dict[str, Any]:
    return {
        **CYPHER_ENGINE_PROFILE,
        "meta": {
            "format": "bom-cypher-engine-profile",
            "version": 1,
            "source": "domains/export.py",
            "note": "Engine dialect constraints for LLM Cypher composition; update domains/export.py",
        },
    }
