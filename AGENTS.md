# AGENTS.md

High-level guide for agents working in this repository.

## 1. Core Working Principles

- **Language:** Repository docs (`*.md`, `docs/`), docstrings, inline comments, and user-facing error messages are **English**. Skill prompts may stay language-neutral; do not add Japanese (or other locale) strings in Python unless there is an explicit i18n requirement.
- **Authoring SSOT:** `ontology/schema.py` (Pydantic). The `ontology/` tree depends only on Pydantic and stdlib — no LanceDB, FastAPI, or agent imports.
- **Published ontology SSOT:** `skills/bom-ontology/assets/ontology.json` (single generated file).
- **Graph context contract:** `ontology/contract/graph_context.yaml` (cross-domain federation rules).
- **All Agent Skills** live under `skills/` (`bom-ontology`, `bom-graph-explorer`).
- Regenerate ontology and explorer assets: `uv run python scripts/sync_ontology.py`.
- Workflow skills must not embed a second copy of `ontology.json`.
- No tool-specific install copies under `.cursor/skills/`.

## 2. Key Components

| Layer | Location | Role |
|-------|----------|------|
| Layout guide | [docs/project-layout.md](docs/project-layout.md) | Why `ontology/`, `domains/`, `app/` exist |
| Ontology | `ontology/` | Platform-independent shared schema + graph context contract (Pydantic only) |
| Domains | `domains/` | Org-owned slices: bundle, pipeline, tools per `ebom` / `routing` / `sourcing` |
| Pipeline | `pipeline/demo/` | Cross-domain demo fixtures and seed orchestration |
| Application | `app/` | Storage, federation facade, hybrid store, cross-domain tools, agent |
| Ontology skill | `skills/bom-ontology/` | Distributable schema for agents (`skills/bom-ontology/assets/ontology.json`) |
| Exploration skill | `skills/bom-graph-explorer/` | Cypher compose protocol + generated `graph-context.json`, `query-catalog.json`, `cypher-engine-profile.json` |

## 3. Ontology vs validation vs exploration

| Concern | Where it lives | Notes |
|---------|----------------|-------|
| **What is allowed** (schema) | `bom-ontology` skill + `ontology/schema.py` | One `ontology.json`; skill is language-neutral |
| **Whether data complies** (validation) | `ontology/schema.py` (Pydantic) | Deterministic; runs in pipelines/tests, not in Skill code |
| **How to explore the graph** | `bom-graph-explorer` skill + `app/` stores | Read-only traversal tools |

A separate **`bom-validate` Agent Skill is not required** for the default setup: writes already go through Pydantic validators (`validate_node_payload`, `RelationEdge`). Add `skills/bom-validate/` only if you need a portable **audit playbook** for agents without the Python package (checklist + violation report format, still reading `bom-ontology`).

Install skills from `skills/` only. Do not copy them into `.cursor/skills/` inside this repository.

## 4. Seeding synthetic BOM data (ontology validation)

Demo and agent runtime need graph, vector, and RDB data under `data/`. **Do not hand-edit LanceDB/DuckDB files.** Load synthetic BOM through the Python stores so every node and edge is validated against the ontology defined in `ontology/schema.py`.

### 4.1 One definition, two consumers (not two competing schemas)

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

### 4.2 What gets validated on each write

```
scripts/seed_complex_bom.py
        │
        ▼
pipeline/demo/seed.py  (orchestrates domain pipelines)
pipeline/demo/sample_data.py  (suppliers, products, processes, components, edges)
        │
        ├── graph.add_node(type, payload)  → validate_node_payload()  (per node type)
        ├── graph.add_edge(payload)        → RelationEdge  (allowed source/target pairs)
        └── unified.upsert_component(...)  → ComponentNode + graph node
```

