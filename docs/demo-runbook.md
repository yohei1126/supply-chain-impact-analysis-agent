# Demo runbook

How to **run**, **verify**, and **evaluate** BOM supply-impact demos: federation CLI (graphs only), web UI, and full stack (LiteLLM + Langfuse + agent).

**Related:** [README.md](../README.md) · [development.md](development.md) · [seeding.md](seeding.md) · [setup-and-demos.md](setup-and-demos.md) · [llm-gateway.md](llm-gateway.md) · [observability.md](observability.md) · [testing-and-quality.md](testing-and-quality.md)

---

## How to use this document

| You want to… | Start here |
|--------------|------------|
| Pick a demo entry point | §1 Demo paths |
| Run federation without Docker LLM/Langfuse | Part A — Federation CLI |
| Run LiteLLM + Langfuse + agent UI | Part B — Full stack setup |
| Walk through browser tabs | Part C — Browser UI |
| Know ground truth (IDs, suppliers, products) | §2 Seed data reference |
| Score an agent run (pass / partial / fail) | Part D — Verification & evaluation |
| See which surface shows which detail | Part D.3 — UI vs Langfuse |
| Automate smoke checks | Part D.4 — Automated checks |

---

## 1. Demo paths

Three entry points share the same synthetic BOM in [`pipeline/demo/sample_data.py`](../pipeline/demo/sample_data.py).

| Path | Command / URL | Proves | Langfuse |
|------|---------------|--------|----------|
| **A. Federation CLI** | `uv run python scripts/demo_federation.py --reset` | Per-domain load, join on `Component.id`, problems/mitigations | No |
| **B. Web UI (graphs)** | `uv run python -m app.agent` → **Domain query** / **Federation** tabs | Cypher + tables + federated map in browser | No |
| **C. Web UI (agent)** | Same server → **Agent (LLM)** tab (+ optional LiteLLM) | Natural-language goals → planner → tools → user summary | Yes (`bom-agent-run`) |

**Recommended first-time flow:** start Neo4j → seed data → **B** (confirm graphs) → **C** (confirm agent) → Langfuse for **C** only.

```bash
# Neo4j (required for all paths)
docker compose --profile neo4j up -d

# Shared seed for B and C
uv run python scripts/seed_complex_bom.py --reset
uv run python -m app.agent
# → http://127.0.0.1:8080/ui/
```

