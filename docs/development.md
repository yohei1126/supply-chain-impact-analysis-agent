# Development guide

Setup, project layout, seeding, CLI demos, tests, and the **implementation roadmap** for three domain graphs with agent-driven logical federation. For the full LiteLLM + Langfuse + web UI flow, see [local-demo-runbook.md](local-demo-runbook.md). For agent/automation conventions, see [AGENTS.md](../AGENTS.md).

**Architecture references:** [project-layout.md](project-layout.md) · [federation-demo-runbook.md](federation-demo-runbook.md) · [testing-and-quality.md](testing-and-quality.md) · [enterprise-graph-design.md](enterprise-graph-design.md) · [graph-context.md](graph-context.md) · [supply-chain-disruption-response.md](supply-chain-disruption-response.md) · [ontology-on-lance.md](ontology-on-lance.md)

## Ontology (single source of truth)

```
ontology/schema.py                          ← edit constraints (Pydantic)
        │
        ▼  uv run python scripts/sync_ontology.py
skills/bom-ontology/assets/ontology.json     ← published artifact for Agent Skills
```

- **Authoring:** only change `ontology/schema.py`.
- **Skills:** read generated `ontology.json`; do not hand-edit it.
- **Runtime writes:** Pydantic validators on every graph/RDB/vector insert.

After `schema.py` changes:

```bash
uv run python scripts/sync_ontology.py
uv run pytest -q tests/test_skill_ontology_asset.py
```

Seeding and validation details: [AGENTS.md](../AGENTS.md) §4.

### Ontology layers (target)

LanceDB is schema-light; meaning and integrity live above storage ([ontology-on-lance.md](ontology-on-lance.md)):

| Layer | Location (today → target) |
|-------|---------------------------|
| Schema + constraints | `ontology/schema.py` |
| Domain partition | `domains/registry.py`, `domains/*/bundle.py` |
| Published JSON Schema | `skills/bom-ontology/assets/ontology.json` |
| Graph context contract | `ontology/contract/graph_context.yaml` — see [graph-context.md](graph-context.md) |
| Federation facade | `app/federation/graph_store.py` |
| Semantics glossary (planned) | `skills/bom-ontology/references/semantics.md` |

## Current state (P0)

What ships today:

| Area | Status | Notes |
|------|--------|-------|
| Three domain Lance graphs | Done | `data/lancedb/{ebom,routing,sourcing}/` via `LanceGraphStore` facade |
| Component master + vector | Done | `data/bom.duckdb`, `component_vectors` |
| Tools | Done | `bom_supplier_impact`, `bom_supply_path`, `bom_hybrid_query` |
| Agent + UI | Done | `POST /v1/agent/run` with `goal`; heuristic + optional LLM planner |
| Disruption from news | Partial | Unstructured `goal` works with LLM mode; no `interpret_disruption` yet |
| Three physical graphs | Done | `data/lancedb/{ebom,routing,sourcing}/` |
| Federation store | Partial | Cross-domain hops via `LanceGraphStore` facade |
| Routing impact tools | Not started | `Process` data seeded; no `work_center_impact` tool |

Primary disruption input is **natural-language `goal`** (e.g. news headline), not graph-native IDs — see [supply-chain-disruption-response.md](supply-chain-disruption-response.md) §4.2.

## Development roadmap

Phased plan aligned with enterprise design docs. **Logical federation first**; physical Lance split when ingest ownership requires it.

```text
P0 ──► P1 ──► P2 ──► P3 ──► P4 ──► P5
done   interpret  sourcing  domain    federation  connectors
       + news     filters   split +   + multi-
                routing     round
                tools       planner
```

### P0 — Unified demo (baseline) ✅

**Goal:** Prove hybrid search, graph traversal, and agent UX on one Lance dataset.

| Deliverable | Location |
|-------------|----------|
| Ontology SSOT + sync | `ontology/schema.py`, `scripts/sync_ontology.py` |
| Graph store | `app/federation/graph_store.py`, `app/storage/domain_store.py` |
| Hybrid pipeline | `app/hybrid_store.py` |
| Exploration tools | `app/tools.py`, `app/exploration.py` |
| Agent server + UI | `app/agent/` |
| Seed data | `pipeline/demo/`, `scripts/seed_complex_bom.py` |
| Skills | `skills/bom-ontology/`, `skills/bom-graph-explorer/` |

