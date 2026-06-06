"""Ontology JSON artifacts must match live export from ontology/schema.py."""

from __future__ import annotations

import json
from pathlib import Path

from ontology.schema import export_schema_bundle

ONTOLOGY_PATHS = (
    Path(__file__).resolve().parents[1] / "ontology" / "assets" / "ontology.json",
    Path(__file__).resolve().parents[1] / "skills" / "bom-ontology" / "assets" / "ontology.json",
)


def _json_safe_allowed_pairs() -> dict[str, list[str]]:
    live = export_schema_bundle()
    return {edge: list(pair) for edge, pair in live["edges"]["allowed_pairs"].items()}


def test_single_ontology_artifact_matches_schema_export() -> None:
    for path in ONTOLOGY_PATHS:
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        live = export_schema_bundle()

        assert on_disk["nodes"] == live["nodes"]
        assert on_disk["edges"]["RelationEdge"] == live["edges"]["RelationEdge"]
        assert on_disk["edges"]["allowed_pairs"] == _json_safe_allowed_pairs()