| Write API | Validator | Typical failure |
|-----------|-----------|-----------------|
| `LanceGraphStore.add_node` | `validate_node_payload` | Missing field, wrong type, bad `country` length |
| `LanceGraphStore.add_edge` | `RelationEdge` | Disallowed edge (e.g. `Product → Component` for `USED_IN`) |
| `UnifiedBomContextStore.upsert_component` | `ComponentNode` | Invalid component attributes |

Invalid rows raise `pydantic.ValidationError` or `ValueError`; nothing is partially committed for that failed call. Fix `pipeline/demo/sample_data.py` (or your own loader that calls the same APIs), not the binary DB files.

### 4.3 Commands (from repository root)

```bash
uv sync

# After editing ontology/schema.py only (Skills / prompts):
uv run python scripts/sync_ontology.py

# Load synthetic BOM into data/lancedb + data/bom.duckdb (validated writes):
uv run python scripts/seed_complex_bom.py --reset
```

| Flag / path | Meaning |
|-------------|---------|
| `--reset` | Delete `data/lancedb` and `data/bom.duckdb` before insert (avoids duplicate nodes on re-run) |
| `--lancedb-path` | Default `data/lancedb` |
| `--duckdb-path` | Default `data/bom.duckdb` |

Default dataset (`seed_complex_bom` in `pipeline/demo/`): **3 suppliers**, **3 products**, **4 processes**, **12 components**, with shared parts, multiple suppliers, and `SUPPLIED_BY` / `USED_IN` / `INPUT_OF` / `PRODUCED_BY` edges.

### 4.4 Customize or extend the dataset

1. Edit **`pipeline/demo/sample_data.py`** (`SUPPLIERS`, `PRODUCTS`, `PROCESSES`, `COMPONENT_BOM`, `PRODUCT_PROCESSES`).
2. Stay within allowed node types and edge pairs (see `ALLOWED_EDGES` in `schema.py` or `ontology.json`).
3. Re-seed with `--reset`:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

`scripts/demo*.py` also call `seed_complex_bom()` but do not pass `--reset`; prefer the dedicated seed script when refreshing demo data before UI or API work.

### 4.5 Verify after seeding

```bash
uv run python scripts/seed_complex_bom.py --reset
uv run pytest -q tests/test_schema.py tests/test_lance_graph_store.py tests/test_hybrid_store.py

# Quick exploration (also seeds if --seed):
uv run python skills/bom-graph-explorer/scripts/explore_graph.py --seed \
  --mode supplier-impact --supplier-id SUP-002
```

Then start demos (§5.3) or the full stack (§5.4) against the same `data/` paths.

## 5. Setup, Agent Skill install, and demos

### 5.1 Python environment (repo checkout)

```bash
cd /path/to/bom-knowledge-graph-agent-skill
uv sync
uv run python scripts/sync_ontology.py      # after schema.py changes
uv run python scripts/seed_complex_bom.py --reset   # validated synthetic BOM
```

### 5.2 Install Agent Skills (user-chosen agent host)

Skill sources live under `skills/`. The install path on disk is chosen by the user (Cursor, Claude Code, CLI agent, etc.).

```bash
# Replace <source> with this repo path or git URL
npx skils add <source> --path skills/bom-ontology
npx skils add <source> --path skills/bom-graph-explorer
```

Install **bom-ontology** first (schema). **bom-graph-explorer** depends on it for exploration workflows.

This repository does not commit tool-specific copies under `.cursor/skills/`.

### 5.3 Demos (Python runtime in this repo)

| Script | Command | What it shows |
|--------|---------|----------------|
| Graph + tools | `uv run python scripts/demo.py` | Interactive graph exploration |
| Hybrid | `uv run python scripts/demo_hybrid.py` | Vector → RDB → graph (`LANCEDB_PATH` optional) |
| Agent (local) | `uv run python scripts/demo_agent.py` | Agent Skills + tool run |
| Federation demo | `uv run python scripts/demo_federation.py --reset` | Per-domain seed, validate, query, federated mitigations — [docs/federation-demo-runbook.md](docs/federation-demo-runbook.md) |
| Skill CLI | `uv run python skills/bom-graph-explorer/scripts/explore_graph.py --seed --mode supplier-impact --supplier-id SUP-001` | Exploration without HTTP server |

