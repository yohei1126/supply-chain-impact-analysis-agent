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
| **Federation agreement** | L4 — Graph Contract | **Partial** (composer + on_federate; production connector metadata pending) |
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
| **L4** Graph Contract | **Partial** (production connector ingest metadata) |
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

### L4 — Graph Contract — **Partial**

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

### L5 — Reasoning — **Out of scope**

No OWL reasoner. Agent uses LLM + **deterministic tools** (modern substitute).

---

## 5. Validation timing in this repo

| When | Mechanism | Levels | Done? |
|------|-----------|--------|-------|
| Authoring | `schema.py`, YAML, `registry.py` | L0–L2, L4 docs | Yes |
| Pre-load | `validate_all_datasets()` | L1–L2 | Yes |
| On write | Pydantic + domain asserts; storage-layer-only mutations | L1–L2 | Yes |
| CI | pytest, export drift tests, **L3 audit** (`seed_complex_bom` + `audit_neo4j.py`) | L1–L3 | Yes |
| After load | Cypher / SHACL | L3 | **Done** (Cypher audit + Neosemantics SHACL + pytest) |
| At federate | Join logic + on_federate gates | L4 | Yes |

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
  Today                         Next
  L0–L3 write-time + post-load  →   production connector ingest metadata (L4 P5)
  L4 composer + on_federate     →   async on_ingest audit pipeline
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
| Prove live Neo4j | `uv run python scripts/audit_neo4j.py` (L3 Cypher + SHACL); re-seed for empty demos |
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
