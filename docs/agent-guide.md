# Agent guide

Detailed setup, seeding, demos, autonomous agent runtime, and **repository terminology** for coding agents and developers.

**Audience:** coding agents, contributors.

**Related:** [AGENTS.md](../AGENTS.md) (principles and done criteria) · [development.md](development.md) · [demo-runbook.md](demo-runbook.md) · [graph-contract.md](graph-contract.md) · [graph-context.md](graph-context.md) · [testing-and-quality.md](testing-and-quality.md) · [project-layout.md](project-layout.md)

---

## Terminology

**SSOT for names** used across docs, code comments, and PRs. Deep dives: [graph-contract.md](graph-contract.md) (Graph Contract design) · [graph-context.md](graph-context.md) (`graph-context.json` usage).

### Quick rules

| If you are talking about… | Say | Do not say |
|---------------------------|-----|------------|
| Federation **agreement** (Bridge Keys, who owns which edge, join rules, quality gates, SLA) | **Graph Contract** | graph context, federation contract |
| Agent **prompt bundle** (domain scopes + bridges exported for Skills) | **graph context** | Graph Contract, contract file |
| **Instance data** in Neo4j (`SUP-002`, `COMP-101`, …) | **graph data** / **domain graph** | graph context |
| **UI/API subgraph** (`nodes[]`, `edges[]` for one run) | **`graph_view`** | graph context, Graph Contract |

**Contract** talk → **Graph Contract**. **Context** talk → **graph context**. Do not rename context artifacts to “contract,” and do not call the contract bundle “graph context” in prose.

### What each is (and is not)

| | **Graph Contract** | **graph context** | **`graph_view`** (related) |
|--|-------------------|-------------------|----------------------------|
| **Role** | Cross-team **agreement** and validation SSOT | **Runtime context** for agents composing Cypher / choosing `graph_id` | **Ephemeral subgraph** for one analysis |
| **Primary file** | `ontology/contract/graph_context.yaml` | `skills/bom-graph-explorer/assets/graph-context.json` | Built in memory; returned in API JSON |
| **Structure** | YAML manifest (identity, domains, joins, quality) | JSON bundle (`identity`, `domains`, `federation`) | `{ nodes[], edges[] }` — actual graph fragment |
| **Graph instance data?** | **No** — rules and scopes | **No** — type-level domain scopes; not Neo4j rows | **Yes** — supplier/component/product nodes and edges |
| **Typical consumers** | Ingest pipelines, audit jobs, governance | `bom-graph-explorer` Skill, agent system prompt | Web UI map, `/v1/agent/run` response |
| **Edited by** | Data governance / platform (hand-authored YAML) | Generated only (`domains/export.py` → `sync_ontology.py`) | Computed per request (`app/graph_viz.py`) |
| **Detail doc** | [graph-contract.md](graph-contract.md) | [graph-context.md](graph-context.md) | [demo-runbook.md](demo-runbook.md) |

Neither the Graph Contract nor `graph-context.json` is a graph in the database sense. Both describe **how graphs may be split, typed, and joined**. Only Neo4j rows and `graph_view` hold **instance-level** nodes and edges.

```text
  Graph Contract (YAML)          graph context (JSON)         graph data (Neo4j)
  ─ agreement & gates      ─►    ─ agent scope bundle    ─►   ─ SUP-002, COMP-101, …
        │                              │                           │
        └──────── sync / derive ───────┘                           │
                                                                   ▼
                                                            graph_view (UI slice)
```

### Naming map (concept vs files)

| Concept | Path |
|---------|------|
| **Ontology** (global shapes) | `ontology/schema.py` → `ontology.json` |
| **Graph Contract** (authoring SSOT) | `ontology/contract/graph_context.yaml` |
| **graph context** (Skill export) | `skills/bom-graph-explorer/assets/graph-context.json` |
| **Terminology** (this section) | `docs/agent-guide.md` |
| Graph Contract design guide | `docs/graph-contract.md` |
| Graph context usage guide | `docs/graph-context.md` |

Historical filenames: YAML uses `graph_context`; JSON uses `graph-context`. **Concept names** follow Contract vs context above — filenames are not renamed.

### When to use which term

| Situation | Use | Example phrasing |
|-----------|-----|------------------|
| Changing Bridge Keys or federation join paths | **Graph Contract** | “Update the Graph Contract `federation.joins` for supplier disruption.” |
| Ingest rejecting a cross-domain edge | **Graph Contract** | “`GraphContract.validate_edge` failed — edge not in domain scope.” |
| Documenting owner team / SLA / quality gates | **Graph Contract** | “Sourcing `sla_hours` in the Graph Contract.” |
| Agent Skill loading domain allow-lists into the prompt | **graph context** | “Embed `graph-context.json` in the explorer Skill.” |
| Cypher compose: which edges exist under `sourcing` | **graph context** | “Check `graph-context.json` → `domains.sourcing.edges`.” |
| Code export function / test name | **graph context** (keep identifiers) | `export_graph_context_bundle()`, `test_graph_context_domains_match_registry` |
| Explaining federation to architects (Zenn / design) | **Graph Contract** | “Bridge Keys are part of the Graph Contract.” |
| API field with nodes and edges for the map | **`graph_view`** | “`graph_view.node_count` must be ≥ 1.” |
| Confusing contract with instance data | **Avoid** | ~~“Load the graph context into Neo4j.”~~ → “Seed Neo4j from the demo pipeline; agents read **graph context** for scope.” |

