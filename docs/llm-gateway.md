# LLM gateway (LiteLLM)

**Docs index:** [development.md](development.md). **Full stack (with Langfuse + agent UI):** [local-demo-runbook.md](local-demo-runbook.md).

`app/agent` plans tool calls via **OpenAI-compatible** `POST /v1/chat/completions`.
Run [LiteLLM](https://docs.litellm.ai/) (>= 1.87.0rc1 for Gemini 3.5 Flash) as a local proxy. The default planner model is **Gemini 3.5 Flash** via `config/litellm.yaml` (`gemini/gemini-3.5-flash`).

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_BASE` | LiteLLM base URL including `/v1` (e.g. `http://127.0.0.1:4000/v1`) |
| `OPENAI_API_KEY` | Bearer token (LiteLLM `master_key`) |
| `OPENAI_MODEL` | LiteLLM alias (default: `bom-gemini-3.5-flash`; legacy: `bom-gemini-planner`) |
| `LLM_GATEWAY` | Optional label in `llm_notes` (`litellm` or `openai` when calling OpenAI directly) |
| `LLM_GATEWAY_BASE` | Alias for `OPENAI_API_BASE` |
| `LLM_GATEWAY_API_KEY` | Alias for `OPENAI_API_KEY` |
| `LLM_MODEL` | Alias for `OPENAI_MODEL` |

Agent run modes:

- `mode=auto` — use LLM when base + key are set; otherwise heuristic planner
- `mode=llm` — always use the gateway
- `mode=tools` — heuristic only

## Gemini 3.5 Flash

| Layer | Value |
|-------|--------|
| LiteLLM upstream | `gemini/gemini-3.5-flash` |
| Proxy alias (use in `OPENAI_MODEL`) | `bom-gemini-3.5-flash` |
| API key | `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey) |

`reasoning_effort: minimal` is set in `config/litellm.yaml` for faster JSON tool planning (see [LiteLLM Gemini 3.5 Flash notes](https://docs.litellm.ai/blog/gemini_3_5_flash)).

## Setup

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` (and/or `UPSTREAM_OPENAI_API_KEY` for the OpenAI-backed alias).
2. Start the stack (LiteLLM + Langfuse + Neo4j via Docker):

```bash
export GEMINI_API_KEY=...
./scripts/start_stack.sh
```

3. Run the BOM agent:

```bash
export OPENAI_API_BASE=http://127.0.0.1:4000/v1
export OPENAI_API_KEY=sk-litellm-local
export OPENAI_MODEL=bom-gemini-3.5-flash
export LLM_GATEWAY=litellm

uv run python -m app.agent
# Browser UI: http://localhost:8080/ui/
curl -s -X POST http://localhost:8080/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Analyze supplier impact for SUP-001","mode":"auto"}'
```

Edit `config/litellm.yaml` to add models (Anthropic, Azure, local Ollama via LiteLLM, etc.).

Install proxy dependency (optional extra):

```bash
uv sync --extra gateway   # installs litellm[proxy] (includes websockets, etc.)
```

## Architecture

```
Agent Skills (prompt) -> BomAutonomousAgent
                              |
                              v
                    OpenAI-compatible /v1/chat/completions
                              |
                         LiteLLM proxy
                              |
              gemini-3.5-flash / openai / ...
```

Tool execution remains deterministic in `app/` after the LLM returns `tool_calls` JSON.
