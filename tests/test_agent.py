import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent.context import BomAgentContext
from app.agent.runner import BomAutonomousAgent, plan_tools_from_goal
from app.agent.skills import build_system_prompt, load_skill_package
from app.federation.graph_store import GraphStore


REPO_ROOT = Path(__file__).resolve().parents[1]


def _seed_context(graph_store: GraphStore, tmp_path: Path) -> BomAgentContext:
    ctx = BomAgentContext.create(
        repo_root=REPO_ROOT,
        duckdb_path=str(tmp_path / "bom.duckdb"),
        graph=graph_store,
    )
    ctx.graph.add_node(
        "Supplier",
        {"id": "SUP-001", "company_name": "Nihon Steel", "country": "JP", "risk_level": "High"},
    )
    ctx.graph.add_node("Product", {"id": "PROD-900", "name": "Industrial Pump", "version": "v1"})
    ctx.component_master.upsert_component(
        {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0}
    )
    ctx.graph.add_edge(
        {
            "source_label": "Component",
            "source_id": "COMP-100",
            "target_label": "Supplier",
            "target_id": "SUP-001",
            "edge_type": "SUPPLIED_BY",
            "properties": {},
        }
    )
    ctx.graph.add_edge(
        {
            "source_label": "Component",
            "source_id": "COMP-100",
            "target_label": "Product",
            "target_id": "PROD-900",
            "edge_type": "USED_IN",
            "properties": {},
        }
    )
    return ctx


def test_load_agent_skills() -> None:
    pkg = load_skill_package(REPO_ROOT, "bom-ontology")
    assert pkg.name == "bom-ontology"
    assert "bom-ontology" in pkg.skill_md
    assert "ontology.json" in pkg.assets

    explorer = load_skill_package(REPO_ROOT, "bom-graph-explorer")
    assert "query-catalog.json" in explorer.assets
    assert "graph-context.json" in explorer.assets

    prompt = build_system_prompt(REPO_ROOT)
    assert "bom-graph-explorer" in prompt
    assert "query-catalog.json" in prompt
    assert "components_by_supplier" in prompt
    assert "cypher-compose.md" in prompt or "Cypher composition protocol" in prompt


def test_plan_tools_from_goal() -> None:
    calls = plan_tools_from_goal("supplier impact SUP-001")
    assert calls[0].name == "bom_supplier_impact"
    assert calls[0].arguments["supplier_id"] == "SUP-001"

    german = plan_tools_from_goal(
        "Our German brass supplier might face a port strike next month. "
        "Which finished products and component parts should we worry about?"
    )
    assert german[0].name == "bom_supplier_impact"
    assert german[0].arguments["supplier_id"] == "SUP-002"


def test_autonomous_agent_run(graph_store: GraphStore, tmp_path) -> None:
    ctx = _seed_context(graph_store, tmp_path)
    agent = BomAutonomousAgent(ctx)
    try:
        result = agent.run("supplier impact SUP-001", mode="tools")
        assert result.tool_calls
        assert result.results[0]["data"]
        assert result.explanation
        assert result.evidence
        assert result.run_report["executions"]
    finally:
        ctx.close()


def test_remote_agent_api(graph_store: GraphStore, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BOM_REPO_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("BOM_DUCKDB_PATH", str(tmp_path / "bom.duckdb"))

    from app.agent import server

    ctx = _seed_context(graph_store, tmp_path)
    server._context = ctx

    client = TestClient(server.app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ui/").status_code == 200
    assert "llm_configured" in client.get("/v1/config").json()

    tools = client.get("/v1/tools").json()["tools"]
    assert any(t["name"] == "bom_supplier_impact" for t in tools)

    response = client.post(
        "/v1/agent/run",
        json={"goal": "supplier impact SUP-001", "mode": "tools"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["explanation"]
    assert body["findings"]
    assert body["evidence"]
    assert body["graph_view"]["node_count"] >= 1
    assert body.get("cypher_executions")
    assert body["cypher_executions"][0]["steps"]
    assert "MATCH" in body["cypher_executions"][0]["steps"][0]["cypher"]
    assert "tool_calls" not in body
    assert "run_report" not in body

    ctx.close()
    server._context = None
