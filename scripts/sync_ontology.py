#!/usr/bin/env python3
"""Export ontology from ontology/schema.py into ontology/assets and skills."""

from __future__ import annotations

import json
from pathlib import Path

from ontology.schema import export_schema_bundle

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = (
    REPO_ROOT / "ontology" / "assets" / "ontology.json",
    REPO_ROOT / "skills" / "bom-ontology" / "assets" / "ontology.json",
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
        "source": "ontology/schema.py",
        "note": "Generated file. Do not edit by hand; run scripts/sync_ontology.py",
    }
    return bundle


def main() -> None:
    text = json.dumps(build_bundle(), ensure_ascii=False, indent=2) + "\n"
    for output in OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