**Tests:** `tests/test_schema.py`, `test_lance_graph_store.py`, `test_hybrid_store.py`, `test_agent.py`

**Exit criteria:** `uv run pytest -q` green; UI shows summary / findings / evidence / map for `SUP-xxx` and hybrid queries.

---

### P1 — News interpretation and planning

**Goal:** Accept unstructured disruption news; produce hypotheses; drive tool selection without inventing graph IDs.

| Deliverable | Proposed location | Notes |
|-------------|-------------------|-------|
| Interpretation schema | `app/agent/disruption.py` | Pydantic `DisruptionHypothesis` (class, geo, materials, confidence) |
| Interpret step | `app/agent/llm_client.py` or dedicated `interpret_disruption` | Logged to Langfuse |
| Geo gazetteer | `skills/bom-disruption-response/references/gazetteer.md` | Hormuz → country codes; Skill-only, no duplicate ontology |
| Planner wiring | `app/agent/runner.py` | `disruption_class` → playbook template |
| Playbook registry | `app/federation/playbooks.yaml` | Maps class → ordered tool names |
| Skill package | `skills/bom-disruption-response/` | Workflows + gazetteer |

**Tests to add:**

- `tests/test_disruption_interpret.py` — fixture headlines → valid hypothesis JSON (mock LLM or golden parser)
- `tests/test_playbook_registry.py` — `maritime_chokepoint` resolves to expected tool sequence
- Extend `tests/test_agent.py` — goal with Hormuz text plans sourcing-first tools when LLM mocked

**Exit criteria:** `POST /v1/agent/run` with Hormuz-style `goal` runs interpretation + at least one sourcing filter tool (or documented widen fallback); Langfuse shows interpretation span.

**Depends on:** P0. **Enables:** P2 geo filters.

---

### P2 — Sourcing graph tools and enrichments

**Goal:** Anchor news hypotheses to suppliers and components in the graph.

| Deliverable | Proposed location | Notes |
|-------------|-------------------|-------|
| `suppliers_by_countries` | `app/exploration.py` + tool def | Filter `Supplier.country` |
| `suppliers_by_risk` | same | Filter `risk_level` |
| `components_by_suppliers` | same | `SUPPLIED_BY` reverse traverse |
| `supply_status` | same | Lead time + single-source flags |
| Lane metadata (optional) | `schema.py` edge props + seed | `shipping_lane`, `primary_port` on `SUPPLIED_BY` |
| Domain bundle export | `domain-bundles.json` via sync script | Sourcing-only edge allow-list |

**Seed / demo:** Extend `pipeline/demo/sample_data.py` with at least one Gulf-region supplier **or** document demo widen path to `risk_level=High` ([supply-chain-disruption-response.md](supply-chain-disruption-response.md) §8.1).

**Tests to add:**

- `tests/test_sourcing_tools.py` — country and risk filters on seeded data
- Schema tests if new edge properties added

**Exit criteria:** Playbook `maritime_chokepoint` step 1–2 pass deterministically in `mode=tools` with seeded widen rules.

**Depends on:** P1 playbooks. **Parallel with:** early P3 schema comments for domains.

---

### P3 — Domain separation and routing tools

**Goal:** Three logical graphs on Lance (via `graph_id` or separate paths); EBOM and routing tools for federation hops.

**Status:** Domain separation **done** — `data/lancedb/{ebom,routing,sourcing}/` with federated `LanceGraphStore` facade. Routing-specific exploration tools still pending.

| Deliverable | Proposed location | Notes |
|-------------|-------------------|-------|
| Domain graph definitions | `domains/registry.py`, `domains/*/bundle.py` | **Done** |
| Per-domain Lance store | `app/storage/domain_store.py` | **Done** |
| Federated facade | `app/federation/graph_store.py` | **Done** — external API unchanged |
| `graph_id` on Lance rows | domain store rows | **Done** (`graph_id` column) |
| Migration script | `scripts/migrate_graph_domains.py` | Not needed when using `--reset` seed |
| Domain-scoped traversal | domain stores | **Done** — edge type enforced per domain |
| EBOM tools | `ebom.products_by_components`, `ebom.where_used` | Pending |
| Routing tools | `routing.processes_by_components`, `routing.products_by_work_center` | Pending |
| Separate Lance paths (optional) | `data/lancedb-{ebom,routing,sourcing}/` | Using subdirs under `data/lancedb/` |

