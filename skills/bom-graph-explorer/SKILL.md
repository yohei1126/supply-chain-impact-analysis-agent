---
name: bom-graph-explorer
description: Explore manufacturing BOM knowledge graphs with strict ontology constraints on LanceGraph, DuckDB, and LanceDB. Use for supplier impact analysis, shortest-path traversal, or vector-to-graph multi-hop exploration in BOM data.
compatibility: Requires bom-ontology (skills/bom-ontology). Optional bom_graph Python package for scripts.
metadata:
  author: bom-knowledge-graph-agent-skill
  version: "1.0"
---

# BOM Graph Explorer (Agent Skill)

Exploration workflows only. Schema: **skills/bom-ontology/assets/ontology.json**.

## Prerequisites

```bash
npx skils add <source> --path skills/bom-ontology
```

## Workflow

1. Load **bom-ontology** → `assets/ontology.json`.
2. Read [references/workflows.md](references/workflows.md).
3. Use tools when Python runtime is available: `bom_supplier_impact`, `bom_supply_path`.

```bash
uv sync
uv run python skills/bom-graph-explorer/scripts/explore_graph.py --seed --mode supplier-impact --supplier-id SUP-001
```

## Additional resources

- [references/ontology.md](references/ontology.md)
- [references/workflows.md](references/workflows.md)
