# Ontology utilization — this project

How the L0–L5 ladder maps to **this repository**: narrow ontology, Graph Contract, what is implemented, and how **agent grounding** differs from GraphRAG.

**Audience:** architects, contributors, coding agents.

**Prerequisites:** [ontology-levels-general.md](ontology-levels-general.md) (classical/modern definitions, L0–L5, GraphRAG §6).

**See also:** [ontology-levels.md](ontology-levels.md) (index) · [terminology.md](terminology.md) · [seeding.md](seeding.md)

---

## 1. Our definition of ontology (narrow)

This repository follows the **modern lightweight** pattern: **semantic validation** at L0–L2 (Pydantic SSOT), **no OWL reasoner** (L5 out of scope), federation as **Graph Contract** (L4). Demo “reasoning” is **tool orchestration + graph traversal**, not ontology entailment.

| Artifact | SSOT path | Level | Role |
|----------|-----------|-------|------|
| **Ontology (narrow)** | `ontology/schema.py` | L0–L2 | Node models, `ALLOWED_EDGES`, `RelationEdge` |
| **Published schema** | `skills/bom-ontology/assets/ontology.json` | L1 | Generated for Skills |
| **Cypher recipes** | `ontology/cypher_builder.py` | L2 (derived) | Query patterns from edge semantics |
| **Domain partition** | `domains/registry.py`, `domains/*/bundle.py` | L2 | Per-`graph_id` allow-list |
| **Graph Contract** | `ontology/contract/graph_context.yaml` | L4 | Bridges, joins, quality gate names |
| **graph context** | `skills/.../graph-context.json` | L4 (derived) | Agent scope bundle |
| **query catalog** | `skills/.../query-catalog.json` | Usage | Named Cypher specs |

Not called ontology here: owner SLA, `as_of` policy, playbook order, Langfuse telemetry.

```text
  ontology/schema.py (L0–L2)          Graph Contract YAML (L4)
           │                                    │
           ├─► ontology.json                    ├─► graph-context.json
           ├─► cypher_builder.py                └─► playbooks / federation
           └─► stores validate on write
```

---

## 2. Two classical roles → this repo

| Classical role | In this project | Implemented? |
|----------------|-----------------|--------------|
| **Semantic validation (define)** | L0–L2 — `schema.py`, registry, write-time validators | **Yes** (Python write paths) |
| **Semantic validation (prove)** | L3 — Cypher audit, SHACL | **Done** (Cypher audit + Neosemantics SHACL + payload re-validation) |
| **Reasoning (inference)** | L5 — OWL/reasoner | **Out of scope** |
| **Modern “inference”** | Federation joins, tools, planner + Cypher | **Yes** (deterministic) |
| **Federation agreement** | L4 — Graph Contract | **Done** |
| **Answer grounding (G\*)** | Tool `evidence`, demo rubric — §7 | **Partial** (tools mode strong; LLM summary weaker) |

**Effective ceiling:** **L2 on all official write paths** (storage layer + post-load L3 gate); **L5 not used**.

Closed-world policy: graph mutations go through `GraphStore.add_node` / `add_edge` only; `execute_domain_cypher` rejects write Cypher; seed/ingest run `require_l3_conformance` after load. Manual Neo4j Browser / external ETL bypass remains an **operational** risk — detect with `audit_neo4j.py` or CI.

---

## 3. Level mapping (summary)

| Level | Implemented? |
|-------|--------------|
| **L0** Vocabulary | **Yes** |
| **L1** Payload schema | **Yes** |
| **L2** Structural + domain scope | **Yes** |
| **L3** Post-load conformance | **Done** |
| **L4** Graph Contract | **Done** |
| **L5** Reasoning | **Out of scope** |

---

## 4. What is implemented (by level)

### L0 — Vocabulary — **Done**

| What | Where |
|------|--------|
| Node and edge type names | `ontology/schema.py` |
| Skill-facing copy | `skills/bom-ontology/`, `skills/bom-graph-explorer/` |

### L1 — Record schema — **Done**