**Tests to add:**

- `tests/test_domain_traversal.py` — reject `USED_IN` under `graph_id=sourcing`
- `tests/test_routing_tools.py` — work center impact on seed data
- Update `test_lance_graph_store.py` for `graph_id`

**Exit criteria:** Seed writes three domain slices; supplier disruption playbook uses sourcing + ebom stores explicitly; routing hop returns processes for affected components.

**Depends on:** P2 sourcing tools (for end-to-end playbooks). See migration steps in [enterprise-graph-design.md](enterprise-graph-design.md) §10.

---

### P4 — Federation layer and multi-round agent

**Goal:** Logical graph integration at query time; replan after tool JSON; mitigations in response.

| Deliverable | Proposed location | Notes |
|-------------|-------------------|-------|
| `GraphFederationStore` | `app/federation/composer.py` | Join on `Component.id`, `Product.id` |
| Impact scoring | `app/federation/impact.py` | Deterministic formula (§6.3 in disruption doc) |
| Multi-round planner | `app/agent/runner.py` | Max rounds, stop rules |
| Unified `graph_view` | `app/graph_viz.py` | Federated subgraph for UI |
| Mitigation templates | `app/federation/mitigations.py` | Owner-tagged actions from tool data |
| `federation.yaml` | Skill or `app/federation/` | Join rules for agents |
| Optional API | `POST /v1/agent/incident` | Derived envelope + extra response fields |

**Tests to add:**

- `tests/test_federation.py` — multi-store join matches single-graph baseline where comparable
- `tests/test_agent_multiround.py` — empty country filter triggers widen plan (mocked LLM)
- `tests/test_mitigations.py` — output cites only IDs present in tool JSON

**Exit criteria:** Full `maritime_chokepoint` and `supplier_disruption` playbooks run multi-hop across domain stores; response includes `impact_score` and mitigations; Langfuse traces plan rounds.

**Depends on:** P3 domain stores and tools.

---

### P5 — Enterprise connectors (out of repo core)

**Goal:** Replace synthetic seed with team-owned ingest pipelines.

| Connector | Target graph | Validates against |
|-----------|--------------|-------------------|
| PLM → EBOM | `lancedb-ebom` | `DOMAIN_GRAPHS["ebom"]` |
| MES/ERP → routing | `lancedb-routing` | `DOMAIN_GRAPHS["routing"]` |
| SRM → sourcing | `lancedb-sourcing` | `DOMAIN_GRAPHS["sourcing"]` |
| News / alerts | Agent `goal` or `context.raw_text` | P1 interpretation |

Keep connectors **outside** `app/` core or behind `scripts/ingest/` adapters so `uv run pytest -q` stays offline-friendly.

**Exit criteria:** Documented adapter contract; at least one sample ingest script per domain in `scripts/ingest/`.

---

### Roadmap summary

| Phase | Focus | Key outcome |
|-------|-------|-------------|
| **P0** ✅ | Unified demo | Agent + tools + UI on one Lance graph |
| **P1** | Interpretation | News `goal` → hypotheses → playbook |
| **P2** | Sourcing tools | Geo / risk filters; lane metadata |
| **P3** | Domain split | `graph_id` or 3 Lance paths + routing tools |
| **P4** | Federation | `GraphFederationStore`, multi-round planner, mitigations |
| **P5** | Connectors | PLM / MES / SRM / news adapters |

### Suggested implementation order (files)

1. `app/federation/playbooks.yaml` + tests (P1, no Lance migration yet)
2. `app/exploration.py` sourcing filters (P2)
3. `domains/registry.py` + `graph_id` in `app/storage/domain_store.py` (P3)
4. `app/federation/composer.py` (P4)
5. `skills/bom-disruption-response/` (P1–P4 prompts and gazetteer)

Do not skip tests when adding tools — agent behavior is regression-prone.

## Project layout

Full directory structure, boundaries, and “where to put a change” guide: **[project-layout.md](project-layout.md)**.

