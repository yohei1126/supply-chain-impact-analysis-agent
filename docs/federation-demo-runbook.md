# Federated domain graph demo (end-to-end)

Step-by-step guide: **generate synthetic data per domain → validate → load → query each graph → federate → find problems → recommend mitigations**.

No Docker, LLM, or Langfuse required. For the full agent UI stack, see [local-demo-runbook.md](local-demo-runbook.md) after this demo.

**Audience:** developers, architects, demo presenters.

**Related:** [project-layout.md](project-layout.md) · [supply-chain-disruption-response.md](supply-chain-disruption-response.md) · [graph-context.md](graph-context.md) · [testing-and-quality.md](testing-and-quality.md) · [demo-verification-and-evaluation.md](demo-verification-and-evaluation.md) (confirm & evaluate demo output)

---

## 1. What this demo proves

Manufacturing supply-chain data is owned by **three teams** (engineering, manufacturing, procurement). Each team loads its own graph. Cross-domain questions are answered by **logical federation** at query time on shared `Component.id` — not by merging databases.

| Phase | What happens | Owner (conceptual) |
|-------|----------------|-------------------|
| 1. Generate | Build independent node/edge bundles per domain | Each `domains/*/pipeline.py` slice |
| 2. Validate | Check every row against `ontology/schema.py` | Shared ontology |
| 3. Load | Write to `data/lancedb/{sourcing,ebom,routing}/` | Per-domain Lance paths |
| 4. Query | Read one graph at a time (supplier → components → products → processes) | Domain stores |
| 5. Federate | Join on `Component.id`; compute impact | `app/federation/` |
| 6. Respond | List **problems** and **mitigations** with owning teams | Deterministic templates |

---

## 2. Prerequisites

From the repository root:

```bash
uv sync
```

Requires Python 3.10+. No API keys or Docker.

---

## 3. Quick start (one command)

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
| `--reset` | Delete `data/lancedb/` before load (recommended) |
| `--lancedb-path` | Default `data/lancedb` |
| `--supplier-id` | Disruption scenario input (default `SUP-001`) |

Expected runtime: ~5–15 seconds (interactive timing depends on Enter presses).

---

## 4. End-to-end flow (what each step does)

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
Step 3   pipeline/demo/load_domains.py       write to data/lancedb/{graph_id}/
         │
         ▼
Step 4   app/federation/analysis.py          query_sourcing / query_ebom / query_routing
         │
         ▼
Step 5   analyze_supplier_disruption()        federate + problems + mitigations + impact_score
```

Physical layout after Step 3:

```
data/lancedb/
  sourcing/     SUPPLIED_BY, Supplier, Component
  ebom/         USED_IN, Product, Component
  routing/      INPUT_OF, PRODUCED_BY, Process, Product, Component
```

Bridge key: **`Component.id`** (same part number in all three graphs). Contract: [ontology/contract/graph_context.yaml](../ontology/contract/graph_context.yaml).

---

## 5. Step-by-step (manual / programmatic)

Use this section if you want to run phases separately in a notebook, test, or custom script.

### Step 1 — Generate synthetic data per domain

Each domain builds its **own** node/edge list from shared fixtures.

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

To change demo data, edit `SUPPLIERS`, `COMPONENT_BOM`, etc. there, then re-run from Step 1.

---

### Step 2 — Validate against ontology

Every node passes `validate_node_payload()`; every edge passes `RelationEdge` (allowed source/target pairs).

```python
from pipeline.demo.domain_datasets import validate_all_datasets

errors = validate_all_datasets(datasets)
assert all(not errs for errs in errors.values()), errors
```

On failure the demo script exits with JSON error details. Fix data or `ontology/schema.py`, then retry.

After changing `ontology/schema.py` only:

```bash
uv run python scripts/sync_ontology.py
```

---

### Step 3 — Load into separate domain graphs

```python
from app.federation.graph_store import LanceGraphStore
from pipeline.demo.load_domains import load_all_domains_separately, reset_lancedb

