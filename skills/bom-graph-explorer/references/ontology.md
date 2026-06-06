# Ontology pointers (no schema copy)

Full node and edge definitions are **not** in this skill.

| Need | Source |
|------|--------|
| Node fields, `allowed_pairs` | `bom-ontology` → `assets/ontology.json` |
| Domain graphs, federation bridges | `bom-graph-explorer` → `assets/graph-context.json` |
| Named Cypher recipes | `bom-graph-explorer` → `assets/query-catalog.json` |
| Engine dialect limits | `bom-graph-explorer` → `assets/cypher-engine-profile.json` |
| Authoring / validation (Python) | `ontology/schema.py` |

Install bom-ontology first, then load this skill's generated assets. Regenerate with:

```bash
uv run python scripts/sync_ontology.py
```

Do **not** duplicate edge tables in skill markdown — drift tests enforce JSON sync with `schema.py`.
