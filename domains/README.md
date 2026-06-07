# Domain modules (organization boundary)

Each subdirectory is owned by a different enterprise team. A domain packages:

| Module | Role |
|--------|------|
| `bundle.py` | Org metadata — owner team, allowed nodes/edges, source systems |
| `pipeline.py` | Ingest into the domain Lance path (demo uses `pipeline/demo/sample_data.py`) |
| `tools.py` | Domain-scoped exploration (future; cross-domain tools stay in `app/`) |

## Shared technical boundary (do not duplicate here)

| Layer | Location | Role |
|-------|----------|------|
| Schema + validators | `ontology/schema.py` | Global SSOT (`Component`, `ALLOWED_EDGES`, …) |
| Graph Contract | `ontology/contract/graph_context.yaml` | Bridge Keys, joins, quality gates (YAML SSOT) |
| Domain registry | `domains/registry.py` | Which graph owns which node/edge types |
| Federation runtime | `app/federation/` | `LanceGraphStore` facade, playbooks |
| Agent | `app/agent/` | Cross-domain planner and UI |

Domains **import** `ontology.schema` for validation rules and receive a graph store from `app` at runtime. They must not import agent or skill layers.

## Layout

```
domains/
  registry.py           partition rules (feeds federation)
  ebom/                 engineering / PLM
  routing/              manufacturing / MES
  sourcing/             procurement / SRM
```

Demo orchestration that runs all three pipelines: `pipeline/demo/seed.py`.

Per-domain ingest entrypoints: `scripts/ingest/{ebom,routing,sourcing}.py`.

Full layout guide: [docs/project-layout.md](../docs/project-layout.md).
