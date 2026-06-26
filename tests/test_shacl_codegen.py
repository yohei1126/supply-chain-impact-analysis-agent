"""SHACL asset generation from ontology/schema.py."""

from __future__ import annotations

from pathlib import Path

from ontology.shacl_codegen import BOM_NS, export_shacl_ttl

SHAPES_PATH = Path(__file__).resolve().parents[1] / "ontology" / "assets" / "bom-shapes.ttl"


def test_shacl_ttl_contains_all_node_shapes() -> None:
    ttl = export_shacl_ttl()
    for label in ("Component", "Process", "Supplier", "Product"):
        assert f"bom:{label}Shape a sh:NodeShape" in ttl
        assert f"sh:targetClass bom:{label}" in ttl


def test_shacl_ttl_includes_edge_constraints() -> None:
    ttl = export_shacl_ttl()
    assert "sh:path bom:USED_IN" in ttl
    assert "sh:class bom:Product" in ttl
    assert "sh:path bom:SUPPLIED_BY" in ttl
    assert "sh:path bom:PRODUCED_BY" in ttl


def test_shacl_ttl_includes_storage_metadata() -> None:
    ttl = export_shacl_ttl()
    for prop in ("graph_id", "as_of", "graph_contract_version"):
        assert f"sh:path bom:{prop}" in ttl


def test_bom_shapes_asset_matches_live_export() -> None:
    on_disk = SHAPES_PATH.read_text(encoding="utf-8")
    assert on_disk == export_shacl_ttl()


def test_bom_namespace_is_stable() -> None:
    assert BOM_NS == "neo4j://graph.schema#"
