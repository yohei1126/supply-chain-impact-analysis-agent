# BOM Knowledge Graph Agent Skill

Explore manufacturing BOMs with an ontology-validated graph, hybrid search (vector + SQL + graph), and optional LLM-assisted analysis. Agent Skills under `skills/` describe the schema and exploration workflows; the Python package `bom_graph/` runs storage, tools, and a small web UI.

## Try it locally (recommended)

1. **Prepare data** — seed a demo BOM into `data/` (validated against the ontology).
2. **Start services** — LiteLLM (LLM) and Langfuse (traces) via Docker; then the BOM agent.
3. **Use the UI** — ask questions, read Summary / Key findings / Evidence, and view the supply chain map.

**Full walkthrough:** [docs/local-demo-runbook.md](docs/local-demo-runbook.md) (terminals, `.env`, Langfuse keys, browser steps, troubleshooting).

## Documentation

| Doc | Audience | Contents |
|-----|----------|----------|
| [docs/local-demo-runbook.md](docs/local-demo-runbook.md) | Anyone running the demo | LiteLLM + Langfuse + agent + UI end-to-end |
| [docs/development.md](docs/development.md) | Developers | Setup, seeding, CLI demos, tests, project layout |
| [docs/llm-gateway.md](docs/llm-gateway.md) | Operators | LiteLLM / Gemini configuration |
| [docs/observability.md](docs/observability.md) | Operators | Langfuse telemetry |
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

See [AGENTS.md](AGENTS.md). Run tests with `uv run pytest -q` after changes.
