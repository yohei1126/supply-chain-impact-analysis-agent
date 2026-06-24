# Testing, lint, and static analysis

How to verify changes in this repository: unit tests, optional linters, and architectural guardrails.

**Audience:** developers and coding agents.

**Related:** [development.md](development.md) (setup) · [project-layout.md](project-layout.md) (layer boundaries) · [AGENTS.md](../AGENTS.md) (principles) · [seeding.md](seeding.md) · [setup-and-demos.md](setup-and-demos.md)

---

## 1. Prerequisites

From the repository root:

```bash
uv sync
```

Python **3.10+** is required (`requires-python` in [`pyproject.toml`](../pyproject.toml)).

Optional extras (not needed for the default test suite):

```bash
uv sync --extra gateway          # LiteLLM CLI
uv sync --extra observability    # Langfuse client
uv sync --extra dev              # ruff + mypy (lint / type check)
```

---

## 2. Unit tests (pytest)

**Test runner:** [pytest](https://docs.pytest.org/) (declared in project dependencies).

### 2.1 Run the full suite

```bash
uv run pytest -q
```

Expected: all tests pass (currently **54** tests under `tests/`). A passing run is the minimum **done criteria** in [AGENTS.md](../AGENTS.md).

Verbose output:

```bash
uv run pytest -v
```

Stop on first failure:

```bash
uv run pytest -x
```

### 2.2 Run a single file or test

```bash
uv run pytest -q tests/test_schema.py
uv run pytest -q tests/test_lance_graph_store.py::test_supplier_impact
```

### 2.3 Tests by layer

| Layer / concern | Test modules |
|-----------------|--------------|
| Ontology (schema) | `tests/test_schema.py`, `tests/test_skill_ontology_asset.py`, `tests/test_ontology_isolation.py` |
| Domain partition | `tests/test_domain_graphs.py`, `tests/test_domain_layout.py` |
| Graph store | `tests/test_lance_graph_store.py`, `tests/test_exploration.py`, `tests/test_graph_viz.py` |
| Federation analysis | `tests/test_federation_analysis.py` |
| Hybrid (vector + RDB + graph) | `tests/test_hybrid_store.py` |
| Agent / API | `tests/test_agent.py`, `tests/test_llm_client.py`, `tests/test_explain.py`, `tests/test_user_response.py`, `tests/test_run_report.py` |
| Skills CLI | `tests/test_skill_script.py` |

Quick smoke after ontology or store changes:

```bash
uv run pytest -q \
  tests/test_schema.py \
  tests/test_ontology_isolation.py \
  tests/test_domain_layout.py \
  tests/test_lance_graph_store.py \
  tests/test_hybrid_store.py
```

After `ontology/schema.py` or `cypher_builder.py` edits, also run sync + asset drift check:

```bash
uv run python scripts/sync_ontology.py
uv run pytest -q tests/test_skill_ontology_asset.py tests/test_skill_agent_assets.py
```

See [agent-skill-assets.md](agent-skill-assets.md) for catalog locations, ownership, and multi-agent versioning.

### 2.4 Tests and local `.env`

Most tests do **not** read `.env`. Exceptions:

| Test | Note |
|------|------|
| `tests/test_llm_client.py` | Uses `monkeypatch` for env vars; clears `OPENAI_MODEL` so local `.env` does not override `LLM_MODEL` |

Agent integration tests use FastAPI `TestClient` and run **offline** (no LiteLLM/Langfuse required).

### 2.5 Planned tests (roadmap)

Not implemented yet — see [development.md](development.md) roadmap:

| Phase | Future module |
|-------|----------------|
| P1 | `tests/test_disruption_interpret.py`, `tests/test_playbook_registry.py` |
| P2 | `tests/test_sourcing_tools.py` |
| P3 | `tests/test_domain_traversal.py`, `tests/test_routing_tools.py` |
| P4 | `tests/test_federation.py`, `tests/test_agent_multiround.py`, `tests/test_mitigations.py` |

---

## 3. Architectural static check (in-repo)

`tests/test_ontology_isolation.py` parses `ontology/**/*.py` with AST and asserts:

- No imports from `app`, `pipeline`, `domains`, LanceDB, FastAPI, etc.
- Only **Pydantic** (+ stdlib) as third-party imports

This enforces the platform-independent boundary described in [ontology/README.md](../ontology/README.md).

```bash
uv run pytest -q tests/test_ontology_isolation.py
```

---

## 4. Lint (ruff)

[Ruff](https://docs.astral.sh/ruff/) is the recommended linter. Install via the optional **`dev`** extra:

```bash
uv sync --extra dev
```

### 4.1 Check

```bash
uv run ruff check ontology domains pipeline app tests scripts
```

Auto-fix safe issues:

```bash
uv run ruff check --fix ontology domains pipeline app tests scripts
```

### 4.2 Format

Ruff can also format Python (optional):

```bash
uv run ruff format ontology domains pipeline app tests scripts
uv run ruff format --check ontology domains pipeline app tests scripts
```

Configuration lives in [`pyproject.toml`](../pyproject.toml) under `[tool.ruff]`.

Ruff is **not enforced in CI** yet. A first run may report import-order (`I`) issues; many are auto-fixable with `--fix`. Style-only findings do not block merging unless your team adopts ruff as a gate.

---

## 5. Static type checking (mypy)

[Mypy](https://mypy.readthedocs.io/) is optional and included in the **`dev`** extra.

```bash
uv sync --extra dev
uv run mypy ontology domains pipeline app
```

Settings in [`pyproject.toml`](../pyproject.toml) under `[tool.mypy]`. The codebase adopts typing gradually — mypy is advisory until CI enforces it.

Skip tests and scripts initially:

```bash
uv run mypy ontology domains app/federation app/storage
```

---

## 6. Recommended workflows

### Before every commit (minimal)

```bash
uv run pytest -q
```

### After ontology or schema changes

```bash
uv run python scripts/sync_ontology.py
uv run pytest -q tests/test_schema.py tests/test_skill_ontology_asset.py tests/test_ontology_isolation.py
git add ontology/assets/ontology.json skills/bom-ontology/assets/ontology.json
```

### Before opening a PR (full local gate)

```bash
uv sync --extra dev
uv run ruff check ontology domains pipeline app tests scripts
uv run mypy ontology domains pipeline app
uv run pytest -q
```

One-liner:

```bash
uv sync --extra dev && \
  uv run ruff check ontology domains pipeline app tests scripts && \
  uv run mypy ontology domains pipeline app && \
  uv run pytest -q
```

---

## 7. What is not covered yet

| Tool | Status |
|------|--------|
| GitHub Actions CI | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — ruff, mypy, Markdown link check, **unit tests (no Neo4j)**, **L3 Neo4j audit** (seed + `audit_neo4j.py`), full pytest with skip guard (Neo4j service) on PRs and pushes to `main` |
| Pre-commit hooks | Not configured |
| Coverage (`pytest-cov`) | Not configured |
| External URL link checker | Not configured (optional: lychee) |

### Markdown internal links

Relative links in `docs/` and `*.md` must target existing files or directories under the repo. CI runs [`tests/test_markdown_links.py`](../tests/test_markdown_links.py) in the static-analysis job; it is also included in `uv run pytest -q`.

```bash
uv run pytest -q tests/test_markdown_links.py
```

Roadmap items mentioned inline in prose (e.g. `app/federation/composer.py`) are intentional **planned** paths — only relative markdown hyperlinks are checked.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `test_llm_client` model mismatch | `.env` sets `OPENAI_MODEL` | Test clears env; ensure you run via `uv run pytest`, not a shell with stale exports |
| Lance tests fail on stale data | Old `data/lancedb` | `uv run python scripts/seed_complex_bom.py --reset` |
| `test_skill_ontology_asset` fails | Edited `schema.py` without sync | `uv run python scripts/sync_ontology.py` |
| Import errors after layout change | Editable install stale | `uv sync` |

---

## 9. Related documentation

| Topic | Doc |
|-------|-----|
| Project layout | [project-layout.md](project-layout.md) |
| Developer setup | [development.md](development.md) |
| Agent change workflow | [AGENTS.md](../AGENTS.md) · [seeding.md](seeding.md) · [setup-and-demos.md](setup-and-demos.md) |
