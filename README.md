# BOM Knowledge Graph Agent

Explore manufacturing BOMs with an ontology-validated Neo4j graph, DuckDB component master, and optional LLM-assisted analysis.

This repository bundles:

- **`ontology/`** — shared schema, constraints, Graph Contract (technical SSOT)
- **`domains/`** — organization-owned domain slices (ebom, routing, sourcing)
- **`pipeline/demo/`** — cross-domain demo seed orchestration
- **`app/`** — federation, stores, agent (shared runtime)
- **`skills/`** — distributable Agent Skills (schema + exploration workflows)
- **`docker-compose.yml`** — optional LiteLLM, Langfuse, and Neo4j for local demos

## Try it locally (recommended)

1. **Prepare data** — seed a demo BOM into Neo4j + DuckDB (validated against the ontology).
2. **Start services** — `./scripts/start_stack.sh` (Neo4j, LiteLLM, Langfuse); seed data; then the BOM agent.
3. **Use the UI** — ask questions, read Summary / Key findings / Evidence, and view the supply chain map.

**Full walkthrough:** [docs/demo-runbook.md](docs/demo-runbook.md) (federation CLI, full stack, verification, troubleshooting).

## Documentation

| Doc | Audience | Contents |
|-----|----------|----------|
| [docs/project-layout.md](docs/project-layout.md) | Developers / architects | Directory structure, org vs technical boundaries |
| [docs/demo-runbook.md](docs/demo-runbook.md) | Anyone running the demo | Federation CLI, full stack (LiteLLM + Langfuse + agent), verification |
| [docs/testing-and-quality.md](docs/testing-and-quality.md) | Developers | Unit tests, ruff, mypy, quality gates |
| [docs/development.md](docs/development.md) | Developers | Setup, seeding, CLI demos, roadmap |
| [docs/llm-gateway.md](docs/llm-gateway.md) | Operators | LiteLLM / Gemini configuration |
| [docs/observability.md](docs/observability.md) | Operators | Langfuse telemetry |
| [docs/enterprise-graph-design.md](docs/enterprise-graph-design.md) | Architects | Enterprise graph domains, Neo4j layout, agent federation |
| [docs/supply-chain-disruption-response.md](docs/supply-chain-disruption-response.md) | Architects / ops | Disruption playbooks, logical graph federation, mitigations |
| [docs/agent-guide.md](docs/agent-guide.md) | Coding agents / contributors | Setup, seeding, demos, **terminology SSOT** |
| [docs/graph-contract.md](docs/graph-contract.md) | Data / ontology authors | Graph Contract (YAML, governance, federation) |
| [docs/graph-context.md](docs/graph-context.md) | Agent / Skill authors | graph context bundle (`graph-context.json`), sync, Cypher compose |
| [docs/agent-guide.md](docs/agent-guide.md) | Coding agents | Seeding, setup, demos, agent runtime |
| [AGENTS.md](AGENTS.md) | Coding agents | Principles, SSOT, change workflow, done criteria |
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

See [AGENTS.md](AGENTS.md), [docs/agent-guide.md](docs/agent-guide.md), and [docs/testing-and-quality.md](docs/testing-and-quality.md).