| What | Where |
|------|--------|
| Pydantic models | `ontology/schema.py` |
| `validate_node_payload()` | `GraphStore.add_node`, demo datasets |
| `ontology.json` | `scripts/sync_ontology.py` |
| Tests | `tests/test_schema.py`, `tests/test_skill_ontology_asset.py` |
| Pre-load validation | `validate_all_datasets()` in `pipeline/demo/domain_datasets.py` |

### L2 — Structural constraints — **Done**

| What | Where |
|------|--------|
| `ALLOWED_EDGES`, `RelationEdge` | `schema.py` |
| Per-`graph_id` allow-list | `domains/registry.py` |
| Neo4j write guards | `app/storage/neo4j_domain_store.py` |
| Demo validate-before-load | `scripts/demo_federation.py`, `tests/test_federation_analysis.py` |
| Cypher from ontology | `ontology/cypher_builder.py`, `tests/test_cypher_builder.py` |
| **Official write path only** | `GraphStore` / `Neo4jDomainStore`; `tests/test_write_path_guardrails.py` |
| **Read-only Cypher executor** | `execute_domain_cypher` rejects CREATE/MERGE/… |
| **Post-load proof on ingest** | `require_l3_conformance` in `seed_complex_bom.py`, `scripts/ingest/*.py` |

**Operational bypass (out of repo control):** Neo4j Browser or external ETL loading directly — use `audit_neo4j.py` or CI to detect.

### L3 — Instance conformance — **Done**

| Item | Status |
|------|--------|
| Cypher audit (`ontology/l3_audit.py`, `app/validation/neo4j_l3_audit.py`) | **Done** — `uv run python scripts/audit_neo4j.py` |
| Payload re-validation (Pydantic on live graph) | **Done** (same audit runner) |
| SHACL via Neosemantics | **Done** — `ontology/shacl_codegen.py` → `ontology/assets/bom-shapes.ttl`; batch validation in `app/validation/neo4j_shacl_audit.py` (requires n10s plugin; CI sets `BOM_L3_REQUIRE_SHACL=1`) |

**Symptom:** empty Supply Chain Map → often stale Neo4j; run `uv run python scripts/seed_complex_bom.py --reset`.

### L4 — Graph Contract — **Done**

| What | Status | Where |
|------|--------|--------|
| YAML SSOT | Done | `ontology/contract/graph_context.yaml` |
| Runtime federation | Done | `app/federation/analysis.py` |
| Playbooks | Done | `app/federation/playbooks.yaml` |
| graph-context export | Done | `domains/export.py`, `tests/test_skill_agent_assets.py` |
| **GraphContract loader** | **Done** | `ontology/contract/graph_contract.py`, `get_graph_contract()` |
| **quality.on_ingest hooks** | **Done** | `app/validation/contract_ingest.py`, `require_l3_conformance` |
| **Federation composer (P4)** | **Done** | `app/federation/composer.py` |
| **quality.on_federate hooks** | **Done** | `app/validation/contract_federate.py` |
| Write-time `validate_edge` / `validate_node` | **Done** | `Neo4jDomainStore` + Graph Contract |
| Composer enforces joins | **Done** | `compose_join` reads `federation.joins` |
| **Ingest `as_of` metadata** | **Done** | `app/validation/ingest_metadata.py`, `Neo4jDomainStore.add_node` |
| **Production connector ingest (P5)** | **Done** | `pipeline/connectors/registry.py`, `app/validation/connector_ingest.py`, `scripts/ingest/` |
| **Async on_ingest audit pipeline** | **Done** | `app/validation/ingest_audit_pipeline.py`, `scripts/audit_ingest_pipeline.py` |

### L5 — Reasoning — **Out of scope**

No OWL reasoner. Agent uses LLM + **deterministic tools** (modern substitute).

---

## 5. Validation timing in this repo