Non-interactive: `DEMO_NONINTERACTIVE=1 uv run python scripts/demo.py`

All under `scripts/` — see [scripts/README.md](scripts/README.md). Demos call `seed_complex_bom()`; use §4.3 `--reset` first for a clean `data/` tree.

Example hybrid run:

```bash
export LANCEDB_PATH=data/lancedb
uv run python scripts/demo_hybrid.py
```

### 5.4 Local full stack (LiteLLM + Langfuse + agent UI)

**Human runbook:** [docs/local-demo-runbook.md](docs/local-demo-runbook.md) · **Developer setup:** [docs/development.md](docs/development.md) · **Enterprise graph design:** [docs/enterprise-graph-design.md](docs/enterprise-graph-design.md) · **Ontology on Lance:** [docs/ontology-on-lance.md](docs/ontology-on-lance.md) · **Disruption response:** [docs/supply-chain-disruption-response.md](docs/supply-chain-disruption-response.md)

| Step | What |
|------|------|
| 1 | `uv sync --extra observability --extra gateway`, configure `.env`, `seed_complex_bom.py --reset` |
| 2 | `./scripts/run_docker_stack.sh -d` → LiteLLM `:4000`, Langfuse `:3000` |
| 3 | Langfuse UI → API keys → `.env` |
| 4 | `uv run --extra observability python -m app.agent` → UI **http://localhost:8080/ui/** |
| 5 | Analyze in UI; inspect traces in Langfuse (`bom-agent-run`) |

- **User UI:** Summary, Key findings, Evidence, Supply chain map only.
- **Langfuse:** planner, tools, skills context, raw JSON — [docs/observability.md](docs/observability.md). **Demo verify & evaluate:** [docs/demo-verification-and-evaluation.md](docs/demo-verification-and-evaluation.md).
- **LiteLLM / Gemini:** [docs/llm-gateway.md](docs/llm-gateway.md).

Requires `BOM_REPO_ROOT` (defaults to cwd); agent loads `.env` on startup. Re-seed with §4.3 before first UI session if `data/` is empty.

### 5.5 Remote agent API (summary)

- `GET /health`, `GET /v1/config` — readiness and `langfuse_configured` / `llm_configured`
- `POST /v1/agent/run` — user JSON (`explanation`, `findings`, `evidence`, `graph_view`); `mode`: `auto` \| `tools` \| `llm`

Details and curl examples: [docs/local-demo-runbook.md](docs/local-demo-runbook.md).

## 6. Autonomous agent framework (`app/agent`)

- Loads Agent Skills from `skills/` into a system prompt (`build_system_prompt`).
- Executes deterministic tools via `ToolRegistry` (aligned with `bom-graph-explorer`).
- `BomAutonomousAgent.run()` supports:
  - `mode=tools` — heuristic planner (no API key)
  - `mode=llm` / `mode=auto` — OpenAI-compatible planner (`OPENAI_*` or `LLM_GATEWAY_*` → LiteLLM or direct OpenAI)
  - explicit `tool_calls` — fully deterministic remote control

Run commands: §5.3 (CLI demos), §5.4 (Docker + UI). Requires seeded `data/` (§4).

## 7. Change Workflow

1. Edit `ontology/schema.py`.
2. Run `uv run python scripts/sync_ontology.py`.
3. Update skill docs if workflows changed.
4. `uv run pytest -q`.

## 8. Unit Test Commands

See [docs/testing-and-quality.md](docs/testing-and-quality.md) for pytest, ruff, mypy, and PR checklists.

```bash
uv sync
uv run pytest -q
```

## 9. Done Criteria

- One `ontology.json` under `skills/bom-ontology/assets/`.
- `uv run pytest -q` succeeds.
