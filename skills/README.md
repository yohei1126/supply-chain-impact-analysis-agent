# Agent Skills

All distributable Agent Skills for this project live under `skills/`.

| Skill | Directory | Purpose |
|-------|-----------|---------|
| `bom-ontology` | [bom-ontology/](bom-ontology/) | Domain schema (`assets/ontology.json`) |
| `bom-graph-explorer` | [bom-graph-explorer/](bom-graph-explorer/) | Exploration workflows (requires bom-ontology) |

## SSOT

| Layer | Location |
|-------|----------|
| Layout (org vs technical boundaries) | [docs/project-layout.md](../docs/project-layout.md) |
| Authoring | `ontology/schema.py` |
| Published JSON (one file) | `skills/bom-ontology/assets/ontology.json` |

```bash
uv run python scripts/sync_ontology.py
```

## Install

```bash
npx skils add <source> --path skills/bom-ontology
npx skils add <source> --path skills/bom-graph-explorer
```

See [Agent Skills specification](https://agentskills.io/specification).
