# Domain ingest scripts (production connector pattern)

Each script loads synthetic data through a **registered production connector**
(`pipeline/connectors/registry.py`) with pinned `graph_contract_version`, `as_of`,
and `source_system` metadata stamped on every node.

| Script | Connector | Domain | Source system |
|--------|-----------|--------|---------------|
| `ebom.py` | `plm-ebom` | Product structure | PLM |
| `routing.py` | `mes-routing` | Manufacturing routing | MES |
| `sourcing.py` | `srm-sourcing` | Supply and sourcing | SRM |

Shared schema: `ontology/schema.py`. Domain bundles: `domains/*/bundle.py`.  
Graph Contract: `ontology/contract/graph_context.yaml`.

For the full cross-domain demo, prefer:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

Run a single domain (requires component nodes for edges):

```bash
uv run python scripts/ingest/sourcing.py
```

Override export timestamp (ISO-8601 UTC):

```bash
CONNECTOR_AS_OF=2026-06-02T12:00:00Z uv run python scripts/ingest/ebom.py
```
