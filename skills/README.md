# Agent Skills

All distributable Agent Skills for this project live under `skills/`.

| Skill | Directory | Purpose |
|-------|-----------|---------|
| `bom-ontology` | [bom-ontology/](bom-ontology/) | Domain schema (`assets/ontology.json`) |
| `bom-graph-explorer` | [bom-graph-explorer/](bom-graph-explorer/) | Cypher composition + query catalog (requires bom-ontology) |

## SSOT

| Layer | Location |
|-------|----------|
| Layout (org vs technical boundaries) | [docs/project-layout.md](../docs/project-layout.md) |
| Schema authoring | `ontology/schema.py` |
| Query recipe authoring | `ontology/cypher_builder.py` |
| Domain / federation export | `domains/export.py` |
| Published schema JSON | `skills/bom-ontology/assets/ontology.json` |
| Published explorer JSON | `skills/bom-graph-explorer/assets/*.json` |

```bash
uv run python scripts/sync_ontology.py
```

Regenerates ontology JSON and bom-graph-explorer assets (`graph-context.json`, `query-catalog.json`, `cypher-engine-profile.json`). Skill markdown stays prose-only (compose protocol); do not duplicate edge tables in `.md` files.

## Install

```bash
npx skils add <source> --path skills/bom-ontology
npx skils add <source> --path skills/bom-graph-explorer
```

See [Agent Skills specification](https://agentskills.io/specification).
