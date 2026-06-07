# Project layout

Why the repository is structured the way it is: **organization boundaries** (who owns the data) versus **technical boundaries** (what must stay consistent for federation).

**Audience:** developers, architects, coding agents.

**Related:** 

* [enterprise-graph-design.md](enterprise-graph-design.md) (three logical graphs) 
* [graph-context.md](graph-context.md) (federation contract) 
* [federation-demo-runbook.md](federation-demo-runbook.md) (E2E domain federation demo)
* [testing-and-quality.md](testing-and-quality.md) (tests, lint, mypy)
* [development.md](development.md) (setup and roadmap) 
* [AGENTS.md](../AGENTS.md) (principles) · [agent-guide.md](agent-guide.md) (setup, seeding)

---

## 1. Design intent

Manufacturing supply-chain knowledge is owned by **different teams** with different systems and release cadences:

| Domain | Typical owner | Systems | Graph focus |
|--------|---------------|---------|-------------|
| **ebom** | Engineering | PLM | Product structure (`USED_IN`) |
| **routing** | Manufacturing | MES / ERP PP | Processes and work centers |
| **sourcing** | Procurement | SRM / ERP MM | Suppliers and supply risk |

Cross-domain questions (“which products are exposed if supplier X is disrupted?”) require **logical federation** at query time — not a single merged physical database owned by one team.

This repository therefore separates concerns into three layers:

```text
┌─────────────────────────────────────────────────────────────┐
│  ontology/     Technical boundary — shared schema & contract  │
│                (Pydantic + stdlib only; no Lance/FastAPI)   │
└───────────────────────────┬─────────────────────────────────┘
                            │ imported by
┌───────────────────────────▼─────────────────────────────────┐
│  domains/      Organization boundary — one slice per team   │
│                bundle + pipeline + (future) domain tools    │
└───────────────────────────┬─────────────────────────────────┘
                            │ writes / reads via
┌───────────────────────────▼─────────────────────────────────┐
│  app/          Shared runtime — storage, federation, agent  │
└─────────────────────────────────────────────────────────────┘
```

**Principles:**

1. **Domains do not share a monolithic codebase path** — each team’s ingest and metadata live under `domains/<name>/`.
2. **Federation consistency is centralized** — global node shapes, edge allow-lists, bridge keys, and join rules live in `ontology/` and `domains/registry.py`.
3. **The agent and stores are shared infrastructure** — cross-domain traversal, UI, and hybrid search sit in `app/`, not inside a single domain folder.
4. **Demo data is explicitly cross-domain** — synthetic fixtures that touch all three graphs live under `pipeline/demo/`, not inside one domain slice.

---

## 2. Top-level map

| Path | Boundary | Role |
|------|----------|------|
| [`ontology/`](../ontology/) | Technical | Global schema (`schema.py`), graph context contract, generated JSON export |
| [`domains/`](../domains/) | Organization | Per-team bundle, ingest pipeline, future domain tools |
| [`app/`](../app/) | Shared runtime | Lance stores, federation facade, hybrid store, agent server |
| [`pipeline/demo/`](../pipeline/demo/) | Demo only | Synthetic BOM fixtures and multi-domain seed orchestration |
| [`scripts/`](../scripts/) | Entrypoints | CLI: seed, per-domain ingest, sync, demos |
| [`skills/`](../skills/) | Distribution | Agent Skills (`bom-ontology`, `bom-graph-explorer`) |
| [`tests/`](../tests/) | Quality | Unit tests mirroring the layers above |
| [`docs/`](../docs/) | Documentation | Architecture, runbooks, this file |
| [`data/`](../data/) | Runtime (gitignored) | LanceDB domain graphs, vectors, DuckDB component master |
| [`config/`](../config/) | Ops | LiteLLM proxy config |

Python packages (see [`pyproject.toml`](../pyproject.toml)): `ontology`, `domains`, `pipeline`, `app`.

---

## 3. Layer details

### 3.1 `ontology/` — shared technical SSOT

Platform-independent. Depends only on **Pydantic** and the standard library.

```
ontology/
  schema.py                     Node/edge models, ALLOWED_EDGES, validate_node_payload()
  contract/
    graph_context.yaml          Bridge keys, federation joins, quality rules (no DB URIs)
  assets/
    ontology.json                 Generated — run scripts/sync_ontology.py
  README.md
```

