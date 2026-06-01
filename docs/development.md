# Development guide

Setup, project layout, seeding, CLI demos, and tests. For the full LiteLLM + Langfuse + web UI flow, see [local-demo-runbook.md](local-demo-runbook.md). For agent/automation conventions, see [AGENTS.md](../AGENTS.md).

## Ontology (single source of truth)

```
bom_graph/schema.py                          ← edit constraints (Pydantic)
        │
        ▼  uv run python scripts/sync_ontology.py
skills/bom-ontology/assets/ontology.json     ← published artifact for Agent Skills
```

- **Authoring:** only change `bom_graph/schema.py`.
- **Skills:** read generated `ontology.json`; do not hand-edit it.
- **Runtime writes:** Pydantic validators on every graph/RDB/vector insert.

After `schema.py` changes:

```bash
uv run python scripts/sync_ontology.py
uv run pytest -q tests/test_skill_ontology_asset.py
```

Seeding and validation details: [AGENTS.md](../AGENTS.md) §4.

## Project layout

```
skills/
  bom-ontology/           schema skill + assets/ontology.json
  bom-graph-explorer/     exploration workflows
bom_graph/                Python runtime (graph, hybrid store, agent)
  agent/                  FastAPI server + web UI + Langfuse telemetry
config/                   litellm.yaml
scripts/                  seed, demos, Docker helpers
data/                     LanceDB + DuckDB (local, gitignored)
docs/                     human runbooks and operator guides
docker-compose.yml        optional LiteLLM + Langfuse (Compose profiles)
```

## Initial setup

From the repository root:

```bash
uv sync
# Optional extras:
#   uv sync --extra gateway        # LiteLLM CLI (local proxy without Docker)
#   uv sync --extra observability  # Langfuse client for agent telemetry

cp .env.example .env   # then edit keys (GEMINI_API_KEY, LANGFUSE_*, etc.)

uv run python scripts/sync_ontology.py      # after schema.py edits only
uv run python scripts/seed_complex_bom.py --reset
```

Default seeded BOM: **3 suppliers**, **3 products**, **4 processes**, **12 components** (`bom_graph/sample_bom.py`).

| Path | Role |
|------|------|
| `data/lancedb` | Graph + vector tables |
| `data/bom.duckdb` | Component attributes (RDB) |

## Install Agent Skills (external agents)

Skills are installed into the user’s agent host (Cursor, Claude Code, etc.), not copied into this repo.

```bash
# Replace <source> with this repo path or git URL
npx skils add <source> --path skills/bom-ontology
npx skils add <source> --path skills/bom-graph-explorer
```

Install **bom-ontology** first. See [skills/README.md](../skills/README.md).

## CLI demos (no HTTP server)

Interactive scripts with step explanations (`Enter` to continue). Non-interactive: `DEMO_NONINTERACTIVE=1`.

```bash
uv run python scripts/demo.py           # graph + exploration tools
uv run python scripts/demo_hybrid.py    # vector → RDB → graph
uv run python scripts/demo_agent.py     # agent Skills + tools (local)
```

Re-seed before demos if `data/` is stale:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

Script index: [scripts/README.md](../scripts/README.md).

## Agent server (without full Docker stack)

Minimal agent + UI (heuristic planner only, no LiteLLM/Langfuse required):

```bash
export BOM_REPO_ROOT=$(pwd)
uv run python scripts/seed_complex_bom.py --reset
uv run python -m bom_graph.agent
# http://localhost:8080/ui/
```

With LLM and Langfuse, use [local-demo-runbook.md](local-demo-runbook.md).

### API smoke test

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8080/v1/config
curl -s -X POST http://localhost:8080/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Analyze supplier impact for SUP-002","mode":"tools"}'
```

User-facing response fields: `explanation`, `findings`, `evidence`, `graph_view`.

## Docker services

Single file: `docker-compose.yml` with profiles `litellm` and `langfuse`.

```bash
./scripts/run_docker_stack.sh -d    # both profiles
docker compose --profile langfuse up -d
docker compose --profile litellm up -d
```

Requires Docker (or Colima: `colima start`). See [observability.md](observability.md) and [llm-gateway.md](llm-gateway.md).

## Tests

```bash
uv sync
uv run pytest -q
```

Targeted:

```bash
uv run pytest -q tests/test_schema.py
uv run pytest -q tests/test_lance_graph_store.py
uv run pytest -q tests/test_hybrid_store.py
uv run pytest -q tests/test_agent.py
```

## Related docs

| Topic | Doc |
|-------|-----|
| Full local demo | [local-demo-runbook.md](local-demo-runbook.md) |
| LiteLLM / Gemini | [llm-gateway.md](llm-gateway.md) |
| Langfuse traces | [observability.md](observability.md) |
| Agent contributors | [AGENTS.md](../AGENTS.md) |