For path **A** without the agent server, see [Part A — Federation CLI](#part-a--federation-cli-no-docker--llm).

---

## 2. Seed data reference (ground truth)

Use this table when judging whether demo output is **correct**, not hallucinated.

### Suppliers

| ID | Name | Country | Risk | Demo role |
|----|------|---------|------|-----------|
| `SUP-001` | Nihon Steel | JP | High | Default federation CLI scenario; steel-heavy supply |
| `SUP-002` | Euro Brass GmbH | DE | Medium | **German brass** agent example |
| `SUP-003` | Pacific Plastics | US | Low | Mitigation / alternate sourcing stories |

### Products

| ID | Name |
|----|------|
| `PROD-900` | Industrial Pump |
| `PROD-901` | Servo Motor Drive |
| `PROD-902` | Valve Manifold |

### Components by supplier (sourcing domain)

| Supplier | Component IDs | Notes |
|----------|---------------|-------|
| `SUP-001` | COMP-100, 102, 103, 104, 105 | Includes **Drive Shaft** (`COMP-103`) |
| `SUP-002` | COMP-101, 106, 108, 110, 111 | All brass-related; **Valve** = `COMP-101` |
| `SUP-003` | COMP-107, 109 | |

### Key cross-links for agent examples

| Scenario clue | Resolves to | Tool (expected) |
|---------------|-------------|-----------------|
| Germany + brass + supplier disruption | `SUP-002` | `bom_supplier_impact` |
| Drive shaft + Servo Motor Drive | `COMP-103` → `PROD-901` | `bom_supply_path` |
| Brass valve shortage / similar parts | `SUP-002` (Euro Brass brass components) | `bom_supplier_impact` |
| Explicit `SUP-001` in goal text | `SUP-001` | `bom_supplier_impact` |

Bridge key for federation: **`Component.id`** (same part number in sourcing, ebom, routing).

---

## Part A — Federation CLI (no Docker / LLM)

Step-by-step: **generate synthetic data per domain → validate → load → query each graph → federate → find problems → recommend mitigations**.

No LiteLLM or Langfuse required. **Neo4j must be running** (`docker compose --profile neo4j up -d` or `./scripts/start_stack.sh` for the full stack).

**Audience:** developers, architects, demo presenters.

### A.1 What this demo proves

Manufacturing supply-chain data is owned by **three teams** (engineering, manufacturing, procurement). Each team loads its own graph. Cross-domain questions are answered by **logical federation** at query time on shared `Component.id` — not by merging databases.

| Phase | What happens | Owner (conceptual) |
|-------|----------------|-------------------|
| 1. Generate | Build independent node/edge bundles per domain | Each `domains/*/pipeline.py` slice |
| 2. Validate | Check every row against `ontology/schema.py` | Shared ontology |
| 3. Load | Write to Neo4j with `graph_id` (`sourcing`, `ebom`, `routing`) | Per-domain graph stores |
| 4. Query | Read one graph at a time (supplier → components → products → processes) | Domain stores |
| 5. Federate | Join on `Component.id`; compute impact | `app/federation/` |
| 6. Respond | List **problems** and **mitigations** with owning teams | Deterministic templates |

### A.2 Prerequisites

From the repository root:

```bash
uv sync
docker compose --profile neo4j up -d
```

Requires Python 3.10+. No API keys beyond Neo4j defaults (`bolt://localhost:7687`, user `neo4j`, password `password` unless overridden in `.env`).

### A.3 Quick start (one command)

Interactive (pauses at each step; press Enter):

```bash
uv run python scripts/demo_federation.py --reset
```

When prompted for `supplier_id`, press Enter for the default **`SUP-001`** (Nihon Steel, High risk).

Non-interactive (CI or scripting):

```bash
DEMO_NONINTERACTIVE=1 uv run python scripts/demo_federation.py --reset --supplier-id SUP-001
```

| Flag | Meaning |
|------|---------|
| `--reset` | Clear Neo4j domain data before load (recommended) |
| `--supplier-id` | Disruption scenario input (default `SUP-001`) |

Expected runtime: ~5–15 seconds (interactive timing depends on Enter presses).

### A.4 End-to-end flow

```text
pipeline/demo/sample_data.py          shared component master rows
         │
         ▼
Step 1   pipeline/demo/domain_datasets.py   build sourcing / ebom / routing bundles
         │
         ▼
Step 2   DomainDataset.validate()            Pydantic via ontology/schema.py
         │
         ▼
Step 3   pipeline/demo/load_domains.py       write to Neo4j (graph_id per domain)
         │
         ▼
Step 4   app/federation/analysis.py          query_sourcing / query_ebom / query_routing
         │
         ▼
Step 5   analyze_supplier_disruption()        federate + problems + mitigations + impact_score
```

Logical layout after Step 3 (single Neo4j database, separated by `graph_id`):

```
neo4j (bolt://localhost:7687)
  graph_id=sourcing   SUPPLIED_BY, Supplier, Component
  graph_id=ebom       USED_IN, Product, Component
  graph_id=routing    INPUT_OF, PRODUCED_BY, Process, Product, Component
```

Bridge key: **`Component.id`**. Graph Contract: [ontology/contract/graph_context.yaml](../ontology/contract/graph_context.yaml) — see [graph-contract.md](graph-contract.md).

### A.5 Step-by-step (manual / programmatic)

Use this section to run phases separately in a notebook, test, or custom script.

#### Step 1 — Generate synthetic data per domain

```python
from pipeline.demo.domain_datasets import build_all_domain_datasets, dataset_summary

datasets = build_all_domain_datasets()
for graph_id, ds in datasets.items():
    print(graph_id, dataset_summary(ds))
```

| Domain | Typical nodes | Typical edges | Module |
|--------|---------------|---------------|--------|
| **sourcing** | Supplier, Component | `SUPPLIED_BY` | `build_sourcing_dataset()` |
| **ebom** | Product, Component | `USED_IN` | `build_ebom_dataset()` |
| **routing** | Process, Product, Component | `INPUT_OF`, `PRODUCED_BY` | `build_routing_dataset()` |

Source fixtures: [`pipeline/demo/sample_data.py`](../pipeline/demo/sample_data.py) (12 components, 3 suppliers, 3 products, 4 processes).

#### Step 2 — Validate against ontology

```python
from pipeline.demo.domain_datasets import validate_all_datasets

errors = validate_all_datasets(datasets)
assert all(not errs for errs in errors.values()), errors
```

After changing `ontology/schema.py` only:

```bash
uv run python scripts/sync_ontology.py
```

#### Step 3 — Load into separate domain graphs

```python
from app.federation.graph_store import GraphStore
from app.storage.neo4j_config import reset_neo4j
from pipeline.demo.load_domains import load_all_domains_separately

graph = GraphStore()
try:
    reset_neo4j(graph.driver)  # optional but recommended
    stats = load_all_domains_separately(graph)
    print(stats)
finally:
    graph.close()
```

**Alternative — single-domain ingest only:**

```bash
uv run python scripts/ingest/sourcing.py
uv run python scripts/ingest/ebom.py
uv run python scripts/ingest/routing.py
```

**Alternative — all domains + DuckDB (agent UI path):**

```bash
uv run python scripts/seed_complex_bom.py --reset
```

Uses [`pipeline/demo/seed.py`](../pipeline/demo/seed.py) (orchestrates domain pipelines + component master store).

#### Step 4 — Query each domain graph

```python
from app.federation.analysis import (
    query_sourcing_for_supplier,
    query_ebom_for_components,
    query_routing_for_components,
)

graph = GraphStore()
try:
    supplier_id = "SUP-001"
    sourcing_q = query_sourcing_for_supplier(graph, supplier_id)
    component_ids = {r["component_id"] for r in sourcing_q.rows}
    ebom_q = query_ebom_for_components(graph, component_ids)
    routing_q = query_routing_for_components(graph, component_ids)
    print(sourcing_q.summary, len(sourcing_q.rows), "rows")
finally:
    graph.close()
```

| Query | Graph | Question answered |
|-------|-------|-------------------|
| `components_by_supplier` | sourcing | Which parts does this supplier provide? Lead time? Risk? |
| `products_by_components` | ebom | Which finished goods use those parts? |
| `processes_by_components` | routing | Which processes / work centers consume those parts? |

#### Step 5 — Federate, find problems, recommend mitigations

```python
from app.federation.analysis import analyze_supplier_disruption

graph = GraphStore()
try:
    analysis = analyze_supplier_disruption(graph, "SUP-001")
    print("impact_score:", analysis.impact_score)
    for p in analysis.problems:
        print(p.severity, p.category, p.message)
finally:
    graph.close()
```

**Problems detected (examples for `SUP-001`):** `supplier_risk`, `single_source`, `lead_time`, `product_spread`, `manufacturing`.

**Mitigations:** owner-tagged actions (procurement, engineering, manufacturing, program_management). See [supply-chain-disruption-response.md](supply-chain-disruption-response.md) §7.

**Impact score:** deterministic formula — not LLM-computed.

### A.6 Example scenarios

Default disrupted supplier: **Nihon Steel** (`SUP-001`, Japan, **High** risk).

Try a different input:

```bash
DEMO_NONINTERACTIVE=1 uv run python scripts/demo_federation.py --reset --supplier-id SUP-002
```

(`SUP-002` Euro Brass — Medium risk, brass components, different product mix.)

Unknown supplier:

```bash
DEMO_NONINTERACTIVE=1 uv run python scripts/demo_federation.py --reset --supplier-id SUP-999
```

Expect `no_supply` problem and empty federated rows.

### A.7 Code map

| Step | Primary module | CLI wrapper |
|------|----------------|-------------|
| 1 Generate | `pipeline/demo/domain_datasets.py` | `scripts/demo_federation.py` |
| 2 Validate | `DomainDataset.validate()` | (same) |
| 3 Load | `pipeline/demo/load_domains.py` | `--reset` flag |
| 4 Query | `app/federation/analysis.py` | Step 4 in demo |
| 5 Federate | `analyze_supplier_disruption()` | Step 5 in demo |
| Domain ingest (production-shaped) | `domains/*/pipeline.py` | `scripts/ingest/*.py` |

Playbook tool order: [`app/federation/playbooks.yaml`](../app/federation/playbooks.yaml).

### A.8 Verify with tests

```bash
uv run pytest -q tests/test_federation_analysis.py
uv run pytest -q tests/test_domain_layout.py tests/test_graph_store.py
```

Full suite: [testing-and-quality.md](testing-and-quality.md).

### A.9 Federation troubleshooting

| Symptom | Fix |
|---------|-----|
| Neo4j connection refused | `docker compose --profile neo4j up -d`; check `BOM_NEO4J_URI` |
| Validation errors after editing data | Stay within `ALLOWED_EDGES` in `ontology/schema.py`; run `uv run python scripts/sync_ontology.py` |
| Empty sourcing results | Wrong `supplier_id`; check `SUPPLIERS` in `sample_data.py` |
| Duplicate nodes on re-run | Use `--reset` or `reset_neo4j()` |
| Edge constraint violation | Edge type not allowed in that domain — check `domains/registry.py` |
| Demo does not pause | Set `DEMO_NONINTERACTIVE=1` or run without a TTY |

---

## Part B — Full stack setup (LiteLLM + Langfuse + agent)

End-to-end steps: Docker stack (Neo4j + LiteLLM + Langfuse) → BOM data → agent server → web UI → Langfuse traces.

### B.1 What you will run

| Process | URL | Role |
|---------|-----|------|
| Neo4j (Docker) | http://127.0.0.1:7474 (browser), bolt://127.0.0.1:7687 | Domain graphs |
| LiteLLM (Docker) | http://127.0.0.1:4000/v1 | OpenAI-compatible LLM gateway (e.g. Gemini) |
| Langfuse (Docker) | http://127.0.0.1:3000 | Traces: planner, tools, raw JSON (not in UI) |
| BOM agent | http://127.0.0.1:8080 | API + user UI |
| User UI | http://127.0.0.1:8080/ui/ | Summary, Key findings, Evidence, Supply chain map |

Use **three terminals** (or run Docker detached in one).

### B.2 Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- **Docker** available (Docker Desktop or [Colima](https://github.com/abiosoft/colima))
- Repo cloned and `cd` into the root

```bash
colima start          # if using Colima and Docker is not running
docker info           # should succeed
```

### B.3 One-time setup

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
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | from Langfuse UI | After step B.5 |

Seed ontology-validated demo BOM (Neo4j domain graphs + DuckDB component master):

```bash
uv run python scripts/seed_complex_bom.py --reset
```

### B.4 Terminal A — Docker stack

```bash
./scripts/start_stack.sh
```

Starts Neo4j, Langfuse, and LiteLLM (detached). Wait until:

- Langfuse: `langfuse-web` logs **Ready** (first boot ~2–3 minutes)
- LiteLLM: container healthy on port **4000**
- Neo4j: bolt port **7687** accepting connections

Quick checks:

LiteLLM is configured with `LITELLM_MASTER_KEY` in [`config/litellm.yaml`](../config/litellm.yaml). **Unauthenticated** requests to `/health` return **401** — that still means the proxy is listening. Use the same key as in `.env` (`sk-litellm-local` by default):

```bash
# LiteLLM — expect 200 (use your LITELLM_MASTER_KEY / OPENAI_API_KEY value)
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer sk-litellm-local" \
  http://127.0.0.1:4000/health

# Langfuse UI — expect 200 (no auth header)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
```

Stop later:

```bash
./scripts/stop_stack.sh
```

### B.5 Langfuse — first-time API keys

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

### B.6 Terminal B — BOM agent

The agent loads `.env` from the repo root on startup. Restart after any `.env` change.

```bash
export BOM_REPO_ROOT=$(pwd)
uv run --extra observability python -m app.agent
```

Confirm Langfuse is wired:

```bash
curl -s http://127.0.0.1:8080/v1/config | python3 -m json.tool
```

Expect `"langfuse_configured": true` and `"llm_configured": true`.

Health check:

```bash
curl -s http://127.0.0.1:8080/health
```

### B.7 Langfuse — confirm telemetry

After at least one **Agent (LLM)** tab run or agent API call (see [Part C.3](#c3-agent-llm-tab)):

1. Open **http://localhost:3000** → **Traces**
2. Find trace name **`bom-agent-run`**
3. Expand spans: `planning`, `tool:bom_supplier_impact` (etc.), generations `planner` / `summarize` when LLM is used

CLI check:

```bash
uv run --extra observability python scripts/verify_langfuse_telemetry.py
```

After at least one analysis, expect one or more **`bom-agent-run`** entries with `auth_check: OK`.

### B.8 Full stack troubleshooting

| Symptom | Fix |
|---------|-----|
| `Cannot connect to the Docker daemon` | `colima start` or start Docker Desktop |
| Neo4j connection refused | `./scripts/start_stack.sh` (includes neo4j profile) or `docker compose --profile neo4j up -d` |
| Langfuse never becomes Ready | `docker compose --profile langfuse logs -f langfuse-web` |
| LiteLLM `/health` returns **401** without `Authorization` | Expected when `master_key` is set — retry with `Bearer` + `LITELLM_MASTER_KEY` |
| LiteLLM **401** on `/v1/chat/completions` | Set `GEMINI_API_KEY` in `.env`; ensure `OPENAI_API_KEY` matches `LITELLM_MASTER_KEY`; restart stack |
| `langfuse_configured: false` on agent | Add keys to `.env`; restart agent with `--extra observability` |
| Empty map / no findings | `uv run python scripts/seed_complex_bom.py --reset`; restart agent |
| Port 4000 already in use | `./scripts/stop_stack.sh` or change `LITELLM_PORT` |
| Port 8080 in use | `export BOM_AGENT_PORT=8081` and use `http://localhost:8081/ui/` |

---

## Part C — Browser UI

Open **http://localhost:8080/ui/**

Top-right pill should show **Ready**. The UI has three tabs — **Domain query**, **Federation**, and **Agent (LLM)**.

### C.1 Domain query tab

Query **one** Neo4j domain graph at a time using **Cypher**.

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

### C.2 Federation tab

1. Enter disrupted supplier (e.g. `SUP-002`) or pick an example.
2. Click **Run federation**.
3. Review the pipeline: sourcing → ebom → routing on `Component.id`.
4. Read **Problems**, **Mitigations**, **Joined impact rows**, and the federated supply chain map.

### C.3 Agent (LLM) tab

Natural-language questions with planner + optional LLM summary (requires LiteLLM when `mode=auto`). UI examples use **indirect scenarios** (no explicit `SUP-xxx` / `COMP-xxx`) so you can verify the agent interprets context before calling tools.

1. Click an example, e.g. **German brass supplier disruption** — read Intent / Expected exploration on the card
2. Click **Analyze**
3. Compare agent tool choices and results against the expected exploration; read **Summary**, **Key findings**, **Evidence**, and the supply chain map

Other examples: **Servo motor drive shaft trace** (part/product names → supply path), **Brass valve shortage** (brass valve parts → Euro Brass supplier impact).

Use this tab for Langfuse **`bom-agent-run`** traces from the browser.

For deterministic API checks (explicit IDs), use curl:

```bash
curl -s -X POST http://127.0.0.1:8080/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Analyze supplier impact for SUP-002","mode":"tools"}' | python3 -m json.tool

curl -s -X POST http://127.0.0.1:8080/v1/federation/domain-query \
  -H 'Content-Type: application/json' \
  -d '{"graph_id":"sourcing","supplier_id":"SUP-002"}' | python3 -m json.tool

curl -s -X POST http://127.0.0.1:8080/v1/federation/analyze \
  -H 'Content-Type: application/json' \
  -d '{"supplier_id":"SUP-002"}' | python3 -m json.tool
```

Scenario playbooks and pass/fail criteria: [Part D.1](#d1-scenario-playbooks).

---

## Part D — Verification & evaluation

### D.1 Scenario playbooks

Each playbook: **action → confirm → evaluate**.

#### D.1.1 Federation — `SUP-002` (Euro Brass)

**Where:** **Federation** tab (or `POST /v1/federation/analyze` with `{"supplier_id":"SUP-002"}`).

| Step | Action | Confirm |
|------|--------|---------|
| 1 | Enter `SUP-002`, click **Run federation** | Status **Ready**; no HTTP error |
| 2 | Domain steps | Three steps: **sourcing → ebom → routing** |
| 3 | Sourcing Cypher | `SUPPLIED_BY` from supplier; rows include COMP-101, 106, 108, 110, 111 |
| 4 | Joined rows | Each row ties component → product(s) → process(es) |
| 5 | Problems / mitigations | Non-empty lists; mitigations mention alternate suppliers where applicable |
| 6 | Map | Federated supply chain map shows nodes/edges (not empty) |
| 7 | Impact score | Numeric pill present |

**Evaluate**

| Result | Criteria |
|--------|----------|
| **Pass** | ≥5 SUP-002 components in sourcing; products include PROD-900 / 901 / 902; map + joined rows populated |
| **Partial** | Sourcing OK but ebom/routing empty → check seed or component ID bridge |
| **Fail** | Empty sourcing for SUP-002 → re-run `seed_complex_bom.py --reset` |

#### D.1.2 Domain query — trace one component across graphs

**Where:** **Domain query** tab.

| Step | Action | Confirm |
|------|--------|---------|
| 1 | **sourcing**, `SUP-002` | Cypher panel shows `components_by_supplier`; table lists brass components |
| 2 | Copy component IDs (e.g. `COMP-101`) | |
| 3 | **ebom**, paste IDs | `USED_IN` rows → products (e.g. Valve → PROD-900, PROD-902) |
| 4 | **routing**, same IDs | `INPUT_OF` / process linkage |

**Evaluate:** Same component IDs appear in all three domains with consistent names/materials.

#### D.1.3 Agent — German brass supplier disruption

**Where:** **Agent (LLM)** tab → example card → **Analyze**.

**Goal sent to agent:**

> Our German brass supplier might face a port strike next month. Which finished products and component parts should we worry about?

| Step | Where | Confirm |
|------|-------|---------|
| 1 | Langfuse → `planning` | Tool `bom_supplier_impact` with `supplier_id: SUP-002` (heuristic) or equivalent (LLM) |
| 2 | Langfuse → `tool:bom_supplier_impact` | `row_count` > 0; `data` mentions Euro Brass / brass components |
| 3 | Agent UI → Summary | Answers which products/parts are at risk (plain language) |
| 4 | Agent UI → Key findings | Mentions affected products and/or brass parts |
| 5 | Agent UI → Evidence | Claims only — no tool names or Cypher |
| 6 | Agent UI → Map | Non-empty if graph tool returned seeds |
| 7 | Cross-check | Compare Langfuse tool JSON to **D.1.1** federation baseline for SUP-002 |

**Evaluate:** Correct tool + grounded findings = **pass**; invented IDs or empty findings while tool returned rows = **fail**.

#### D.1.4 Agent — Servo motor drive shaft trace

**Goal:**

> The servo motor drive product relies on a drive shaft part. Can you trace how that component connects through the bill of materials to the finished assembly?

**Evaluate:** Path must connect **Drive Shaft** (`COMP-103`) to **Servo Motor Drive** (`PROD-901`). Tool: `bom_supply_path`.

#### D.1.5 Agent — Brass valve shortage

**Goal:**

> We're short on brass valve-related parts. Find similar components in our catalog and show which suppliers feed them.

**Evaluate:** Heuristic planner routes to `bom_supplier_impact` with `SUP-002`. **Valve** (`COMP-101`) and Euro Brass should appear in tool output and findings.

#### D.1.6 Agent — explicit ID (regression / API)

```bash
curl -s -X POST http://127.0.0.1:8080/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Analyze supplier impact for SUP-002","mode":"tools"}' | python3 -m json.tool
```

**Evaluate:** `findings` non-empty; `graph_view.node_count >= 1`; Langfuse shows `SUP-002` in tool args.

### D.2 Evaluation rubric

Use after any **Agent (LLM)** run. Federation / Domain tabs use **functional** checks only (D.1.1–D.1.2).

#### Dimensions

| # | Dimension | Question | Primary source |
|---|-----------|----------|----------------|
| 1 | **Data readiness** | Is Neo4j seeded and health **Ready**? | UI pill; `GET /health` |
| 2 | **Tool selection** | Did the planner pick the right tool(s) for the scenario? | Langfuse `planning` |
| 3 | **Tool execution** | Did tools return non-empty `data` when seed supports it? | Langfuse `tool:*` |
| 4 | **Grounding** | Are summary/findings/evidence supported by tool JSON? | Langfuse metadata vs Agent UI |
| 5 | **User presentation** | Is the Agent UI free of Cypher, tool names, raw JSON? | Agent UI |
| 6 | **Graph fidelity** | Does the map reflect tool graph seeds? | Agent UI map vs tool output |
| 7 | **Observability** | Is there a complete `bom-agent-run` trace? | Langfuse / `verify_langfuse_telemetry.py` |

#### Overall grade

| Grade | Meaning |
|-------|---------|
| **Pass** | Correct tool + args; grounded findings; federation baseline aligns |
| **Partial** | Tool ran but summarize weak; map empty but findings OK |
| **Fail** | No tools; empty tool data after seed; hallucinated IDs; Langfuse missing when configured |

#### Heuristic vs LLM planner

| Mode | Evaluation focus |
|------|------------------|
| **`mode=tools`** or LLM off | Exact match to expected tools/args (`tests/test_agent.py`) |
| **`mode=auto`** with LiteLLM | Tool choice *reasonable* for goal; grounding still mandatory |

Do **not** fail an LLM run solely because args differ from heuristic — fail if tools are wrong for the business question or output is ungrounded.

### D.3 UI vs Langfuse

| Surface | Audience | Question it answers |
|---------|----------|---------------------|
| **Agent (LLM) tab** | Business user | *What is the impact in plain language?* |
| **Domain / Federation tabs** | Demo / architecture reviewer | *Do graphs and federation join behave correctly?* |
| **Langfuse** (`bom-agent-run`) | Developer / evaluator | *Why these tools, with what args, and what raw data backed the answer?* |

**Rule:** Langfuse-only details (planner, args, Cypher, raw JSON) stay out of the Agent UI. Cypher belongs on Domain/Federation tabs.

| Content | Agent UI | Domain | Federation | Langfuse |
|---------|:--------:|:------:|:------------:|:--------:|
| Summary / findings / evidence | ✓ | — | — | ✓ |
| Supply chain map | ✓ | — | ✓ | counts |
| Cypher + domain tables | — | ✓ | ✓ | ✓ |
| Problems / mitigations | — | — | ✓ | — |
| Planner, tool args, raw JSON | — | — | — | ✓ |

Details: [observability.md](observability.md).

### D.4 Automated checks

| Check | Command | Proves |
|-------|---------|--------|
| Unit + integration | `uv run pytest -q` | Planner, federation API, user response, skills assets |
| German brass planner | `uv run pytest -q tests/test_agent.py::test_plan_tools_from_goal` | SUP-002 routing for indirect goal |
| Federation API | `uv run pytest -q tests/test_federation_api.py` | Domain query Cypher + analyze join |
| Agent grounding benchmarks | `uv run pytest -q tests/test_agent_grounding.py` | G* evidence + narrative checks on seeded graph |
| Agent grounding CLI | `uv run python scripts/eval_agent_grounding.py --quiet` | End-to-end steward benchmark after seed |
| Langfuse smoke | `uv run --extra observability python scripts/verify_langfuse_telemetry.py` | Keys + recent `bom-agent-run` traces |

### D.5 Implementation map

| Topic | Code |
|-------|------|
| Seed / ground truth | `pipeline/demo/sample_data.py` |
| UI example cards | `app/agent/static/app.js` → `AGENT_EXAMPLES` |
| Heuristic planner | `app/agent/runner.py` → `plan_tools_from_goal` |
| User-facing response | `app/agent/user_response.py` |
| Langfuse emission | `app/agent/telemetry.py` |
| Federation analyze | `app/federation/analysis.py` |

---

## Quick links

| Task | Section |
|------|---------|
| Federation CLI (no LLM) | [Part A](#part-a--federation-cli-no-docker--llm) |
| Docker + agent + Langfuse | [Part B](#part-b--full-stack-setup-litellm--langfuse--agent) |
| Browser walkthrough | [Part C](#part-c--browser-ui) |
| Scenario pass/fail criteria | [Part D.1](#d1-scenario-playbooks) |
| Architecture | [enterprise-graph-design.md](enterprise-graph-design.md) |
| Disruption playbooks | [supply-chain-disruption-response.md](supply-chain-disruption-response.md) |
| Generated JSON catalogs | [agent-skill-assets.md](agent-skill-assets.md) |
