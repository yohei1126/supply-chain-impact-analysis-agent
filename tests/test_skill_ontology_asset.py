import json
from pathlib import Path

from bom_graph.schema import export_schema_bundle

ONTOLOGY_JSON = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "bom-ontology"
    / "assets"
    / "ontology.json"
)


def _json_safe_allowed_pairs() -> dict[str, list[str]]:
    live = export_schema_bundle()
    return {edge: list(pair) for edge, pair in live["edges"]["allowed_pairs"].items()}


def test_single_ontology_artifact_matches_schema_export() -> None:
    on_disk = json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))
    live = export_schema_bundle()

    assert on_disk["nodes"] == live["nodes"]
    assert on_disk["edges"]["RelationEdge"] == live["edges"]["RelationEdge"]
    assert on_disk["edges"]["allowed_pairs"] == _json_safe_allowed_pairs()