### Contents by layer (what lives where)

| Content | Graph Contract (YAML) | graph context (JSON) | Neo4j / `graph_view` |
|---------|:---------------------:|:--------------------:|:--------------------:|
| Bridge Keys (`Component.id`, …) | ✓ `identity.bridges` | ✓ `identity.bridges` | ✓ instance IDs |
| Allowed node/edge **types** per domain | ✓ `domains` | ✓ `domains` | ✓ typed nodes/edges |
| Federation join **definitions** | ✓ `federation.joins` (full steps) | ✓ `federation.joins` (recipe names) | — |
| Quality gates / SLA | ✓ `quality`, `sla_hours` | — | — |
| Owner team metadata | ✓ `owner_team` | — | — |
| Tool playbooks | — (see `playbooks.yaml`) | — | — |
| Supplier/product **rows** | — | — | ✓ |

### Related terms (do not conflate)

| Term | Meaning |
|------|---------|
| **Ontology** | Global node/edge **shapes** and validators (`ontology/schema.py`, `ontology.json`) |
| **Data contract** | Single-dataset guarantees ([datacontract.com](https://datacontract.com/) style) — analogous, not identical to Graph Contract |
| **Domain graph** | One `graph_id` slice of instance data in Neo4j (`sourcing`, `ebom`, `routing`) |
| **Bridge Key** | Shared ID field (e.g. `Component.id`) defined **in** the Graph Contract |
| **graph context** | Agent-facing **scope bundle** — [graph-context.md](graph-context.md) |
| **Graph Contract** | Cross-domain federation **agreement** — [graph-contract.md](graph-contract.md) |

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
| Federation demo | `uv run python scripts/demo_federation.py --reset` | Per-domain seed, validate, query, federated mitigations — [demo-runbook.md](demo-runbook.md#part-a--federation-cli-no-docker--llm) |
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

**Human runbook:** [demo-runbook.md](demo-runbook.md) · **Developer setup:** [development.md](development.md) · **Terminology:** [agent-guide.md § Terminology](agent-guide.md#terminology) · **Graph Contract:** [graph-contract.md](graph-contract.md) · **Graph context:** [graph-context.md](graph-context.md) · **Enterprise graph design:** [enterprise-graph-design.md](enterprise-graph-design.md) · **Disruption response:** [supply-chain-disruption-response.md](supply-chain-disruption-response.md)

| Step | What |
|------|------|
| 1 | `uv sync --extra observability --extra gateway`, configure `.env`, start Neo4j if needed, `seed_complex_bom.py --reset` |
| 2 | `./scripts/start_stack.sh` → LiteLLM `:4000`, Langfuse `:3000`, Neo4j `:7687` |
| 3 | Langfuse UI → API keys → `.env` |
| 4 | `uv run --extra observability python -m app.agent` → UI **http://localhost:8080/ui/** |
| 5 | Analyze in UI; inspect traces in Langfuse (`bom-agent-run`) |

- **User UI:** Summary, Key findings, Evidence, Supply chain map only.
- **Langfuse:** planner, tools, skills context, raw JSON — [observability.md](observability.md). **Demo verify & evaluate:** [demo-runbook.md](demo-runbook.md#part-d--verification--evaluation).
- **LiteLLM / Gemini:** [llm-gateway.md](llm-gateway.md).

Requires `BOM_REPO_ROOT` (defaults to cwd); agent loads `.env` on startup. Re-seed before first UI session if `data/` is empty.

### Remote agent API (summary)

- `GET /health`, `GET /v1/config` — readiness and `langfuse_configured` / `llm_configured`
- `POST /v1/agent/run` — user JSON (`explanation`, `findings`, `evidence`, `graph_view`); `mode`: `auto` | `tools` | `llm`

Details and curl examples: [demo-runbook.md](demo-runbook.md).

---

## Autonomous agent framework (`app/agent`)

- Loads Agent Skills from `skills/` into a system prompt (`build_system_prompt`).
- Executes deterministic tools via `ToolRegistry` (aligned with `bom-graph-explorer`).
- `BomAutonomousAgent.run()` supports:
  - `mode=tools` — heuristic planner (no API key)
  - `mode=llm` / `mode=auto` — OpenAI-compatible planner (`OPENAI_*` or `LLM_GATEWAY_*` → LiteLLM or direct OpenAI)
  - explicit `tool_calls` — fully deterministic remote control

Run commands: CLI demos and Docker + UI above. Requires seeded `data/` (see [Seeding](#seeding-synthetic-bom-data-ontology-validation)).