reset_lancedb("data/lancedb")  # optional but recommended
graph = LanceGraphStore(lancedb_path="data/lancedb")
stats = load_all_domains_separately(graph)
print(stats)
```

Each domain is written **independently** through `DomainLanceGraphStore` with domain-scoped edge allow-lists ([`domains/registry.py`](../domains/registry.py)).

**Alternative — single-domain ingest only:**

```bash
uv run python scripts/ingest/sourcing.py
uv run python scripts/ingest/ebom.py
uv run python scripts/ingest/routing.py
```

These call `domains/*/pipeline.py` directly (components must exist before edges).

**Alternative — all domains + DuckDB + vectors (agent UI path):**

```bash
uv run python scripts/seed_complex_bom.py --reset
```

Uses [`pipeline/demo/seed.py`](../pipeline/demo/seed.py) (orchestrates domain pipelines + hybrid store).

---

### Step 4 — Query each domain graph

Input for this demo: **`supplier_id`** (e.g. `SUP-001`).

```python
from app.federation.analysis import (
    query_sourcing_for_supplier,
    query_ebom_for_components,
    query_routing_for_components,
)

supplier_id = "SUP-001"

sourcing_q = query_sourcing_for_supplier(graph, supplier_id)
component_ids = {r["component_id"] for r in sourcing_q.rows}

ebom_q = query_ebom_for_components(graph, component_ids)
routing_q = query_routing_for_components(graph, component_ids)

print(sourcing_q.summary, len(sourcing_q.rows), "rows")
print(ebom_q.summary, len(ebom_q.rows), "rows")
print(routing_q.summary, len(routing_q.rows), "rows")
```

| Query | Graph | Question answered |
|-------|-------|-------------------|
| `components_by_supplier` | sourcing | Which parts does this supplier provide? Lead time? Risk? |
| `products_by_components` | ebom | Which finished goods use those parts? |
| `processes_by_components` | routing | Which processes / work centers consume those parts? |

Queries touch **one Lance path each** — no cross-graph SQL join.

---

### Step 5 — Federate, find problems, recommend mitigations

```python
from app.federation.analysis import analyze_supplier_disruption

analysis = analyze_supplier_disruption(graph, supplier_id)

print("impact_score:", analysis.impact_score)
print("federated rows:", len(analysis.federated_rows))
for p in analysis.problems:
    print(p.severity, p.category, p.message)
for m in analysis.mitigations:
    print(m.priority, m.owner_team, m.action)
```

**Federation join:** `SUPPLIED_BY` (sourcing) → `Component.id` → `USED_IN` (ebom) → optional `INPUT_OF` (routing). Implemented in [`app/federation/graph_store.py`](../app/federation/graph_store.py) (`impacted_products_by_supplier`) and [`app/federation/analysis.py`](../app/federation/analysis.py).

**Problems detected (examples for `SUP-001`):**

| Category | Meaning |
|----------|---------|
| `supplier_risk` | Supplier already marked High risk |
| `single_source` | Affected component has only one supplier |
| `lead_time` | Lead time ≥ 18 days |
| `product_spread` | Multiple finished goods impacted |
| `manufacturing` | Work centers affected via routing graph |

**Mitigations:** owner-tagged actions (procurement, engineering, manufacturing, program_management). Filled only from query evidence — see [supply-chain-disruption-response.md](supply-chain-disruption-response.md) §7.

**Impact score:** deterministic formula (product count, cost exposure, single-source count, lead-time factor) — not LLM-computed.

---

## 6. Example scenario: `SUP-001`

Default disrupted supplier: **Nihon Steel** (`SUP-001`, Japan, **High** risk).

Typical federated outcome:

- **Components:** steel-heavy parts (e.g. `COMP-100` Frame, `COMP-103` Drive Shaft)
- **Products:** `PROD-900` Industrial Pump, `PROD-901` Servo Motor Drive
- **Processes / work centers:** e.g. `WC-1`, `WC-12` via `INPUT_OF`
- **Mitigations:** qualify alternate supplier, assess ECO on high-cost parts, reschedule assembly, notify program office

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

---

## 7. Code map

| Step | Primary module | CLI wrapper |
|------|----------------|-------------|
| 1 Generate | `pipeline/demo/domain_datasets.py` | `scripts/demo_federation.py` |
| 2 Validate | `DomainDataset.validate()` | (same) |
| 3 Load | `pipeline/demo/load_domains.py` | `--reset` flag |
| 4 Query | `app/federation/analysis.py` | Step 4 in demo |
| 5 Federate | `analyze_supplier_disruption()` | Step 5 in demo |
| Domain ingest (production-shaped) | `domains/*/pipeline.py` | `scripts/ingest/*.py` |

Playbook tool order (future agent wiring): [`app/federation/playbooks.yaml`](../app/federation/playbooks.yaml).

---

## 8. Verify with tests

```bash
uv run pytest -q tests/test_federation_analysis.py
uv run pytest -q tests/test_domain_layout.py tests/test_lance_graph_store.py
```

Full suite: [testing-and-quality.md](testing-and-quality.md).

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Validation errors after editing data | Stay within `ALLOWED_EDGES` in `ontology/schema.py`; run `uv run python scripts/sync_ontology.py` after schema edits |
| Empty sourcing results | Wrong `supplier_id`; check `SUPPLIERS` in `sample_data.py` |
| Duplicate nodes on re-run | Use `--reset` or `reset_lancedb()` |
| `Edge constraint violation` | Edge type not allowed in that domain — check `domains/registry.py` |
| Demo does not pause | Set `DEMO_NONINTERACTIVE=1` or run without a TTY |

---

## 10. Next steps

| Goal | Command / doc |
|------|----------------|
| Agent UI + LLM | [local-demo-runbook.md](local-demo-runbook.md) |
| Architecture | [enterprise-graph-design.md](enterprise-graph-design.md) |
| Disruption playbooks (design) | [supply-chain-disruption-response.md](supply-chain-disruption-response.md) |
| Project layout | [project-layout.md](project-layout.md) |

After federation demo, seed hybrid store for the web UI:

```bash
uv run python scripts/seed_complex_bom.py --reset
uv run python -m app.agent
# http://localhost:8080/ui/
```