Quick reference:

```
ontology/          shared schema + contract (Pydantic only)
domains/           org-owned ebom | routing | sourcing slices
pipeline/demo/     cross-domain synthetic seed
app/               storage, federation, agent
skills/            distributable Agent Skills
scripts/           CLI entrypoints
data/lancedb/      runtime LanceDB (ebom, routing, sourcing)
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

Default seeded BOM: **3 suppliers**, **3 products**, **4 processes**, **12 components** (`pipeline/demo/sample_data.py`).

| Path | Role |
|------|------|
| `data/lancedb` | Vector table (`component_vectors`) |
| `data/lancedb/ebom` | EBOM domain graph (`USED_IN`) |
| `data/lancedb/routing` | Routing domain graph (`INPUT_OF`, `PRODUCED_BY`) |
| `data/lancedb/sourcing` | Sourcing domain graph (`SUPPLIED_BY`) |
| `data/bom.duckdb` | Component master (cross-graph ID anchor) |

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

**Federated domain demo (recommended first):** per-domain generate → validate → load → query → federate → mitigations — [federation-demo-runbook.md](federation-demo-runbook.md).

```bash
uv run python scripts/demo_federation.py --reset
```

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
uv run python -m app.agent
# http://localhost:8080/ui/
```

With LLM and Langfuse, use [local-demo-runbook.md](local-demo-runbook.md).

### API smoke test

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8080/v1/config

# P0: ID-shaped disruption (heuristic planner)
curl -s -X POST http://localhost:8080/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Analyze supplier impact for SUP-002","mode":"tools"}'

# P1 target: unstructured news (requires LLM / mode auto or llm)
curl -s -X POST http://localhost:8080/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Strait of Hormuz closure reported — what is our supply chain exposure?","mode":"auto"}'
```

User-facing response fields: `explanation`, `findings`, `evidence`, `graph_view`. P4 adds `impact_score`, `mitigations`, and Langfuse-logged `interpretation` (not in UI).

## Docker services

Single file: `docker-compose.yml` with profiles `litellm` and `langfuse`.

```bash
./scripts/run_docker_stack.sh -d    # both profiles
docker compose --profile langfuse up -d
docker compose --profile litellm up -d
```

Requires Docker (or Colima: `colima start`). See [observability.md](observability.md) and [llm-gateway.md](llm-gateway.md).

## Tests

See **[testing-and-quality.md](testing-and-quality.md)** for the full guide (pytest, ruff, mypy, PR checklist).

```bash
uv sync
uv run pytest -q
```

Targeted (P0):

```bash
uv run pytest -q tests/test_schema.py
uv run pytest -q tests/test_lance_graph_store.py
uv run pytest -q tests/test_hybrid_store.py
uv run pytest -q tests/test_agent.py
```

Planned by phase:

| Phase | Test module |
|-------|-------------|
| P1 | `tests/test_disruption_interpret.py`, `tests/test_playbook_registry.py` |
| P2 | `tests/test_sourcing_tools.py` |
| P3 | `tests/test_domain_traversal.py`, `tests/test_routing_tools.py` |
| P4 | `tests/test_federation.py`, `tests/test_agent_multiround.py`, `tests/test_mitigations.py` |

Run the full suite after every phase merge; see [AGENTS.md](../AGENTS.md) done criteria.

## Related docs

| Topic | Doc |
|-------|-----|
| Full local demo | [local-demo-runbook.md](local-demo-runbook.md) |
| Enterprise graph + agent design | [enterprise-graph-design.md](enterprise-graph-design.md) |
| Supply chain disruption response | [supply-chain-disruption-response.md](supply-chain-disruption-response.md) |
| Ontology on LanceDB | [ontology-on-lance.md](ontology-on-lance.md) |
| Graph context contract | [graph-context.md](graph-context.md) |
| LiteLLM / Gemini | [llm-gateway.md](llm-gateway.md) |
| Langfuse traces | [observability.md](observability.md) |
| Tests, lint, type check | [testing-and-quality.md](testing-and-quality.md) |
| Federated domain demo (E2E) | [federation-demo-runbook.md](federation-demo-runbook.md) |
| Agent contributors | [AGENTS.md](../AGENTS.md) |
