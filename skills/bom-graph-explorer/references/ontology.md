# Ontology for BOM graph exploration

Schema is not in this skill. Install **bom-ontology**:

**`skills/bom-ontology/assets/ontology.json`**

```bash
npx skils add <source> --path skills/bom-ontology
```

| Context | Schema source |
|---------|----------------|
| Agent host | bom-ontology → `assets/ontology.json` |
| Python pipeline | `ontology/schema.py` (generates the JSON above) |

## Allowed edges (summary)

| Edge | From | To |
|------|------|-----|
| `USED_IN` | Component | Product |
| `PRODUCED_BY` | Product | Process |
| `SUPPLIED_BY` | Component | Supplier |
| `INPUT_OF` | Component | Process |

Full definitions: `assets/ontology.json` only.
