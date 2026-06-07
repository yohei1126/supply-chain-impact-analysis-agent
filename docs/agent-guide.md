# Agent guide

Detailed setup, seeding, demos, and autonomous agent runtime for coding agents and developers.

**Audience:** coding agents, contributors.

**Related:** [AGENTS.md](../AGENTS.md) (principles and done criteria) · [development.md](development.md) · [local-demo-runbook.md](local-demo-runbook.md) · [testing-and-quality.md](testing-and-quality.md) · [project-layout.md](project-layout.md)

---

## Seeding synthetic BOM data (ontology validation)

Demo and agent runtime need Neo4j graph data and DuckDB component master under `data/`. **Do not hand-edit Neo4j databases or DuckDB files.** Load synthetic BOM through the Python stores so every node and edge is validated against the ontology defined in `ontology/schema.py`.

### One definition, two consumers (not two competing schemas)

| Role | File | Used when seeding? |
|------|------|-------------------|
| **Authoring (only place to edit constraints)** | `ontology/schema.py` | **Yes** — Pydantic validators on every write |
| **Published export for Agent Skills** | `skills/bom-ontology/assets/ontology.json` | **No** — generated; agents read this at prompt time |

`ontology.json` is **not** a second source of truth. `scripts/sync_ontology.py` calls `export_schema_bundle()` from `schema.py` and overwrites the JSON (see `meta.source` in the file). Seeding, tests, and stores all validate against **the same** `schema.py` definitions.

**Drift only happens if the workflow is skipped:** editing `ontology.json` by hand, or changing `schema.py` without running sync. Guardrail: `tests/test_skill_ontology_asset.py` asserts on-disk `ontology.json` matches a live export — run `uv run python scripts/sync_ontology.py` after schema edits, then commit the regenerated JSON.

```
ontology/schema.py  ──export_schema_bundle()──►  sync_ontology.py  ──►  ontology.json  (Skills / prompts)
     │
     └── validate_node_payload, RelationEdge, …  (seed, stores, pytest)
```

### What gets validated on each write

```
scripts/seed_complex_bom.py
        │
        ▼
pipeline/demo/seed.py  (orchestrates domain pipelines)
pipeline/demo/sample_data.py  (suppliers, products, processes, components, edges)
        │
        ├── graph.add_node(type, payload)  → validate_node_payload()  (per node type)
        ├── graph.add_edge(payload)        → RelationEdge  (allowed source/target pairs)
        └── component_master.upsert_component(...)  → ComponentNode + graph node
```

| Write API | Validator | Typical failure |
|-----------|-----------|-----------------|
| `GraphStore.add_node` | `validate_node_payload` | Missing field, wrong type, bad `country` length |
| `GraphStore.add_edge` | `RelationEdge` | Disallowed edge (e.g. `Product → Component` for `USED_IN`) |
| `ComponentMasterStore.upsert_component` | `ComponentNode` | Invalid component attributes |

Invalid rows raise `pydantic.ValidationError` or `ValueError`; nothing is partially committed for that failed call. Fix `pipeline/demo/sample_data.py` (or your own loader that calls the same APIs), not the binary DB files.

### Seed commands (from repository root)

```bash
uv sync

# After editing ontology/schema.py only (Skills / prompts):
uv run python scripts/sync_ontology.py

# Load synthetic BOM into Neo4j + data/bom.duckdb (validated writes):
uv run python scripts/seed_complex_bom.py --reset
```

| Flag / path | Meaning |
|-------------|---------|
| `--reset` | Clear Neo4j domain data and delete `data/bom.duckdb` before insert |
| `--duckdb-path` | Default `data/bom.duckdb` |
| `BOM_NEO4J_URI` | Default `bolt://localhost:7687` (see `.env.example`) |

Default dataset (`seed_complex_bom` in `pipeline/demo/`): **3 suppliers**, **3 products**, **4 processes**, **12 components**, with shared parts, multiple suppliers, and `SUPPLIED_BY` / `USED_IN` / `INPUT_OF` / `PRODUCED_BY` edges.

### Customize or extend the dataset

1. Edit **`pipeline/demo/sample_data.py`** (`SUPPLIERS`, `PRODUCTS`, `PROCESSES`, `COMPONENT_BOM`, `PRODUCT_PROCESSES`).
2. Stay within allowed node types and edge pairs (see `ALLOWED_EDGES` in `schema.py` or `ontology.json`).
3. Re-seed with `--reset`:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

`scripts/demo*.py` also call `seed_complex_bom()` but do not pass `--reset`; prefer the dedicated seed script when refreshing demo data before UI or API work.

### Verify after seeding

```bash
uv run python scripts/seed_complex_bom.py --reset
uv run pytest -q tests/test_schema.py tests/test_graph_store.py tests/test_component_master_store.py

# Quick exploration (also seeds if --seed):
uv run python skills/bom-graph-explorer/scripts/explore_graph.py --seed \
  --mode supplier-impact --supplier-id SUP-002
```

