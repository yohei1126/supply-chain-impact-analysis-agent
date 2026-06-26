# Seeding synthetic BOM data

Demo and agent runtime need Neo4j graph data and DuckDB component master under `data/`. **Do not hand-edit Neo4j databases or DuckDB files.** Load synthetic BOM through the Python stores so every node and edge is validated against the ontology defined in `ontology/schema.py`.

**Audience:** coding agents, contributors, pipeline engineers.

**Related:** [AGENTS.md](../AGENTS.md) · [terminology.md](terminology.md) · [setup-and-demos.md](setup-and-demos.md) · [development.md](development.md) · [demo-runbook.md](demo-runbook.md)

---

## One definition, two consumers (not two competing schemas)

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

## What gets validated on each write

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

## Validation lifecycle (before / during / after load)

Ontology **validation** (define + prove) runs at several stages; **reasoning (L5)** is not used. Full table with purpose and scope: [ontology-levels-project.md §5](ontology-levels-project.md#5-validation-timing-in-this-repo).

| Stage | What runs | Goal |
|-------|-----------|------|
| **Pre-load** | `validate_all_datasets()` | Catch bad payloads in memory before Neo4j writes |
| **On write** | Pydantic + domain allow-list on `add_node` / `add_edge` | Reject invalid rows at ingest |
| **After load** | `require_l3_conformance` — L3 Cypher + SHACL + L4 `on_ingest` gates | Prove the loaded graph conforms |

```bash
# Seed runs on-write validation; ends with post-load proof:
uv run python scripts/seed_complex_bom.py --reset

# Manual post-load audit only:
uv run python scripts/audit_neo4j.py
```

## Seed commands (from repository root)

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

## Customize or extend the dataset

1. Edit **`pipeline/demo/sample_data.py`** (`SUPPLIERS`, `PRODUCTS`, `PROCESSES`, `COMPONENT_BOM`, `PRODUCT_PROCESSES`).
2. Stay within allowed node types and edge pairs (see `ALLOWED_EDGES` in `schema.py` or `ontology.json`).
3. Re-seed with `--reset`:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

`scripts/demo*.py` also call `seed_complex_bom()` but do not pass `--reset`; prefer the dedicated seed script when refreshing demo data before UI or API work.

## Verify after seeding

```bash
uv run python scripts/seed_complex_bom.py --reset
uv run pytest -q tests/test_schema.py tests/test_graph_store.py tests/test_component_master_store.py

# Quick exploration (also seeds if --seed):
uv run python skills/bom-graph-explorer/scripts/explore_graph.py --seed \
  --mode supplier-impact --supplier-id SUP-002
```

Then start CLI demos or the full stack — [setup-and-demos.md](setup-and-demos.md), [demo-runbook.md](demo-runbook.md).
