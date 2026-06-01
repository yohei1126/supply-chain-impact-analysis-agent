#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/docker_preflight.sh"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

LANGFUSE_PORT="${LANGFUSE_PORT:-3000}"
LITELLM_PORT="${LITELLM_PORT:-4000}"
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-litellm-local}"

echo "Starting LiteLLM + Langfuse (docker compose)"
echo "  Langfuse UI:  http://127.0.0.1:${LANGFUSE_PORT}"
echo "  LiteLLM API:  http://127.0.0.1:${LITELLM_PORT}/v1"
echo ""
echo "BOM agent (.env):"
echo "  LANGFUSE_HOST=http://localhost:${LANGFUSE_PORT}"
echo "  OPENAI_API_BASE=http://127.0.0.1:${LITELLM_PORT}/v1"
echo "  OPENAI_API_KEY=\${LITELLM_MASTER_KEY}"
echo "  OPENAI_MODEL=bom-gemini-3.5-flash"
echo ""
echo "First Langfuse boot: wait for langfuse-web 'Ready', then create API keys in the UI."
echo "Stop: docker compose --profile langfuse --profile litellm down"
echo ""

exec docker compose --profile langfuse --profile litellm up "$@"
