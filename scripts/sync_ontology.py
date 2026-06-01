#!/usr/bin/env python3
"""Export ontology from bom_graph.schema into skills/bom-ontology/assets/ontology.json."""

from __future__ import annotations

import json
from pathlib import Path

from bom_graph.schema import export_schema_bundle

OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "bom-ontology"
    / "assets"
    / "ontology.json"
)


def build_bundle() -> dict:
    bundle = export_schema_bundle()
    bundle["edges"]["allowed_pairs"] = {
        edge: list(pair) for edge, pair in bundle["edges"]["allowed_pairs"].items()
    }
    bundle["meta"] = {
        "format": "bom-ontology-bundle",
        "version": 1,
        "domain": "bom-graph",
        "source": "bom_graph/schema.py",
        "note": "Generated file. Do not edit by hand; run scripts/sync_ontology.py",
    }
    return bundle


def main() -> None:
    text = json.dumps(build_bundle(), ensure_ascii=False, indent=2) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
