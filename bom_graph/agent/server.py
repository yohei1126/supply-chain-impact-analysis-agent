from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bom_graph.agent.context import BomAgentContext
from bom_graph.agent.llm_config import load_openai_compat_settings
from bom_graph.agent.runner import BomAutonomousAgent
from bom_graph.agent.telemetry import langfuse_configured, start_run_tracer
from bom_graph.agent.types import AgentRunResult, ToolCall
from bom_graph.agent.user_response import build_user_response

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
    description="Remote autonomous agent API aligned with Agent Skills and bom_graph runtime.",
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
    )


def main() -> None:
    import uvicorn

    host = os.getenv("BOM_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("BOM_AGENT_PORT", "8080"))
    uvicorn.run("bom_graph.agent.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
