# AGENTS.md

High-level guide for agents working in this repository.

**Detailed instructions** (seeding, setup, demos, agent runtime): [docs/agent-guide.md](docs/agent-guide.md).

## 1. Core Working Principles

- **Language:** Repository docs (`*.md`, `docs/`), docstrings, inline comments, and user-facing error messages are **English**. Skill prompts may stay language-neutral; do not add Japanese (or other locale) strings in Python unless there is an explicit i18n requirement.
- **Authoring SSOT:** `ontology/schema.py` (Pydantic). The `ontology/` tree depends only on Pydantic and stdlib — no Neo4j, FastAPI, or agent imports.
- **Published ontology SSOT:** `skills/bom-ontology/assets/ontology.json` (single generated file).
- **Graph context contract:** `ontology/contract/graph_context.yaml` (cross-domain federation rules).
- **All Agent Skills** live under `skills/` (`bom-ontology`, `bom-graph-explorer`).
- Regenerate ontology and explorer assets: `uv run python scripts/sync_ontology.py`.
- Workflow skills must not embed a second copy of `ontology.json`.
- No tool-specific install copies under `.cursor/skills/`.

## 2. Key Components

| Layer | Location | Role |
|-------|----------|------|
| Layout guide | [docs/project-layout.md](docs/project-layout.md) | Why `ontology/`, `domains/`, `app/` exist |
| Ontology | `ontology/` | Platform-independent shared schema + graph context contract (Pydantic only) |
| Domains | `domains/` | Org-owned slices: bundle, pipeline, tools per `ebom` / `routing` / `sourcing` |
| Pipeline | `pipeline/demo/` | Cross-domain demo seed orchestration |
| Application | `app/` | Storage, federation facade, component master store, cross-domain tools, agent |
| Ontology skill | `skills/bom-ontology/` | Distributable schema for agents (`skills/bom-ontology/assets/ontology.json`) |
| Exploration skill | `skills/bom-graph-explorer/` | Cypher compose protocol + generated `graph-context.json`, `query-catalog.json`, `cypher-engine-profile.json` |

## 3. Ontology vs validation vs exploration

| Concern | Where it lives | Notes |
|---------|----------------|-------|
| **What is allowed** (schema) | `bom-ontology` skill + `ontology/schema.py` | One `ontology.json`; skill is language-neutral |
| **Whether data complies** (validation) | `ontology/schema.py` (Pydantic) | Deterministic; runs in pipelines/tests, not in Skill code |
| **How to explore the graph** | `bom-graph-explorer` skill + `app/` stores | Read-only traversal tools |

A separate **`bom-validate` Agent Skill is not required** for the default setup: writes already go through Pydantic validators (`validate_node_payload`, `RelationEdge`). Add `skills/bom-validate/` only if you need a portable **audit playbook** for agents without the Python package (checklist + violation report format, still reading `bom-ontology`).

Install skills from `skills/` only. Do not copy them into `.cursor/skills/` inside this repository.

Seeding, validation on write, and demo commands: [docs/agent-guide.md](docs/agent-guide.md#seeding-synthetic-bom-data-ontology-validation).

## 4. Change Workflow

1. Edit `ontology/schema.py`.
2. Run `uv run python scripts/sync_ontology.py`.
3. Update skill docs if workflows changed.
4. `uv run pytest -q`.

## 5. Tests and quality

See [docs/testing-and-quality.md](docs/testing-and-quality.md) for pytest, ruff, mypy, CI, and PR checklists.

```bash
uv sync --extra dev
uv run ruff check ontology domains pipeline app tests scripts
uv run mypy ontology domains pipeline app
uv run pytest -q
```

## 6. Done Criteria

- One `ontology.json` under `skills/bom-ontology/assets/`.
- `uv run pytest -q` succeeds.
