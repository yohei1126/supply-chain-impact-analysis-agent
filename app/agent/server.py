from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent.context import BomAgentContext
from app.agent.llm_config import load_openai_compat_settings
from app.agent.runner import BomAutonomousAgent
from app.agent.telemetry import langfuse_configured, start_run_tracer
from app.agent.types import AgentRunResult, ToolCall
from app.agent.user_response import build_user_response
from app.federation.analysis import (
    analyze_supplier_disruption,
    query_ebom_for_components,
    query_routing_for_components,
    query_sourcing_for_supplier,
)
from app.federation.serialize import (
    build_domain_query_spec,
    domain_query_to_dict,
    federated_analysis_to_dict,
)
from app.graph_viz import build_graph_view

_context: BomAgentContext | None = None
_STATIC_DIR = Path(__file__).resolve().parent / "static"


def _load_repo_env() -> None:
    """Load .env from BOM_REPO_ROOT (or cwd) so Langfuse/OpenAI vars apply without manual export."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(os.getenv("BOM_REPO_ROOT", Path.cwd()))
    load_dotenv(root / ".env")


_load_repo_env()


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentRunRequest(BaseModel):
    goal: str
    mode: str = "auto"
    tool_calls: list[ToolCallRequest] | None = None
    summarize: bool = True


class AgentRunResponse(BaseModel):
    """User-facing payload; technical run details go to Langfuse when configured."""

    goal: str
    explanation: str
    findings: list[str] = Field(default_factory=list)
    evidence: list[dict[str, str]] = Field(default_factory=list)
    graph_view: dict[str, Any] = Field(default_factory=dict)
    cypher_executions: list[dict[str, Any]] = Field(default_factory=list)
    run_summary: dict[str, Any] = Field(default_factory=dict)


GraphId = Literal["sourcing", "ebom", "routing"]


class DomainQueryRequest(BaseModel):
    graph_id: GraphId
    supplier_id: str | None = None
    component_ids: list[str] | None = None


class FederationAnalyzeRequest(BaseModel):
    supplier_id: str


def _get_context() -> BomAgentContext:
    if _context is None:
        raise HTTPException(status_code=503, detail="Agent context not initialized")
    return _context


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _context
    repo_root = Path(os.getenv("BOM_REPO_ROOT", Path.cwd()))
    _context = BomAgentContext.create(
        repo_root=repo_root,
        lancedb_path=os.getenv("BOM_LANCEDB_PATH", "data/lancedb"),
        duckdb_path=os.getenv("BOM_DUCKDB_PATH", "data/bom.duckdb"),
    )
    yield
    if _context is not None:
        _context.close()
        _context = None


app = FastAPI(
    title="BOM Knowledge Graph Agent",
    description="Remote autonomous agent API aligned with Agent Skills and app runtime.",
    version="0.1.0",
    lifespan=lifespan,
)

if _STATIC_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=_STATIC_DIR, html=True), name="ui")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/", status_code=302)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/config")
def runtime_config() -> dict[str, Any]:
    settings = load_openai_compat_settings()
    return {
        "ready": True,
        "llm_configured": settings.configured,
        "langfuse_configured": langfuse_configured(),
    }


@app.get("/v1/skills/system-prompt")
def system_prompt() -> dict[str, str]:
    ctx = _get_context()
    return {"prompt": ctx.system_prompt()}


@app.get("/v1/tools")
def list_tools() -> dict[str, Any]:
    ctx = _get_context()
    return {"tools": ctx.tools.list_tools()}


@app.post("/v1/tools/invoke")
def invoke_tool(body: ToolCallRequest) -> dict[str, Any]:
    ctx = _get_context()
    try:
        return ctx.tools.invoke(body.name, **body.arguments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _graph_view_for_federation(ctx: BomAgentContext, supplier_id: str, federated_rows: list[dict[str, Any]]) -> dict[str, Any]:
    seeds: set[tuple[str, str]] = {("Supplier", supplier_id)}
    for row in federated_rows:
        if row.get("component_id"):
            seeds.add(("Component", str(row["component_id"])))
        if row.get("product_id"):
            seeds.add(("Product", str(row["product_id"])))
    return build_graph_view(ctx.graph, seeds, expand_hops=1)


@app.get("/v1/federation/domains")
def list_federation_domains() -> dict[str, Any]:
    return {
        "domains": [
            {
                "graph_id": "sourcing",
                "owner_team": "procurement",
                "nodes": ["Component", "Supplier"],
                "edges": ["SUPPLIED_BY"],
                "query": "components_by_supplier",
                "param": "supplier_id",
            },
            {
                "graph_id": "ebom",
                "owner_team": "engineering",
                "nodes": ["Component", "Product"],
                "edges": ["USED_IN"],
                "query": "products_by_components",
                "param": "component_ids",
            },
            {
                "graph_id": "routing",
                "owner_team": "manufacturing",
                "nodes": ["Component", "Process", "Product"],
                "edges": ["INPUT_OF", "PRODUCED_BY"],
                "query": "processes_by_components",
                "param": "component_ids",
            },
        ],
        "bridge_key": "Component.id",
    }


@app.post("/v1/federation/domain-query")
def run_domain_query(body: DomainQueryRequest) -> dict[str, Any]:
    ctx = _get_context()
    if body.graph_id == "sourcing":
        if not body.supplier_id:
            raise HTTPException(status_code=400, detail="supplier_id is required for sourcing queries")
        result = query_sourcing_for_supplier(ctx.graph, body.supplier_id.strip())
    elif body.graph_id == "ebom":
        if not body.component_ids:
            raise HTTPException(status_code=400, detail="component_ids is required for ebom queries")
        result = query_ebom_for_components(ctx.graph, set(body.component_ids))
    elif body.graph_id == "routing":
        if not body.component_ids:
            raise HTTPException(status_code=400, detail="component_ids is required for routing queries")
        result = query_routing_for_components(ctx.graph, set(body.component_ids))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown graph_id: {body.graph_id}")

    return {
        "mode": "domain",
        "bridge_key": "Component.id",
        "query": build_domain_query_spec(
            result,
            supplier_id=body.supplier_id.strip() if body.supplier_id else None,
            component_ids=body.component_ids,
        ),
        "result": domain_query_to_dict(result),
    }


@app.post("/v1/federation/analyze")
def run_federation_analyze(body: FederationAnalyzeRequest) -> dict[str, Any]:
    ctx = _get_context()
    supplier_id = body.supplier_id.strip()
    if not supplier_id:
        raise HTTPException(status_code=400, detail="supplier_id is required")

    analysis = analyze_supplier_disruption(ctx.graph, supplier_id)
    payload = federated_analysis_to_dict(analysis)
    payload["graph_view"] = _graph_view_for_federation(ctx, supplier_id, analysis.federated_rows)
    return {"mode": "federation", **payload}


@app.post("/v1/agent/run", response_model=AgentRunResponse)
def run_agent(body: AgentRunRequest) -> AgentRunResponse:
    ctx = _get_context()
    agent = BomAutonomousAgent(ctx)

    explicit_calls = None
    if body.tool_calls:
        explicit_calls = [
            ToolCall(name=item.name, arguments=item.arguments) for item in body.tool_calls
        ]

    tracer = start_run_tracer(body.goal, body.mode)
    try:
        result: AgentRunResult = agent.run(
            body.goal,
            mode=body.mode,  # type: ignore[arg-type]
            tool_calls=explicit_calls,
            llm_settings=load_openai_compat_settings(),
            summarize=body.summarize,
            tracer=tracer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        tracer.flush()

    user = build_user_response(result)
    return AgentRunResponse(
        goal=user["goal"],
        explanation=user["explanation"],
        findings=user["findings"],
        evidence=user["evidence"],
        graph_view=user["graph_view"],
        cypher_executions=user["cypher_executions"],
        run_summary=user["run_summary"],
    )


def main() -> None:
    import uvicorn

    host = os.getenv("BOM_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("BOM_AGENT_PORT", "8080"))
    uvicorn.run("app.agent.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
