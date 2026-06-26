# Testing, lint, and static analysis

How to verify changes: unit tests, Neo4j integration tests, lint, and type checking.

**Audience:** developers and coding agents.

**Related:** [setup-and-demos.md](setup-and-demos.md) (start app) · [development.md](development.md) · [seeding.md](seeding.md) · [AGENTS.md](../AGENTS.md)

---

## 1. Prerequisites

From the repository root:

```bash
uv sync --extra dev    # pytest + ruff + mypy
```

Python **3.10+** (`requires-python` in [`pyproject.toml`](../pyproject.toml)).

Optional extras:

```bash
uv sync --extra gateway          # LiteLLM CLI
uv sync --extra observability    # Langfuse client
```

---

## 2. Test tiers

| Tier | Neo4j required | n10s plugin | Typical use |
|------|----------------|-------------|-------------|
| **Offline** | No | No | Fast feedback; CI static-analysis job |
| **Integration** | Yes | Yes (for SHACL tests) | L3 audit, federation, graph store |
| **Full suite** | Yes (no skips) | Yes | Pre-push; matches CI `test` job |

Without Neo4j, graph-dependent tests **skip** automatically (`pytest -rs` lists them).

---

## 3. Start Neo4j for local integration tests

### Docker Compose (matches CI)

```bash
colima start    # macOS, if Docker is not running
docker compose --profile neo4j up -d
```

The repo `neo4j` service sets `NEO4J_PLUGINS='["n10s"]'` for L3 SHACL validation.

Or use the full stack script (Neo4j + LiteLLM + Langfuse):

```bash
./scripts/start_stack.sh
```

Default env (same as `.env.example`):

```bash
export BOM_NEO4J_URI=bolt://localhost:7687
export BOM_NEO4J_USER=neo4j
export BOM_NEO4J_PASSWORD=password
```

Verify connectivity:

```bash
uv run python -c "from app.storage.neo4j_config import get_driver, verify_connectivity; d=get_driver(); verify_connectivity(d); d.close(); print('OK')"
```

Verify n10s SHACL procedures:

```bash
uv run python -c "
from app.storage.neo4j_config import get_driver
from app.validation.neo4j_shacl_audit import neosemantics_shacl_available
d = get_driver()
with d.session() as s:
    print('n10s SHACL:', neosemantics_shacl_available(s))
d.close()
"
```

Seed before integration tests or UI work:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

L3 conformance audit (Cypher + Pydantic + SHACL):

```bash
BOM_L3_REQUIRE_SHACL=1 uv run python scripts/audit_neo4j.py
```

---

## 4. Run tests (pytest)

