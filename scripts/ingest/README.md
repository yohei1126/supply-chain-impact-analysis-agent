# Domain ingest scripts (demo)

Each script loads synthetic data through the matching domain pipeline under `domains/<domain>/pipeline.py`.

| Script | Domain | Lance path | Owner (conceptual) |
|--------|--------|------------|--------------------|
| `ebom.py` | Product structure | `data/lancedb/ebom/` | Engineering / PLM |
| `routing.py` | Manufacturing routing | `data/lancedb/routing/` | Manufacturing / MES |
| `sourcing.py` | Supply and sourcing | `data/lancedb/sourcing/` | Procurement / SRM |

Shared schema: `ontology/schema.py`. Domain bundles: `domains/*/bundle.py`.  
Federation contract: `ontology/contract/graph_context.yaml`.

For the full cross-domain demo, prefer:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

Run a single domain (requires component nodes for edges):

```bash
uv run python scripts/ingest/sourcing.py
```