| Edit here when… | Do not put here… |
|-----------------|------------------|
| A node type gains a field globally | LanceDB connection code |
| A new edge type is allowed everywhere | Agent tool names or playbooks |
| Federation join rules change (contract) | Team-specific ingest logic |

Domain partition rules (`DOMAIN_GRAPHS`, which graph owns which edge) live in **`domains/registry.py`**, not in `ontology/`.

See also: [graph-context.md](graph-context.md), [ontology/README.md](../ontology/README.md).

### 3.2 `domains/` — organization-owned slices

Each subdirectory is a **bounded context** one enterprise team can own and eventually extract to its own repository.

```
domains/
  registry.py                   graph_id → allowed nodes/edges; EDGE_TO_GRAPH, NODE_TO_GRAPHS
  bundle.py                     DomainBundle dataclass
  ebom/
    bundle.py                   owner_team, source_systems, allowed types
    pipeline.py                 PLM-shaped ingest (demo → pipeline/demo/sample_data.py)
    tools.py                    Domain exploration stubs (future)
  routing/
  sourcing/
  README.md
```

| Module | Owner concern |
|--------|---------------|
| `bundle.py` | Governance metadata — who owns the graph, which systems feed it |
| `pipeline.py` | How rows land in `data/lancedb/<graph_id>/` |
| `tools.py` | Domain-scoped read tools (e.g. `suppliers_by_countries`) |

**Import rules:** domains may import `ontology.schema`. Pipelines receive `LanceGraphStore` from `app` at runtime. Domains must **not** import `app.agent` or `skills/`.

Per-domain demo ingest: [`scripts/ingest/ebom.py`](../scripts/ingest/ebom.py) (and routing, sourcing).

See also: [domains/README.md](../domains/README.md).

### 3.3 `app/` — shared runtime and federation

```
app/
  storage/
    domain_store.py             DomainLanceGraphStore — one Lance path per graph_id
    lance_util.py
  federation/
    graph_store.py              LanceGraphStore facade — federates on Component.id / Product.id
    playbooks.yaml              Agent tool sequences (runtime; not in ontology contract)
  hybrid_store.py               DuckDB component master + Lance vectors
  exploration.py                Cross-domain exploration API
  tools.py                      Tool definitions for the agent
  graph_viz.py                  Unified subgraph for the UI
  agent/                        FastAPI server, LLM planner, web UI
```

| Component | Why shared |
|-----------|------------|
| `LanceGraphStore` | Cross-domain hops (supplier → component → product → process) |
| `hybrid_store.py` | `Component.id` master anchor across all graphs |
| `agent/` | One integration surface for Skills + tools + UI |

Playbooks reference tool names implemented in `app/`; federation **joins** are defined in `ontology/contract/graph_context.yaml`.

### 3.4 `pipeline/demo/` — cross-domain demo only

```
pipeline/demo/
  sample_data.py                SUPPLIERS, PRODUCTS, COMPONENT_BOM, …
  seed.py                       Calls domains.{ebom,routing,sourcing}.pipeline in order
```

Not a production ingest layer. Real PLM/MES/SRM connectors extend `domains/*/pipeline.py` or live in external repos that call the same store APIs.

Full demo seed: `uv run python scripts/seed_complex_bom.py --reset`

### 3.5 `skills/` — distributable agent packages

| Skill | Contents |
|-------|----------|
| `bom-ontology` | Generated `skills/bom-ontology/assets/ontology.json` (from `ontology/schema.py`) |
| `bom-graph-explorer` | Exploration workflows + optional Python CLI |

Skills are **language-neutral prompts and assets**. Validation runs in Python (`ontology/schema.py`), not inside Skill markdown.

Install path is user-chosen (Cursor, Claude Code, etc.) — see [skills/README.md](../skills/README.md).

### 3.6 `scripts/` — CLI entrypoints

| Script | Purpose |
|--------|---------|
| `seed_complex_bom.py` | All domains → `data/` |
| `ingest/{ebom,routing,sourcing}.py` | Single-domain demo ingest |
| `sync_ontology.py` | Regenerate `ontology.json` in ontology/assets and skills |
| `demo*.py` | Interactive exploration without HTTP server |