Then start CLI demos or the full stack (below) against the same `data/` paths.

---

## Setup, Agent Skill install, and demos

### Python environment (repo checkout)

```bash
cd /path/to/supply-chain-impact-analysis-agent
uv sync
uv run python scripts/sync_ontology.py      # after schema.py changes
uv run python scripts/seed_complex_bom.py --reset   # validated synthetic BOM
```

### Install Agent Skills (user-chosen agent host)

Skill sources live under `skills/`. The install path on disk is chosen by the user (Cursor, Claude Code, CLI agent, etc.).

```bash
# Replace <source> with this repo path or git URL
npx skils add <source> --path skills/bom-ontology
npx skils add <source> --path skills/bom-graph-explorer
```

Install **bom-ontology** first (schema). **bom-graph-explorer** depends on it for exploration workflows.

This repository does not commit tool-specific copies under `.cursor/skills/`.

### CLI demos (Python runtime in this repo)

| Script | Command | What it shows |
|--------|---------|----------------|
| Graph + tools | `uv run python scripts/demo.py` | Interactive graph exploration |
| Agent (local) | `uv run python scripts/demo_agent.py` | Agent Skills + tool run |
| Federation demo | `uv run python scripts/demo_federation.py --reset` | Per-domain seed, validate, query, federated mitigations — [federation-demo-runbook.md](federation-demo-runbook.md) |
| Skill CLI | `uv run python skills/bom-graph-explorer/scripts/explore_graph.py --seed --mode supplier-impact --supplier-id SUP-001` | Exploration without HTTP server |

Non-interactive: `DEMO_NONINTERACTIVE=1 uv run python scripts/demo.py`

All under `scripts/` — see [scripts/README.md](../scripts/README.md). Demos call `seed_complex_bom()`; use `--reset` on the seed script first for a clean Neo4j + DuckDB tree.

Start the local Docker stack (Langfuse + LiteLLM + Neo4j):

```bash
./scripts/start_stack.sh
uv run python scripts/seed_complex_bom.py --reset
```

Stop: `./scripts/stop_stack.sh`

### Local full stack (LiteLLM + Langfuse + agent UI)

**Human runbook:** [local-demo-runbook.md](local-demo-runbook.md) · **Developer setup:** [development.md](development.md) · **Enterprise graph design:** [enterprise-graph-design.md](enterprise-graph-design.md) · **Graph context:** [graph-context.md](graph-context.md) · **Disruption response:** [supply-chain-disruption-response.md](supply-chain-disruption-response.md)

| Step | What |
|------|------|
| 1 | `uv sync --extra observability --extra gateway`, configure `.env`, start Neo4j if needed, `seed_complex_bom.py --reset` |
| 2 | `./scripts/start_stack.sh` → LiteLLM `:4000`, Langfuse `:3000`, Neo4j `:7687` |
| 3 | Langfuse UI → API keys → `.env` |
| 4 | `uv run --extra observability python -m app.agent` → UI **http://localhost:8080/ui/** |
| 5 | Analyze in UI; inspect traces in Langfuse (`bom-agent-run`) |

- **User UI:** Summary, Key findings, Evidence, Supply chain map only.
- **Langfuse:** planner, tools, skills context, raw JSON — [observability.md](observability.md). **Demo verify & evaluate:** [demo-verification-and-evaluation.md](demo-verification-and-evaluation.md).
- **LiteLLM / Gemini:** [llm-gateway.md](llm-gateway.md).

Requires `BOM_REPO_ROOT` (defaults to cwd); agent loads `.env` on startup. Re-seed before first UI session if `data/` is empty.

### Remote agent API (summary)

- `GET /health`, `GET /v1/config` — readiness and `langfuse_configured` / `llm_configured`
- `POST /v1/agent/run` — user JSON (`explanation`, `findings`, `evidence`, `graph_view`); `mode`: `auto` | `tools` | `llm`

Details and curl examples: [local-demo-runbook.md](local-demo-runbook.md).

---

## Autonomous agent framework (`app/agent`)

- Loads Agent Skills from `skills/` into a system prompt (`build_system_prompt`).
- Executes deterministic tools via `ToolRegistry` (aligned with `bom-graph-explorer`).
- `BomAutonomousAgent.run()` supports:
  - `mode=tools` — heuristic planner (no API key)
  - `mode=llm` / `mode=auto` — OpenAI-compatible planner (`OPENAI_*` or `LLM_GATEWAY_*` → LiteLLM or direct OpenAI)
  - explicit `tool_calls` — fully deterministic remote control

Run commands: CLI demos and Docker + UI above. Requires seeded `data/` (see [Seeding](#seeding-synthetic-bom-data-ontology-validation)).
