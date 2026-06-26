# Setup and demos

How to install dependencies, start Neo4j and the agent, and run CLI demos.

**Audience:** coding agents, contributors, demo presenters.

**Related:** [testing-and-quality.md](testing-and-quality.md) (tests) · [demo-runbook.md](demo-runbook.md) (full walkthrough) · [development.md](development.md) · [seeding.md](seeding.md) · [AGENTS.md](../AGENTS.md)

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| [uv](https://docs.astral.sh/uv/) | Python package manager (Python **3.10+**) |
| Docker or [Colima](https://github.com/abiosoft/colima) | Neo4j and optional LiteLLM/Langfuse stack |
| Git clone | `cd` into the repository root for all commands below |

```bash
colima start    # if Docker is not running (macOS)
docker info     # should succeed
```

---

## One-time setup

From the repository root:

```bash
uv sync
cp .env.example .env    # edit BOM_NEO4J_* , API keys as needed
uv run python scripts/sync_ontology.py
```

For the **full stack** (LLM + Langfuse), also install extras:

```bash
uv sync --extra observability --extra gateway
```

Seeding details: [seeding.md](seeding.md).

---

## Start the app

Pick the path that matches what you need. All paths that use graph data require **Neo4j** (with the **n10s** plugin for L3 SHACL validation on seed/audit).

### Neo4j (required for graph-backed flows)

Start Neo4j via Docker Compose (includes n10s for SHACL):

```bash
./scripts/start_stack.sh          # Neo4j + LiteLLM + Langfuse (recommended)
# or Neo4j only:
docker compose --profile neo4j up -d
```

Default connection (also in `.env.example`):

| Variable | Default |
|----------|---------|
| `BOM_NEO4J_URI` | `bolt://localhost:7687` |
| `BOM_NEO4J_USER` | `neo4j` |
| `BOM_NEO4J_PASSWORD` | `password` |

Wait until bolt accepts connections, then seed validated demo data:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

Optional L3 proof (Cypher + Pydantic + Neosemantics SHACL):

```bash
BOM_L3_REQUIRE_SHACL=1 uv run python scripts/audit_neo4j.py
```

Skip Neo4j when you only need LiteLLM/Langfuse: `./scripts/start_stack.sh --no-neo4j`

---

### Path A — Agent UI, tools mode (no LLM, no Docker LLM stack)

Heuristic planner only; no API keys required beyond Neo4j.

```bash
# Terminal 1 — Neo4j (if not already running)
docker compose --profile neo4j up -d

# Terminal 2 — seed + agent
export BOM_REPO_ROOT=$(pwd)
uv run python scripts/seed_complex_bom.py --reset
uv run python -m app.agent
```

Open **http://localhost:8080/ui/** and run a goal such as `Analyze supplier impact for SUP-002` with mode **tools**.

Health check:

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8080/v1/config
```

---

### Path B — Full stack (Neo4j + LiteLLM + Langfuse + agent UI)

For LLM planning, Gemini via LiteLLM, and Langfuse traces. Step-by-step narrative: [demo-runbook.md §B](demo-runbook.md#part-b--full-stack-setup-litellm--langfuse--agent).

```bash
# 1. One-time: uv sync --extra observability --extra gateway ; configure .env (GEMINI_API_KEY, etc.)

# 2. Terminal A — Docker stack
./scripts/start_stack.sh

# 3. After Langfuse is Ready — create API keys in http://localhost:3000 → add to .env

# 4. Terminal B — seed + agent
uv run python scripts/seed_complex_bom.py --reset
uv run --extra observability python -m app.agent
```

| Service | URL |
|---------|-----|
| Agent UI | http://localhost:8080/ui/ |
| Neo4j Browser | http://127.0.0.1:7474 |
| LiteLLM | http://127.0.0.1:4000/v1 |
| Langfuse | http://127.0.0.1:3000 |

Stop stack: `./scripts/stop_stack.sh`

---

### Path C — CLI demos (no HTTP server)

Interactive scripts; use `--reset` on the seed script first for a clean graph.

| Script | Command | What it shows |
|--------|---------|----------------|
| Federation demo | `uv run python scripts/demo_federation.py --reset` | Per-domain seed, validate, query, federated mitigations |
| Graph + tools | `uv run python scripts/demo.py` | Interactive graph exploration |
| Agent (local) | `uv run python scripts/demo_agent.py` | Agent Skills + tool run |
| Skill CLI | `uv run python skills/bom-graph-explorer/scripts/explore_graph.py --seed --mode supplier-impact --supplier-id SUP-001` | Exploration without HTTP server |

Non-interactive: `DEMO_NONINTERACTIVE=1 uv run python scripts/demo.py`

Script index: [scripts/README.md](../scripts/README.md).

---

## Install Agent Skills (external agents)

Skill sources live under `skills/`. Install path is chosen by the user (Cursor, Claude Code, etc.).

```bash
# Replace <source> with this repo path or git URL
npx skils add <source> --path skills/bom-ontology
npx skils add <source> --path skills/bom-graph-explorer
```

Install **bom-ontology** first. This repository does not commit tool-specific copies under `.cursor/skills/`.

---

## Run tests

Quick reference — full guide: **[testing-and-quality.md](testing-and-quality.md)**.

### Offline (no Neo4j)

```bash
uv sync --extra dev
uv run pytest -q tests/test_schema.py tests/test_shacl_codegen.py tests/test_agent.py
```

### With Neo4j (integration)

Start Neo4j with n10s (see above), then:

```bash
uv run pytest -q tests/test_l3_audit.py tests/test_shacl_audit.py tests/test_federation.py
```

### Full local gate (before PR)

```bash
uv sync --extra dev
uv run ruff check ontology domains pipeline app tests scripts
uv run mypy ontology domains pipeline app
uv run pytest -q -rs
```

CI runs the same static checks plus a Neo4j service with n10s and `BOM_L3_REQUIRE_SHACL=1` on seed/audit — see [testing-and-quality.md §7](testing-and-quality.md#7-what-is-not-covered-yet).

---

## Remote agent API (summary)

- `GET /health`, `GET /v1/config` — readiness and `langfuse_configured` / `llm_configured`
- `POST /v1/agent/run` — response: `explanation`, `findings`, `evidence`, `graph_view`; `mode`: `auto` | `tools` | `llm`

curl examples: [demo-runbook.md](demo-runbook.md). Agent framework: [agent-runtime.md](agent-runtime.md).
