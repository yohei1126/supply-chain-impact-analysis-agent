# Autonomous agent runtime

How the BOM agent loads Skills, plans tool calls, and returns user-facing responses.

**Audience:** coding agents, contributors working in `app/agent/`.

**Related:** [AGENTS.md](../AGENTS.md) · [seeding.md](seeding.md) · [setup-and-demos.md](setup-and-demos.md) · [demo-runbook.md](demo-runbook.md) · [observability.md](observability.md) · [graph-context.md](graph-context.md)

---

## Overview (`app/agent`)

- Loads Agent Skills from `skills/` into a system prompt (`build_system_prompt`).
- Embeds generated assets (`ontology.json`, `graph-context.json`, query catalog) via `app/agent/skills.py`.
- Executes deterministic tools via `ToolRegistry` (aligned with `bom-graph-explorer`).
- `BomAutonomousAgent.run()` supports:
  - `mode=tools` — heuristic planner (no API key)
  - `mode=llm` / `mode=auto` — OpenAI-compatible planner (`OPENAI_*` or `LLM_GATEWAY_*` → LiteLLM or direct OpenAI)
  - explicit `tool_calls` — fully deterministic remote control

## User-facing vs operator detail

| Surface | Fields | Audience |
|---------|--------|----------|
| Agent UI / `POST /v1/agent/run` | `explanation`, `findings`, `evidence`, `graph_view` | Business user |
| Langfuse (`bom-agent-run`) | planner, tool args, raw JSON, skills context | Developer / evaluator |

See [demo-runbook.md § D.3](demo-runbook.md#d3-ui-vs-langfuse) and [observability.md](observability.md).

## Run commands

| Goal | Doc |
|------|-----|
| CLI demos (no HTTP) | [setup-and-demos.md](setup-and-demos.md) |
| Full stack + UI | [demo-runbook.md](demo-runbook.md) |
| Seeded data required | [seeding.md](seeding.md) |

```bash
uv run python scripts/seed_complex_bom.py --reset
uv run --extra observability python -m app.agent
# → http://localhost:8080/ui/
```
