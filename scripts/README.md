# Scripts

Run from the **repository root** (`data/` paths are relative to cwd).

| Script | Purpose |
|--------|---------|
| `sync_ontology.py` | Regenerate `skills/bom-ontology/assets/ontology.json` from `ontology/schema.py` |
| `seed_complex_bom.py` | Ontology-validated synthetic BOM → LanceDB + DuckDB + vectors (`--reset`) |
| `demo.py` | Interactive graph + tool exploration demo |
| `demo_hybrid.py` | Interactive vector → RDB → graph demo |
| `demo_agent.py` | Interactive autonomous agent demo (local, no HTTP) |

Non-interactive demos: `DEMO_NONINTERACTIVE=1 uv run python scripts/demo.py`

| Script | Purpose |
|--------|---------|
| `verify_langfuse_telemetry.py` | Check Langfuse keys + list `bom-agent-run` traces |
| `run_docker_stack.sh` | LiteLLM + Langfuse (`docker compose --profile litellm --profile langfuse`) |
| `run_litellm_proxy.sh` | LiteLLM via `uv` only (no Docker; `config/litellm.yaml`) |

Docker profiles (from repo root): `langfuse` only → `docker compose --profile langfuse up -d`

All Docker services are in **`docker-compose.yml`**.
