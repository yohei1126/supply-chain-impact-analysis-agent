---
name: bom-ontology
description: Language-neutral BOM graph schema and edge constraints for manufacturing knowledge graphs. Use when validating node types, allowed relationships, or graph write policies before exploration or pipeline ingestion.
compatibility: No runtime required; read assets/ontology.json. Pair with bom-graph-explorer for workflows.
metadata:
  author: bom-knowledge-graph-agent-skill
  version: "1.0"
---

# BOM graph ontology (Agent Skill)

Domain schema only — no exploration workflows.

## Schema SSOT

Load **[assets/ontology.json](assets/ontology.json)** (the only `ontology.json` in this repository).

## Install

```bash
npx skils add <source> --path skills/bom-ontology
```

## Related packages

| Package | Path |
|---------|------|
| **bom-ontology** (this skill) | `skills/bom-ontology/` |
| **bom-graph-explorer** | `skills/bom-graph-explorer/` |
| **Python authoring** | `bom_graph/schema.py` → `scripts/sync_ontology.py` |
