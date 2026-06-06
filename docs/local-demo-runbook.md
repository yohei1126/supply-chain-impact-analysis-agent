# Local demo runbook (LiteLLM + Langfuse + agent UI)

End-to-end steps to run the BOM supply-impact demo on your machine: Docker stack → BOM data → agent server → web UI → Langfuse traces.

**Federation-only demo (no Docker / no LLM):** [federation-demo-runbook.md](federation-demo-runbook.md) — per-domain seed, validate, query, federated mitigations.

**Overview:** [README.md](../README.md). **Development / layout / CLI demos:** [development.md](development.md). **Agents:** [AGENTS.md](../AGENTS.md) §5.4–5.5. **LiteLLM / Langfuse:** [llm-gateway.md](llm-gateway.md), [observability.md](observability.md).

## What you will run

| Process | URL | Role |
|---------|-----|------|
| LiteLLM (Docker) | http://127.0.0.1:4000/v1 | OpenAI-compatible LLM gateway (e.g. Gemini) |
| Langfuse (Docker) | http://127.0.0.1:3000 | Traces: planner, tools, raw JSON (not in UI) |
| BOM agent | http://127.0.0.1:8080 | API + user UI |
| User UI | http://127.0.0.1:8080/ui/ | Summary, Key findings, Evidence, Supply chain map |

