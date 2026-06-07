# Observability (Langfuse)

The web UI is **user-facing** (summary, key findings, evidence, supply chain map). Developer details — Agent Skills, planner mode, tool arguments, store names, raw JSON, and evidence pointers — are sent to **Langfuse** when configured.

**What to check where (UI vs Langfuse vs Domain/Federation tabs):** [demo-runbook.md](demo-runbook.md#part-d--verification--evaluation) — includes demo scenario playbooks and evaluation rubric.

**Docs index:** [development.md](development.md). **Full stack (Docker + agent + UI):** [demo-runbook.md](demo-runbook.md#part-b--full-stack-setup-litellm--langfuse--agent).

## Local self-host (Docker Compose)

Langfuse runs from the single root **`docker-compose.yml`** (`--profile langfuse`).

### 1. Start Langfuse

With LiteLLM together:

```bash
cd /path/to/bom-knowledge-graph-agent-skill
./scripts/start_stack.sh
```

Langfuse only:

```bash
docker compose --profile langfuse up -d
```

Wait until `langfuse-web` logs **Ready** (about 2–3 minutes on first pull). Open **http://localhost:3000**.

Stop:

```bash
./scripts/stop_stack.sh
```

Remove data volumes as well:

```bash
./scripts/stop_stack.sh -v
```

### 2. Create API keys

1. Sign up in the Langfuse UI (first visit only).
2. Create or open a project → **Settings** → **API Keys**.
3. Copy **Public key** and **Secret key**.

### 3. Configure the BOM agent

```bash
uv sync --extra observability
```

Add to `.env`:

```bash
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

Restart the agent (env is read at process start):

```bash
source .env
export BOM_REPO_ROOT=$(pwd)
uv run python -m app.agent
```

Run an analysis from **http://localhost:8080/ui/** — traces appear in Langfuse under **Traces** (name: `bom-agent-run`).

### Optional: stronger local secrets

For anything beyond a laptop demo, set in `.env` before `docker compose up`:

```bash
# openssl rand -hex 32
ENCRYPTION_KEY=...
NEXTAUTH_SECRET=...
SALT=...
REDIS_AUTH=...
MINIO_ROOT_PASSWORD=...
POSTGRES_PASSWORD=...
```

### Ports (default)

| Port | Service |
|------|---------|
| 3000 | Langfuse UI + API (`LANGFUSE_HOST`) |
| 9090 | MinIO S3 API (blob storage) |
| 5432, 6379, 8123 | Postgres, Redis, ClickHouse (localhost only) |

## Langfuse Cloud (alternative)

No Docker required. Use keys from [cloud.langfuse.com](https://cloud.langfuse.com):

```bash
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

## What appears in Langfuse

Each `POST /v1/agent/run` creates a trace **`bom-agent-run`** with:

| Observation | Content |
|-------------|---------|
| Agent root | User goal, mode |
| Span `planning` | Heuristic vs LLM planner, planned `tool_calls` |
| Generations `planner` / `summarize` | LLM messages and outputs (when LLM is configured) |
| Tools `tool:*` | Arguments, query description, stores, raw `data` |
| Trace output | Explanation, evidence, graph counts |
| Trace metadata | Full `run_report`, `tool_results`, notes |

## Verify telemetry

```bash
uv sync --extra observability
uv run python scripts/verify_langfuse_telemetry.py
```

Or check the running agent loaded keys:

```bash
curl -s http://127.0.0.1:8080/v1/config | python3 -m json.tool
# expect "langfuse_configured": true
```

After `.env` changes, **restart** the agent (`uv run python -m app.agent`). The server loads `.env` from `BOM_REPO_ROOT` (or cwd) on startup.

In Langfuse UI: **Traces** → filter name **`bom-agent-run`**.

## Without Langfuse

If keys are unset (or `langfuse` is not installed), telemetry is a no-op; the UI and API still work.

## API surface

- **`POST /v1/agent/run`** — user-facing fields: `goal`, `explanation`, `findings`, `evidence`, `graph_view`. Operator detail (planner, tools, Cypher, raw JSON): Langfuse metadata — see [demo-runbook.md](demo-runbook.md#d3-ui-vs-langfuse).
- Integrations: `GET /v1/tools`, `POST /v1/tools/invoke`, `GET /v1/skills/system-prompt`.
- Full internal `AgentRunResult` in Python: `BomAutonomousAgent.run()`.
