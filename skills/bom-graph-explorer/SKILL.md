---
name: bom-graph-explorer
description: Compose and validate BOM graph Cypher using bom-ontology assets and generated query catalogs. Use for supplier impact, supply-path, or component search exploration when the agent must interpret context and build domain-scoped queries.
compatibility: Requires bom-ontology (skills/bom-ontology). Read generated assets under assets/; do not duplicate schema tables in prompts.
metadata:
  author: bom-knowledge-graph-agent-skill
  version: "1.1"
---

# BOM Graph Explorer (Agent Skill)

Ontology-driven **Cypher composition** for federated BOM graphs. Execution lives in the app layer; this skill teaches how to read generated assets and compose valid queries.

## Prerequisites

```bash
npx skils add <source> --path skills/bom-ontology
npx skils add <source> --path skills/bom-graph-explorer
```

## Read order (generated assets — do not hand-edit)

1. **bom-ontology** → `assets/ontology.json` — node shapes and `allowed_pairs`.
2. **This skill** → `assets/graph-context.json` — graph context (domain graphs and federation bridges).
3. **This skill** → `assets/query-catalog.json` — named query recipes and federation steps.
4. **This skill** → `assets/cypher-engine-profile.json` — Neo4j dialect limits.
5. **references/cypher-compose.md** — composition checklist (prose only).

Regenerate all JSON after schema or query changes:

```bash
uv run python scripts/sync_ontology.py
```

## Agent tools (invoke — do not reimplement in Cypher prose)

| Tool | When |
|------|------|
| `bom_supplier_impact` | Supplier disruption → components and products |
| `bom_supply_path` | Path from component to product |

Tool names are stable; internal execution may use catalog queries and federation joins.

## Additional resources

- [references/cypher-compose.md](references/cypher-compose.md) — how to compose Cypher from assets
- [references/workflows.md](references/workflows.md) — scenario → catalog recipe mapping
- [references/ontology.md](references/ontology.md) — where schema lives (pointer only)