Use **three terminals** (or run Docker detached in one).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- **Docker** available (Docker Desktop or [Colima](https://github.com/abiosoft/colima))
- Repo cloned and `cd` into the root

```bash
colima start          # if using Colima and Docker is not running
docker info           # should succeed
```

## 1. One-time setup

From the repository root:

```bash
uv sync --extra observability --extra gateway
cp .env.example .env    # skip if .env already exists
```

Edit `.env`:

| Variable | Example | Notes |
|----------|---------|--------|
| `GEMINI_API_KEY` | `...` | Required for LiteLLM → Gemini (`config/litellm.yaml`) |
| `OPENAI_API_BASE` | `http://127.0.0.1:4000/v1` | Points at Docker LiteLLM |
| `OPENAI_API_KEY` | `sk-litellm-local` | Same as `LITELLM_MASTER_KEY` |
| `OPENAI_MODEL` | `bom-gemini-3.5-flash` | LiteLLM model alias |
| `LANGFUSE_HOST` or `LANGFUSE_BASE_URL` | `http://localhost:3000` | Local Langfuse |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | from Langfuse UI | After step 3 |

Seed ontology-validated demo BOM (graph + vector + RDB):

```bash
uv run python scripts/seed_complex_bom.py --reset
```

## 2. Terminal A — LiteLLM + Langfuse (Docker)

```bash
./scripts/run_docker_stack.sh -d
```

Wait until:

- Langfuse: `langfuse-web` logs **Ready** (first boot ~2–3 minutes)
- LiteLLM: container healthy on port **4000**

Quick checks:

LiteLLM is configured with `LITELLM_MASTER_KEY` in [`config/litellm.yaml`](../config/litellm.yaml). **Unauthenticated** requests to `/health` return **401** — that still means the proxy is listening. Use the same key as in `.env` (`sk-litellm-local` by default):

```bash
# LiteLLM — expect 200 (use your LITELLM_MASTER_KEY / OPENAI_API_KEY value)
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer sk-litellm-local" \
  http://127.0.0.1:4000/health

# Optional: list model aliases exposed to the agent
curl -s http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer sk-litellm-local"

# Langfuse UI — expect 200 (no auth header)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
```

Expect models such as `bom-gemini-3.5-flash`, `bom-gemini-planner`, and `bom-openai-planner` in the `/v1/models` response.

Stop later:

```bash
docker compose --profile langfuse --profile litellm down
```

## 3. Langfuse — first-time API keys

1. Open **http://localhost:3000**
2. Sign up / sign in (first visit only)
3. Create or open a project → **Settings** → **API Keys**
4. Copy **Public key** and **Secret key** into `.env`:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

Verify connectivity (optional):

```bash
uv run --extra observability python scripts/verify_langfuse_telemetry.py
```

Expect at least:

```
Langfuse telemetry check
  LANGFUSE_HOST: http://localhost:3000
  keys set: True
  auth_check: OK
```

Before any agent run, trace list may be empty — that is fine if `auth_check: OK`.

## 4. Terminal B — BOM agent

The agent loads `.env` from the repo root on startup. Restart after any `.env` change.

```bash
export BOM_REPO_ROOT=$(pwd)
uv run --extra observability python -m app.agent
```

Confirm Langfuse is wired:

```bash
curl -s http://127.0.0.1:8080/v1/config | python3 -m json.tool
```

Expect:

```json
"langfuse_configured": true,
"llm_configured": true
```

If `langfuse_configured` is **false**, stop the agent and ensure `.env` has `LANGFUSE_*` keys, then start again with `--extra observability`.

Health check:

```bash
curl -s http://127.0.0.1:8080/health
```

## 5. Browser — federation UI

Open **http://localhost:8080/ui/**

Top-right pill should show **Ready**. The UI has three tabs — **Domain query**, **Federation**, and **Agent (LLM)**.

### Domain query tab

Query **one** Lance graph at a time using **Cypher** (`lance-graph` over Lance `graph_nodes` / `graph_edges`).

| Domain | Example | What you see |
|--------|---------|--------------|
| **sourcing** | `SUP-002` | Components with `SUPPLIED_BY` to that supplier |
| **ebom** | `COMP-103` | Products linked via `USED_IN` |
| **routing** | `COMP-103` | Processes linked via `INPUT_OF` |

After **Run domain query**, check **Cypher query** for the executed statement and parameters.

Suggested flow:

1. Run sourcing for `SUP-002` — note component IDs returned.
2. Switch to **ebom**, paste those component IDs, run again — same IDs, different graph.
3. Switch to **Federation** tab to see all three joined on `Component.id`.

### Federation tab

1. Enter disrupted supplier (e.g. `SUP-002`) or pick an example.
2. Click **Run federation**.
3. Review the pipeline: sourcing → ebom → routing on `Component.id`.
4. Read **Problems**, **Mitigations**, **Joined impact rows**, and the federated supply chain map.

### Agent (LLM) tab

Natural-language questions with planner + optional LLM summary (requires LiteLLM when `mode=auto`).

1. Click an example, e.g. **Supplier SUP-002 disruption**
2. Click **Analyze**
3. Read **Summary**, **Key findings**, **Evidence**, and the supply chain map

Other examples: **Path to motor assembly** (`COMP-103` → `PROD-901`), **Brass valve parts** (hybrid vector + RDB + graph).

Use this tab for Langfuse **`bom-agent-run`** traces from the browser.

### REST API (no browser)

```bash
curl -s -X POST http://127.0.0.1:8080/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Analyze supplier impact for SUP-002","mode":"auto"}' | python3 -m json.tool
```

Federation endpoints:

```bash
curl -s -X POST http://127.0.0.1:8080/v1/federation/domain-query \
  -H 'Content-Type: application/json' \
  -d '{"graph_id":"sourcing","supplier_id":"SUP-002"}' | python3 -m json.tool

curl -s -X POST http://127.0.0.1:8080/v1/federation/analyze \
  -H 'Content-Type: application/json' \
  -d '{"supplier_id":"SUP-002"}' | python3 -m json.tool
```

## 6. Langfuse — confirm telemetry

After at least one **Agent (LLM)** tab run or agent API call (see §5):

1. Open **http://localhost:3000** → **Traces**
2. Find trace name **`bom-agent-run`**
3. Expand spans: `planning`, `tool:bom_supplier_impact` (etc.), generations `planner` / `summarize` when LLM is used

CLI check:

```bash
uv run --extra observability python scripts/verify_langfuse_telemetry.py
```

After at least one analysis, expect something like:

```
Langfuse telemetry check
  LANGFUSE_HOST: http://localhost:3000
  keys set: True
  auth_check: OK

Recent traces (up to 10): 6
  - bom-agent-run id=0d3c92dcb4ef6d27580d323bbe8ade81
  - bom-agent-run id=a350907567f28afe9d52f26d27497337
  ...

OK: found 6 bom-agent-run trace(s). Open Langfuse UI -> Traces.
```

Trace IDs differ per run; what matters is `auth_check: OK` and one or more **`bom-agent-run`** entries.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Cannot connect to the Docker daemon` | `colima start` or start Docker Desktop |
| Langfuse never becomes Ready | `docker compose --profile langfuse logs -f langfuse-web` |
| LiteLLM `/health` returns **401** without `Authorization` | Expected when `master_key` is set — retry with `Bearer` + `LITELLM_MASTER_KEY` (see step 2) |
| LiteLLM **401** on `/v1/chat/completions` or model errors | Set `GEMINI_API_KEY` in `.env`; ensure `OPENAI_API_KEY` matches `LITELLM_MASTER_KEY`; restart stack |
| `langfuse_configured: false` on agent | Add keys to `.env`; restart agent with `--extra observability` |
| Empty map / no findings | `uv run python scripts/seed_complex_bom.py --reset`; restart agent |
| Port 4000 already in use | Stop `./scripts/run_litellm_proxy.sh` if running, or change `LITELLM_PORT` |
| Port 8080 in use | `export BOM_AGENT_PORT=8081` and use `http://localhost:8081/ui/` |

## Optional: LiteLLM without Docker

If you prefer a local LiteLLM process instead of the Docker profile:

```bash
./scripts/run_litellm_proxy.sh
```

Do **not** run Docker LiteLLM on port 4000 at the same time. Keep `OPENAI_API_BASE=http://127.0.0.1:4000/v1` in `.env`.