See [scripts/README.md](../scripts/README.md).

---

## 4. Runtime data layout

```
data/
  lancedb/
    ebom/                       graph_nodes, graph_edges (USED_IN)
    routing/                    INPUT_OF, PRODUCED_BY
    sourcing/                   SUPPLIED_BY
    component_vectors/          hybrid search index
  bom.duckdb                    component master (bridge for Component.id)
```

Physical separation matches organization boundaries. **Logical integration** happens in `app/federation/graph_store.py` at query time using shared IDs — see [enterprise-graph-design.md](enterprise-graph-design.md).

---

## 5. Dependency flow

```text
ontology/schema.py
       │
       ├──────────────────► domains/*/bundle.py
       │                    domains/registry.py
       │
       ├──────────────────► app/storage/domain_store.py  (validators on write)
       │
       └──────────────────► skills/bom-ontology/assets/ontology.json  (sync)

domains/*/pipeline.py ──► app/federation/graph_store.py ──► app/agent/
pipeline/demo/seed.py  ──► (orchestrates all domain pipelines)
```

**Forbidden:** `ontology/` importing `app/`, `domains/` importing `app.agent`, hand-editing generated `ontology.json`.

Guardrail: `tests/test_ontology_isolation.py` asserts `ontology/**/*.py` only imports Pydantic and stdlib.

---

## 6. Where to put a change

| You need to… | Edit |
|--------------|------|
| Add a field to `Component` everywhere | `ontology/schema.py` → `sync_ontology.py` |
| Restrict which graph may write `USED_IN` | `domains/registry.py`, `domains/ebom/bundle.py` |
| Add PLM export mapping for EBOM | `domains/ebom/pipeline.py` |
| Add supplier filter by country | `domains/sourcing/tools.py` + register in `app/tools.py` |
| Change cross-domain join rules | `ontology/contract/graph_context.yaml` |
| Change agent tool order for disruptions | `app/federation/playbooks.yaml` |
| Add synthetic demo parts | `pipeline/demo/sample_data.py` |
| Change Lance persistence | `app/storage/domain_store.py` |

---

## 7. Historical layout (removed)

These paths existed during earlier refactors and **are not present anymore**. If you see them in old notes or PRs, use the replacement:

| Removed | Replacement |
|---------|-------------|
| `bom_graph/` | Split into `ontology/`, `domains/`, `app/`, `pipeline/demo/` |
| `ontology/domains/` | `domains/` (top-level organization boundary) |
| `pipeline/ebom/`, `pipeline/routing/`, `pipeline/sourcing/` | `domains/*/pipeline.py` |
| `bom_graph/sample_bom.py` | `pipeline/demo/sample_data.py` |
| Playbooks inside `graph_context.yaml` | `app/federation/playbooks.yaml` |

There are **no empty legacy directories** left from these moves. Placeholder files that look minimal but are intentional:

- `domains/*/tools.py` — docstring stubs for future domain tools (roadmap P2/P3)
- `ontology/contract/__init__.py`, `pipeline/__init__.py` — package markers

---

## 8. Related documentation

| Topic | Document |
|-------|----------|
| Enterprise three-graph design | [enterprise-graph-design.md](enterprise-graph-design.md) |
| Graph context / federation contract | [graph-context.md](graph-context.md) |
| Disruption playbooks | [supply-chain-disruption-response.md](supply-chain-disruption-response.md) |
| Local demo | [local-demo-runbook.md](local-demo-runbook.md) |
| Federated domain demo (E2E) | [federation-demo-runbook.md](federation-demo-runbook.md) |
| Developer setup & roadmap | [development.md](development.md) |
| Tests, lint, static analysis | [testing-and-quality.md](testing-and-quality.md) |
| Agent / SSOT workflow | [AGENTS.md](../AGENTS.md) · [agent-guide.md](agent-guide.md) |
| Agent skill JSON catalogs & versioning | [agent-skill-assets.md](agent-skill-assets.md) |
| Demo verify & evaluate (UI vs Langfuse) | [demo-verification-and-evaluation.md](demo-verification-and-evaluation.md) |
