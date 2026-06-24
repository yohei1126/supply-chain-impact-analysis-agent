# Ontology layer (shared technical boundary)

Platform-independent definitions for the manufacturing supply-chain knowledge graph:
global schema, validation constraints, and the cross-domain **Graph Contract**.

Organization-owned domain slices live under **`domains/`** (bundle, pipeline, tools per team).
This directory holds what every domain shares for federation consistency.

## Dependencies

| Allowed | Not allowed (belongs elsewhere) |
|---------|----------------------------------|
| Python stdlib | LanceDB, DuckDB, FastAPI, httpx, Langfuse, LiteLLM |
| **Pydantic** (models + validators) | Agent Skills, tool registries, HTTP servers |
| | Domain pipelines (`domains/*/pipeline.py`), runtime stores (`app/`) |

`ontology/` is imported by `domains/`, `app/`, `pipeline/demo/`, and export scripts.
It must not import those layers back.

## Layout

```
ontology/
  schema.py                 SSOT: node/edge Pydantic models, ALLOWED_EDGES, validators
  contract/
    graph_context.yaml      Graph Contract SSOT: identity bindings, joins, quality gates (storage-agnostic)
  assets/
    ontology.json             generated JSON Schema export (run scripts/sync_ontology.py)
```

Domain partitioning (`DOMAIN_GRAPHS`, owner metadata) lives in **`domains/registry.py`**
and **`domains/*/bundle.py`**, not here. The agent **graph context** bundle (`graph-context.json`) is exported from **`domains/export.py`** via `scripts/sync_ontology.py`. Terminology: [docs/terminology.md](../docs/terminology.md) · Utilization levels: [docs/ontology-levels.md](../docs/ontology-levels.md) ([general](../docs/ontology-levels-general.md), [project](../docs/ontology-levels-project.md)) · Graph context: [docs/graph-context.md](../docs/graph-context.md).

## Authoring workflow

1. Edit `schema.py` when node/edge shapes or global constraints change.
2. Run `uv run python scripts/sync_ontology.py` to refresh `ontology/assets/ontology.json`.
3. Run `uv run pytest -q tests/test_schema.py tests/test_ontology_isolation.py`.

When a domain gains or loses node/edge types, update **`domains/registry.py`** and the
matching **`domains/<name>/bundle.py`** in the same change.
