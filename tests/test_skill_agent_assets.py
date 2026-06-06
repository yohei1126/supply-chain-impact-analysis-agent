"""Generated bom-graph-explorer assets must match live export."""

from __future__ import annotations

import json
from pathlib import Path

from domains.export import (
    export_cypher_engine_profile,
    export_graph_context_bundle,
    export_query_catalog,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPLORER_ASSETS: dict[Path, object] = {
    REPO_ROOT / "skills" / "bom-graph-explorer" / "assets" / "graph-context.json": export_graph_context_bundle,
    REPO_ROOT / "skills" / "bom-graph-explorer" / "assets" / "query-catalog.json": export_query_catalog,
    REPO_ROOT
    / "skills"
    / "bom-graph-explorer"
    / "assets"
    / "cypher-engine-profile.json": export_cypher_engine_profile,
}


def test_explorer_assets_match_live_export() -> None:
    for path, builder in EXPLORER_ASSETS.items():
        assert path.exists(), f"Missing generated asset: {path}"
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        live = builder()
        assert on_disk == live, f"Drift in {path.name}; run uv run python scripts/sync_ontology.py"


def test_query_catalog_covers_all_query_specs() -> None:
    catalog = export_query_catalog()
    queries = catalog["queries"]
    assert "components_by_supplier" in queries
    assert queries["components_by_supplier"]["graph_id"] == "sourcing"
    assert queries["components_by_supplier"]["edge_type"] == "SUPPLIED_BY"
    assert "impact_products_by_components" in queries
    assert "supplier_disruption_impact" in catalog["federation_recipes"]


def test_graph_context_domains_match_registry() -> None:
    bundle = export_graph_context_bundle()
    assert set(bundle["domains"]) == {"sourcing", "ebom", "routing"}
    assert bundle["identity"]["master_entity"] == "Component"
    sourcing_edges = bundle["domains"]["sourcing"]["edges"]
    assert sourcing_edges["SUPPLIED_BY"] == {"from": "Component", "to": "Supplier"}


def test_explorer_skill_loads_generated_assets() -> None:
    from app.agent.skills import load_skill_package

    pkg = load_skill_package(REPO_ROOT, "bom-graph-explorer")
    for name in ("graph-context.json", "query-catalog.json", "cypher-engine-profile.json"):
        assert name in pkg.assets, f"Missing {name} in bom-graph-explorer assets"
