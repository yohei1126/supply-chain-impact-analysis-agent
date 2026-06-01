#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PORT="${LITELLM_PORT:-4000}"
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-litellm-local}"

echo "Starting LiteLLM on http://127.0.0.1:${PORT}/v1 (local uv process)"
echo "  Docker (with Langfuse): ./scripts/run_docker_stack.sh -d"
echo "  config: config/litellm.yaml (default model alias: bom-gemini-3.5-flash -> gemini/gemini-3.5-flash)"
echo "  requires: GEMINI_API_KEY in .env, litellm>=1.87.0rc1 (uv sync --extra gateway)"
exec uv run --extra gateway litellm --config config/litellm.yaml --port "$PORT"
