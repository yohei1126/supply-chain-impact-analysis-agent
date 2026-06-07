# Setup and demos

Python environment, Agent Skill install, CLI demos, and pointers to the full local stack.

**Audience:** coding agents, contributors, demo presenters.

**Related:** [AGENTS.md](../AGENTS.md) · [seeding.md](seeding.md) · [demo-runbook.md](demo-runbook.md) · [development.md](development.md) · [scripts/README.md](../scripts/README.md)

---

## Python environment (repo checkout)

```bash
cd /path/to/supply-chain-impact-analysis-agent
uv sync
uv run python scripts/sync_ontology.py      # after schema.py changes
uv run python scripts/seed_complex_bom.py --reset   # validated synthetic BOM
```

Seeding details: [seeding.md](seeding.md).

## Install Agent Skills (user-chosen agent host)

Skill sources live under `skills/`. The install path on disk is chosen by the user (Cursor, Claude Code, CLI agent, etc.).

```bash
# Replace <source> with this repo path or git URL
npx skils add <source> --path skills/bom-ontology
npx skils add <source> --path skills/bom-graph-explorer
```

Install **bom-ontology** first (schema). **bom-graph-explorer** depends on it for exploration workflows.

This repository does not commit tool-specific copies under `.cursor/skills/`.

## CLI demos (Python runtime in this repo)

| Script | Command | What it shows |
|--------|---------|----------------|
| Graph + tools | `uv run python scripts/demo.py` | Interactive graph exploration |
| Agent (local) | `uv run python scripts/demo_agent.py` | Agent Skills + tool run |
| Federation demo | `uv run python scripts/demo_federation.py --reset` | Per-domain seed, validate, query, federated mitigations — [demo-runbook.md](demo-runbook.md#part-a--federation-cli-no-docker--llm) |
| Skill CLI | `uv run python skills/bom-graph-explorer/scripts/explore_graph.py --seed --mode supplier-impact --supplier-id SUP-001` | Exploration without HTTP server |

Non-interactive: `DEMO_NONINTERACTIVE=1 uv run python scripts/demo.py`

All under `scripts/` — see [scripts/README.md](../scripts/README.md). Demos call `seed_complex_bom()`; use `--reset` on the seed script first for a clean Neo4j + DuckDB tree.

## Docker stack (Neo4j + LiteLLM + Langfuse)

```bash
./scripts/start_stack.sh
uv run python scripts/seed_complex_bom.py --reset
```

Stop: `./scripts/stop_stack.sh`

## Local full stack (LiteLLM + Langfuse + agent UI)

**Human runbook:** [demo-runbook.md](demo-runbook.md) · **Developer setup:** [development.md](development.md) · **Terminology:** [terminology.md](terminology.md) · **Graph Contract:** [graph-contract.md](graph-contract.md) · **Graph context:** [graph-context.md](graph-context.md)

| Step | What |
|------|------|
| 1 | `uv sync --extra observability --extra gateway`, configure `.env`, start Neo4j if needed, `seed_complex_bom.py --reset` |
| 2 | `./scripts/start_stack.sh` → LiteLLM `:4000`, Langfuse `:3000`, Neo4j `:7687` |
| 3 | Langfuse UI → API keys → `.env` |
| 4 | `uv run --extra observability python -m app.agent` → UI **http://localhost:8080/ui/** |
| 5 | Analyze in UI; inspect traces in Langfuse (`bom-agent-run`) |

- **User UI:** Summary, Key findings, Evidence, Supply chain map only.
- **Langfuse:** [observability.md](observability.md). **Demo verify & evaluate:** [demo-runbook.md](demo-runbook.md#part-d--verification--evaluation).
- **LiteLLM / Gemini:** [llm-gateway.md](llm-gateway.md).

Requires `BOM_REPO_ROOT` (defaults to cwd); agent loads `.env` on startup. Re-seed before first UI session if `data/` is empty.

## Remote agent API (summary)

- `GET /health`, `GET /v1/config` — readiness and `langfuse_configured` / `llm_configured`
- `POST /v1/agent/run` — user JSON (`explanation`, `findings`, `evidence`, `graph_view`); `mode`: `auto` | `tools` | `llm`

Details and curl examples: [demo-runbook.md](demo-runbook.md). Agent framework: [agent-runtime.md](agent-runtime.md).