Classical ontology serves **validation** and **reasoning** ([general §1](ontology-levels-general.md#1-the-two-roles-of-ontology-classical-view)). **This section covers validation only** — define allowed patterns (L0–L2), prove loaded data conforms (L3), and Graph Contract quality (L4). **Reasoning (L5 OWL)** is out of scope here; see [§2](#2-two-classical-roles--this-repo) for how this repo substitutes inference with tools and federation.

Validation splits into two classical phases:

| Phase | Question | Levels in this repo |
|-------|----------|---------------------|
| **Define** | What may exist? | L0–L2 authoring; L4 contract docs |
| **Prove** | Does the stored graph conform? | L3 post-load; L4 quality gates |

```text
  Authoring (define)     Pre-load ──► On write (reject) ──► After load (prove) ──► At federate (L4)
  schema.py, YAML        datasets      GraphStore            Neo4j audit           composer
  registry.py            in memory     add_node/add_edge     SHACL, on_ingest      on_federate
```

| When | Purpose | Scope | Mechanism | Levels |
|------|---------|-------|-----------|--------|
| **Authoring** | **Define** vocabulary, record shapes, edge rules, and federation policy | Source files only (`schema.py`, `graph_context.yaml`, `registry.py`); no Neo4j rows | Human edit + review; `sync_ontology.py` exports | L0–L2, L4 docs |
| **Pre-load** | **Reject bad payloads early** before any graph mutation | In-memory demo/ingest datasets (`validate_all_datasets()` on dicts from `sample_data.py` or adapters) | Pydantic on dataset bundles | L1–L2 |
| **On write** | **Block invalid rows at the storage boundary** (closed-world ingest) | Each official `GraphStore.add_node` / `add_edge`; domain allow-list; ingest metadata stamping | `validate_node_payload`, `RelationEdge`, `assert_*_allowed_in_graph`, Graph Contract write hooks | L1–L2 |
| **After load (L3)** | **Prove** the live graph still matches ontology shapes and structure | All Neo4j nodes/edges with `graph_id`; bypass via Browser/ETL is out of repo control | Cypher audit (`ontology/l3_audit.py`), Pydantic re-validation, Neosemantics SHACL batch (`audit_neo4j.py`, `require_l3_conformance`) | L3 |
| **After load (L4 ingest)** | **Prove** Graph Contract ingest quality (bridges, orphans, cross-store checks) | Same loaded graph + DuckDB component master | Sync: `run_on_ingest_quality_gates` in `require_l3_conformance`; async batch: `scripts/audit_ingest_pipeline.py` (`on_ingest_audit`) | L4 |
| **At federate** | **Enforce** cross-domain join and federate rules on composed results | Federation tool outputs merged on Bridge Keys; not individual Neo4j writes | `composer.py`, `contract_federate.py` (`quality.on_federate`) | L4 |
| **CI** | **Regression guard** — repeat define/prove checks on every change | Committed exports; CI Neo4j + n10s; pytest | Asset drift tests, seed + `audit_neo4j.py` + `audit_ingest_pipeline.py` (`BOM_L3_REQUIRE_SHACL=1`), full pytest | L1–L4 |

**Not validation (out of scope for this table):**

| Role | Purpose | In this repo |
|------|---------|--------------|
| **Reasoning (L5)** | Infer implicit types/edges from OWL semantics | **Out of scope** — no OWL reasoner |
| **Answer grounding (G\*)** | Are agent **answers** faithful to tool/graph output? | Partial — `evidence[]`, demo rubric; see [§7](#7-agent-grounding-vs-graphrag) |

Seeding walkthrough (write path): [seeding.md](seeding.md). Run post-load proof: `uv run python scripts/audit_neo4j.py` (L3); `uv run python scripts/audit_ingest_pipeline.py` (L4 batch).

---

## 6. Ontology vs contract vs context

| Concern | Ontology (L0–L2) | Graph Contract (L4) | graph context |
|---------|:------------------:|:-------------------:|:-------------:|
| Node/edge meaning | ✓ | refs `schema.py` | via `ontology.json` |
| Per-`graph_id` allow-list | ✓ | ✓ YAML | ✓ JSON |
| Bridge Keys | — | ✓ | ✓ |
| Federation joins | — | ✓ | recipes |
| Quality gates | — | ✓ | — |
| Cypher catalog | ✓ | — | ✓ |
| Neo4j rows | write-time only | at federate | — |

---

## 7. Agent grounding vs GraphRAG

This repo does **not** use [GraphRAG](https://microsoft.github.io/graphrag/index/default_dataflow/) indexing. Grounding is still relevant for the **Agent (LLM)** tab.

| Aspect | GraphRAG grounding | This project's agent |
|--------|-------------------|----------------------|
| **Knowledge source** | LLM-extracted graph + communities | **Curated** Neo4j + DuckDB (L0–L2 on write) |
| **Retrieval** | Vector + community reports | **Deterministic tools** (`bom_supplier_impact`, …) |
| **Claim support** | Citations to entities / text units | `evidence[]` from tool JSON |
| **Ontology level** | L0–L1 soft at extract; G* at answer | **L2** on data; **G\*** on narrative vs tools |
| **Verification** | §6 in [ontology-levels-general.md](ontology-levels-general.md#6-graphrag-grounding--verification-and-ontology-levels) | [demo-runbook.md §D](demo-runbook.md#part-d--verification--evaluation), `tests/test_agent.py` |

### How we verify grounding today

| Check | Where | Level |
|-------|-------|-------|
| Planner picks correct tool/IDs | `tests/test_agent.py::test_plan_tools_from_goal` | G* (tool choice) |
| Tool output matches seed ground truth | [demo-runbook.md](demo-runbook.md) playbooks (SUP-002, COMP-103, …) | L3-ish + G* |
| User response has `evidence` | `tests/test_user_response.py` | G* |
| LLM summary only uses tool JSON | `summarize_run_openai_compat` system prompt | G* (prompt constraint) |
| Full trace for audit | Langfuse `bom-agent-run` | Ops, not ontology |

**Strong grounding path:** `mode=tools` — no LLM narrative drift. **`mode=auto`:** run demo-runbook rubric (pass/partial/fail) + Langfuse spans.

GraphRAG-style **G\*** eval (judge vs retrieved communities) does **not** apply directly unless you add an LLM-extracted layer. If you later index docs into GraphRAG, use general doc §6.3 **plus** L3 validation on the indexed graph against `schema.py` exports.

---

## 8. SHACL (L3)

[Neosemantics SHACL](https://neo4j.com/labs/neosemantics/5.14/validation/) validates an **existing** graph — semantic validation, not reasoning. Does not replace L1–L2 SSOT or L4 Contract.

Path: `schema.py` → `ontology/shacl_codegen.py` → `ontology/assets/bom-shapes.ttl` (via `scripts/sync_ontology.py`) → batch validation with `n10s.validation.shacl.validateSet` in `app/validation/neo4j_shacl_audit.py`.

Install the n10s plugin on Neo4j (`NEO4J_PLUGINS='["n10s"]'` in Docker). Set `BOM_L3_REQUIRE_SHACL=1` to fail audits when the plugin is missing.

---

## 9. Roadmap

```text
  Today                         Next (optional)
  L0–L4 validation + contract   →   bom-validate Skill (portable audit playbook)
  G* partial                    →   LLM mode auto-eval
```

[graph-contract.md §10](graph-contract.md#10-implementation-roadmap) · [development.md](development.md).

---

## 10. Contributor quick reference

| Task | Edit |
|------|------|
| New node field or edge type | `ontology/schema.py` → `sync_ontology.py` → pytest |
| Restrict type to `graph_id` | `domains/registry.py` + `graph_context.yaml` |
| Federation join | `graph_context.yaml` + `playbooks.yaml` |
| Agent-visible scope | `domains/export.py` → regenerate JSON |
| Prove live Neo4j | `uv run python scripts/audit_neo4j.py` (L3); `uv run python scripts/audit_ingest_pipeline.py` (L4 batch) |
| Agent grounding eval | [demo-runbook.md §D](demo-runbook.md#part-d--verification--evaluation) |

---

## Related

| Topic | Doc |
|-------|-----|
| General L0–L5, GraphRAG | [ontology-levels-general.md](ontology-levels-general.md) |
| Index | [ontology-levels.md](ontology-levels.md) |
| Naming | [terminology.md](terminology.md) |
| Graph Contract | [graph-contract.md](graph-contract.md) |
| Seeding | [seeding.md](seeding.md) |
