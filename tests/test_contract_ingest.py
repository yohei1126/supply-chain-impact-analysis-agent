"""Tests for Graph Contract quality.on_ingest hooks."""

from __future__ import annotations

from app.federation.graph_store import GraphStore
from app.validation.contract_ingest import run_on_ingest_quality_gates
from pipeline.demo.load_domains import load_all_domains_separately


def test_on_ingest_quality_passes_after_full_load(
    graph_store: GraphStore,
    tmp_path,
) -> None:
    load_all_domains_separately(graph_store)
    duckdb = tmp_path / "bom.duckdb"
    from app.component_master_store import ComponentMasterStore

    master = ComponentMasterStore(graph_store=graph_store, duckdb_path=str(duckdb))
    try:
        for node in graph_store._all_nodes():
            if node["label"] != "Component":
                continue
            props = {
                key: node["properties"][key]
                for key in ("id", "name", "material", "cost")
                if key in node["properties"]
            }
            master.upsert_component(props)
    finally:
        master.close()

    report = run_on_ingest_quality_gates(graph_store.driver, duckdb_path=duckdb)
    assert report.passed, report.violations
