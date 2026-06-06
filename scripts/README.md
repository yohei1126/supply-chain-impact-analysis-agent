# Scripts

Run from the **repository root** (`data/` paths are relative to cwd).

| Script | Purpose |
|--------|---------|
| `sync_ontology.py` | Regenerate `skills/bom-ontology/assets/ontology.json` from `ontology/schema.py` |
| `seed_complex_bom.py` | Ontology-validated synthetic BOM → LanceDB + DuckDB + vectors (`--reset`) |
| `demo_federation.py` | **E2E federated demo** — [docs/federation-demo-runbook.md](../docs/federation-demo-runbook.md) |
| `demo.py` | Interactive graph + tool exploration demo |
| `demo_hybrid.py` | Interactive vector → RDB → graph demo |
| `demo_agent.py` | Interactive autonomous agent demo (local, no HTTP) |
| `verify_langfuse_telemetry.py` | Check Langfuse keys + list `bom-agent-run` traces |
| `run_docker_stack.sh` | LiteLLM + Langfuse (`docker compose --profile litellm --profile langfuse`) |
| `run_litellm_proxy.sh` | LiteLLM via `uv` only (no Docker; `config/litellm.yaml`) |

Per-domain ingest: `ingest/{ebom,routing,sourcing}.py` — see [ingest/README.md](ingest/README.md).

Non-interactive demos: `DEMO_NONINTERACTIVE=1 uv run python scripts/demo.py`

Federation demo (resets LanceDB):

```bash
uv run python scripts/demo_federation.py --reset
DEMO_NONINTERACTIVE=1 uv run python scripts/demo_federation.py --reset --supplier-id SUP-001
```

Docker profiles (from repo root): `langfuse` only → `docker compose --profile langfuse up -d`

All Docker services are in **`docker-compose.yml`**.