**Test runner:** [pytest](https://docs.pytest.org/) (project dependency).

### 4.1 Full suite

```bash
uv run pytest -q
```

Show skips (recommended locally):

```bash
uv run pytest -q -rs
```

Currently **~104** tests collected; **~40+** may skip without Neo4j. CI fails if any test skips in the Neo4j job.

Verbose / stop on first failure:

```bash
uv run pytest -v
uv run pytest -x
```

### 4.2 Offline smoke (no Neo4j)

Same subset as CI `static-analysis` job:

```bash
uv run pytest -q \
  tests/test_schema.py \
  tests/test_ontology_isolation.py \
  tests/test_skill_ontology_asset.py \
  tests/test_skill_agent_assets.py \
  tests/test_agent.py \
  tests/test_llm_client.py \
  tests/test_user_response.py \
  tests/test_explain.py \
  tests/test_run_report.py \
  tests/test_cypher_builder.py \
  tests/test_domain_layout.py \
  tests/test_domain_graphs.py::test_graph_for_edge_mapping \
  tests/test_write_path_guardrails.py \
  tests/test_graph_contract.py \
  tests/test_composer.py \
  tests/test_ingest_metadata.py \
  tests/test_shacl_codegen.py \
  tests/test_cli_smoke.py::test_sync_ontology_cli \
  tests/test_markdown_links.py
```

### 4.3 Neo4j integration

Requires running Neo4j (and n10s for SHACL modules):

```bash
uv run pytest -q tests/test_l3_audit.py tests/test_shacl_audit.py
uv run pytest -q tests/test_federation.py tests/test_federation_analysis.py
uv run pytest -q tests/test_graph_store.py tests/test_exploration.py
```

Single file or test:

```bash
uv run pytest -q tests/test_schema.py
uv run pytest -q tests/test_shacl_audit.py::test_shacl_audit_passes_after_domain_load
```

### 4.4 Tests by layer

| Layer / concern | Test modules |
|-----------------|--------------|
| Ontology (schema) | `tests/test_schema.py`, `tests/test_skill_ontology_asset.py`, `tests/test_ontology_isolation.py` |
| SHACL codegen | `tests/test_shacl_codegen.py` |
| L3 / SHACL audit | `tests/test_l3_audit.py`, `tests/test_shacl_audit.py` |
| Graph Contract / composer | `tests/test_graph_contract.py`, `tests/test_composer.py` |
| Ingest metadata | `tests/test_ingest_metadata.py` |
| Domain partition | `tests/test_domain_graphs.py`, `tests/test_domain_layout.py` |
| Graph store / exploration | `tests/test_graph_store.py`, `tests/test_exploration.py`, `tests/test_graph_viz.py` |
| Federation | `tests/test_federation.py`, `tests/test_federation_analysis.py` |
| Hybrid (vector + RDB + graph) | `tests/test_hybrid_store.py` |
| Agent / API | `tests/test_agent.py`, `tests/test_llm_client.py`, `tests/test_user_response.py`, … |
| Write-path guardrails | `tests/test_write_path_guardrails.py` |
| Skills CLI | `tests/test_skill_script.py` |
| Markdown links | `tests/test_markdown_links.py` |

After `ontology/schema.py` edits:

```bash
uv run python scripts/sync_ontology.py
uv run pytest -q tests/test_skill_ontology_asset.py tests/test_shacl_codegen.py tests/test_skill_agent_assets.py
git add ontology/assets/ ontology.json skills/bom-ontology/assets/ontology.json skills/bom-graph-explorer/assets/
```

### 4.5 Tests and `.env`

Most tests do **not** read `.env`. Agent tests use FastAPI `TestClient` and run **offline** (no LiteLLM/Langfuse required).

| Test | Note |
|------|------|
| `tests/test_llm_client.py` | Uses `monkeypatch` for env; clears `OPENAI_MODEL` so local `.env` does not override |

---

## 5. Lint and format (ruff)

Install via **`dev`** extra (included above).

```bash
uv run ruff check ontology domains pipeline app tests scripts
uv run ruff check --fix ontology domains pipeline app tests scripts
uv run ruff format ontology domains pipeline app tests scripts
uv run ruff format --check ontology domains pipeline app tests scripts
```

Config: [`pyproject.toml`](../pyproject.toml) `[tool.ruff]`.

---

## 6. Static type checking (mypy)

```bash
uv run mypy ontology domains pipeline app
```

Config: [`pyproject.toml`](../pyproject.toml) `[tool.mypy]`.

---

## 7. Recommended workflows

### Before every commit (minimal)

```bash
uv run pytest -q tests/test_schema.py tests/test_shacl_codegen.py tests/test_agent.py
```

### Before opening a PR (full local gate)

```bash
uv sync --extra dev
uv run ruff check ontology domains pipeline app tests scripts
uv run ruff format --check ontology domains pipeline app tests scripts
uv run mypy ontology domains pipeline app
uv run python scripts/sync_ontology.py
git diff --exit-code -- ontology/assets/ skills/bom-ontology/assets/ontology.json skills/bom-graph-explorer/assets/
uv run pytest -q -rs
```

One-liner:

```bash
uv sync --extra dev && \
  uv run ruff check ontology domains pipeline app tests scripts && \
  uv run mypy ontology domains pipeline app && \
  uv run pytest -q -rs
```

With Neo4j running, also:

```bash
uv run python scripts/seed_complex_bom.py --reset
BOM_L3_REQUIRE_SHACL=1 uv run python scripts/audit_neo4j.py --quiet
```

---

## 8. CI (GitHub Actions)

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

| Job | What it runs |
|-----|----------------|
| **static-analysis** | ruff, mypy, markdown links, ontology/SHACL asset drift, offline pytest subset |
| **test** | Neo4j 5 + n10s service → seed + L3 audit (`BOM_L3_REQUIRE_SHACL=1`) → full pytest (skips forbidden) |
| **langfuse-smoke** | Optional; skips if secrets missing |

---

## 9. Architectural static check

`tests/test_ontology_isolation.py` ensures `ontology/` imports only Pydantic + stdlib.

```bash
uv run pytest -q tests/test_ontology_isolation.py
```

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Many tests skipped | Neo4j not running | `docker compose --profile neo4j up -d` or `./scripts/start_stack.sh` |
| `Connection refused` on `:7687` | Colima/Docker stopped | `colima start`; wait for Neo4j healthy |
| SHACL audit fails: n10s missing | Plain Neo4j without plugin | Use repo `docker-compose.yml` neo4j profile or `NEO4J_PLUGINS='["n10s"]'` |
| `UriNamespaceHasNoAssociatedPrefix` | Stale `bom-shapes.ttl` | `uv run python scripts/sync_ontology.py` |
| `test_skill_ontology_asset` / `test_shacl_codegen` fails | Edited `schema.py` without sync | `uv run python scripts/sync_ontology.py` |
| Empty Supply Chain Map in UI | Stale or empty Neo4j | `uv run python scripts/seed_complex_bom.py --reset` |
| `test_llm_client` model mismatch | `.env` sets `OPENAI_MODEL` | Run via `uv run pytest`; test clears env |
| Seed fails mid-pipeline | Partial graph from crashed run | `seed_complex_bom.py --reset` |
| Import errors after layout change | Stale editable install | `uv sync` |

---

## 11. Not configured yet

| Tool | Status |
|------|--------|
| Pre-commit hooks | Not configured |
| Coverage (`pytest-cov`) | Not configured |
| External URL link checker | Not configured |

---

## 12. Related documentation

| Topic | Doc |
|-------|-----|
| Start app / demos | [setup-and-demos.md](setup-and-demos.md) |
| Developer setup | [development.md](development.md) |
| Seeding | [seeding.md](seeding.md) |
| L3 / SHACL levels | [ontology-levels-project.md](ontology-levels-project.md) |
| Agent change workflow | [AGENTS.md](../AGENTS.md) |
