"""Tests for federation REST endpoints used by the web UI."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent import server
from app.federation.graph_store import GraphStore
from pipeline.demo.load_domains import load_all_domains_separately

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def federation_client(graph_store: GraphStore, tmp_path, monkeypatch):
    load_all_domains_separately(graph_store)

    monkeypatch.setenv("BOM_REPO_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("BOM_DUCKDB_PATH", str(tmp_path / "bom.duckdb"))

    ctx = server.BomAgentContext.create(
        repo_root=REPO_ROOT,
        duckdb_path=str(tmp_path / "bom.duckdb"),
        graph=graph_store,
    )
    server._context = ctx
    client = TestClient(server.app)
    yield client
    ctx.close()
    server._context = None


def test_list_federation_domains(federation_client) -> None:
    body = federation_client.get("/v1/federation/domains").json()
    assert body["bridge_key"] == "Component.id"
    ids = {d["graph_id"] for d in body["domains"]}
    assert ids == {"sourcing", "ebom", "routing"}


def test_domain_query_sourcing(federation_client) -> None:
    response = federation_client.post(
        "/v1/federation/domain-query",
        json={"graph_id": "sourcing", "supplier_id": "SUP-001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "domain"
    assert body["result"]["graph_id"] == "sourcing"
    assert body["result"]["rows"]
    query = body["query"]
    assert query["graph_id"] == "sourcing"
    assert query["query_name"] == "components_by_supplier"
    assert query["language"] == "Cypher"
    assert query["parameters"]["supplier_id"] == "SUP-001"
    assert "MATCH" in query["cypher"]
    assert "SUPPLIED_BY" in query["cypher"]


def test_domain_query_ebom_requires_component_ids(federation_client) -> None:
    response = federation_client.post(
        "/v1/federation/domain-query",
        json={"graph_id": "ebom"},
    )
    assert response.status_code == 400


def test_federation_analyze(federation_client) -> None:
    response = federation_client.post(
        "/v1/federation/analyze",
        json={"supplier_id": "SUP-001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "federation"
    assert body["supplier_id"] == "SUP-001"
    assert len(body["domain_queries"]) == 3
    assert body["federated_rows"]
    assert body["graph_view"]["node_count"] >= 1
    assert body["join_plan"]
