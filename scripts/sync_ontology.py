#!/usr/bin/env python3
"""Export ontology and agent skill assets from Python SSOT."""

from __future__ import annotations

import json
from pathlib import Path

from app.validation.contract_loader import assert_contract_matches_registry
from domains.export import (
    export_cypher_engine_profile,
    export_graph_context_bundle,
    export_query_catalog,
)
from ontology.contract.graph_contract import load_graph_contract
from ontology.schema import export_schema_bundle
from ontology.shacl_codegen import export_shacl_ttl

REPO_ROOT = Path(__file__).resolve().parents[1]

ONTOLOGY_OUTPUTS = (
    REPO_ROOT / "ontology" / "assets" / "ontology.json",
    REPO_ROOT / "skills" / "bom-ontology" / "assets" / "ontology.json",
)

SHAPES_OUTPUT = REPO_ROOT / "ontology" / "assets" / "bom-shapes.ttl"

EXPLORER_OUTPUTS: dict[Path, object] = {
    REPO_ROOT
    / "skills"
    / "bom-graph-explorer"
    / "assets"
    / "graph-context.json": export_graph_context_bundle,
    REPO_ROOT
    / "skills"
    / "bom-graph-explorer"
    / "assets"
    / "query-catalog.json": export_query_catalog,
    REPO_ROOT
    / "skills"
    / "bom-graph-explorer"
    / "assets"
    / "cypher-engine-profile.json": export_cypher_engine_profile,
}


def build_ontology_bundle() -> dict:
    bundle = export_schema_bundle()
    bundle["edges"]["allowed_pairs"] = {
        edge: list(pair) for edge, pair in bundle["edges"]["allowed_pairs"].items()
    }
    bundle["meta"] = {
        "format": "bom-ontology-bundle",
        "version": 1,
        "domain": "bom-graph",
        "source": "ontology/schema.py",
        "note": "Generated file. Do not edit by hand; run scripts/sync_ontology.py",
    }
    return bundle


def main() -> None:
    contract = load_graph_contract()
    assert_contract_matches_registry(contract)
    print(f"Graph Contract v{contract.version} OK (schema, registry, federation joins)")

    ontology_text = json.dumps(build_ontology_bundle(), ensure_ascii=False, indent=2) + "\n"
    for output in ONTOLOGY_OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(ontology_text, encoding="utf-8")
        print(f"Wrote {output}")

    SHAPES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shapes_text = export_shacl_ttl()
    SHAPES_OUTPUT.write_text(shapes_text, encoding="utf-8")
    print(f"Wrote {SHAPES_OUTPUT}")

    for output, builder in EXPLORER_OUTPUTS.items():
        output.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(builder(), ensure_ascii=False, indent=2) + "\n"
        output.write_text(text, encoding="utf-8")
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
