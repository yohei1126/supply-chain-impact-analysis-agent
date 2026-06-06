# BOM Knowledge Graph Agent

Explore manufacturing BOMs with an ontology-validated graph, hybrid search (vector + SQL + graph), and optional LLM-assisted analysis.

This repository bundles:

- **`ontology/`** — shared schema, constraints, graph-context contract (technical SSOT)
- **`domains/`** — organization-owned domain slices (ebom, routing, sourcing)
- **`pipeline/demo/`** — cross-domain demo seed orchestration
- **`app/`** — federation, stores, agent (shared runtime)
- **`skills/`** — distributable Agent Skills (schema + exploration workflows)
- **`docker-compose.yml`** — optional LiteLLM and Langfuse for local demos

## Try it locally (recommended)

1. **Prepare data** — seed a demo BOM into `data/` (validated against the ontology).
2. **Start services** — LiteLLM (LLM) and Langfuse (traces) via Docker; then the BOM agent.
3. **Use the UI** — ask questions, read Summary / Key findings / Evidence, and view the supply chain map.

**Full walkthrough:** [docs/local-demo-runbook.md](docs/local-demo-runbook.md) (terminals, `.env`, Langfuse keys, browser steps, troubleshooting).

## Documentation

| Doc | Audience | Contents |
|-----|----------|----------|
| [docs/project-layout.md](docs/project-layout.md) | Developers / architects | Directory structure, org vs technical boundaries |
| [docs/local-demo-runbook.md](docs/local-demo-runbook.md) | Anyone running the demo | LiteLLM + Langfuse + agent + UI end-to-end |
| [docs/testing-and-quality.md](docs/testing-and-quality.md) | Developers | Unit tests, ruff, mypy, quality gates |
| [docs/development.md](docs/development.md) | Developers | Setup, seeding, CLI demos, roadmap |
| [docs/llm-gateway.md](docs/llm-gateway.md) | Operators | LiteLLM / Gemini configuration |
| [docs/observability.md](docs/observability.md) | Operators | Langfuse telemetry |
| [docs/enterprise-graph-design.md](docs/enterprise-graph-design.md) | Architects | Enterprise graph domains, Lance layout, agent federation |
| [docs/supply-chain-disruption-response.md](docs/supply-chain-disruption-response.md) | Architects / ops | Disruption playbooks, logical graph federation, mitigations |
| [docs/ontology-on-lance.md](docs/ontology-on-lance.md) | Data / ontology authors | Schema-light Lance vs application ontology layers |
| [AGENTS.md](AGENTS.md) | Coding agents | SSOT, validation, change workflow |
| [skills/README.md](skills/README.md) | Skill consumers | Installing `bom-ontology` and `bom-graph-explorer` |
| [scripts/README.md](scripts/README.md) | Script reference | `seed_*`, `demo_*`, Docker helpers |

Copy [`.env.example`](.env.example) to `.env` before the full stack demo.

## What you get in the UI

- **Summary** — narrative answer to your question  
- **Key findings** — bullet facts from the analysis  
- **Evidence** — grounded claims (no raw tool JSON)  
- **Supply chain map** — suppliers, parts, and products  

Planner details, tool arguments, and full JSON go to **Langfuse** when configured (not shown in the UI).

## Contributing / agent development

See [AGENTS.md](AGENTS.md) and [docs/testing-and-quality.md](docs/testing-and-quality.md). Run tests with `uv run pytest -q` after changes.
