#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/docker_preflight.sh"
# shellcheck disable=SC1091
source "$ROOT/scripts/stack_profiles.sh"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

LANGFUSE_PORT="${LANGFUSE_PORT:-3000}"
LITELLM_PORT="${LITELLM_PORT:-4000}"
NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-7474}"
NEO4J_BOLT_PORT="${NEO4J_BOLT_PORT:-7687}"
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-litellm-local}"

COMPOSE_ARGS=()
SKIP_NEO4J=false

for arg in "$@"; do
  if [[ "$arg" == "--no-neo4j" ]]; then
    SKIP_NEO4J=true
  elif [[ "$arg" == "--neo4j" ]]; then
    : # backward compatible no-op (neo4j is on by default)
  else
    COMPOSE_ARGS+=("$arg")
  fi
done

if [[ ${#COMPOSE_ARGS[@]} -eq 0 ]]; then
  COMPOSE_ARGS=(-d)
fi

resolve_stack_profiles "$SKIP_NEO4J"

echo "Starting Docker stack (${STACK_PROFILES[*]})"
echo "  Langfuse UI:  http://127.0.0.1:${LANGFUSE_PORT}"
echo "  LiteLLM API:  http://127.0.0.1:${LITELLM_PORT}/v1"
if [[ "$SKIP_NEO4J" != true ]]; then
  echo "  Neo4j Browser: http://127.0.0.1:${NEO4J_HTTP_PORT}"
  echo "  Neo4j Bolt:    bolt://127.0.0.1:${NEO4J_BOLT_PORT}"
fi
echo ""
echo "BOM agent (.env):"
echo "  LANGFUSE_HOST=http://localhost:${LANGFUSE_PORT}"
echo "  OPENAI_API_BASE=http://127.0.0.1:${LITELLM_PORT}/v1"
echo "  OPENAI_API_KEY=\${LITELLM_MASTER_KEY}"
echo "  OPENAI_MODEL=bom-gemini-3.5-flash"
if [[ "$SKIP_NEO4J" != true ]]; then
  echo "  BOM_NEO4J_URI=bolt://localhost:${NEO4J_BOLT_PORT}"
  echo "  BOM_NEO4J_USER=neo4j"
  echo "  BOM_NEO4J_PASSWORD=password"
fi
echo ""
echo "Seed demo BOM: uv run python scripts/seed_complex_bom.py --reset"
echo "Start agent:   uv run python -m app.agent"
echo ""
echo "Skip Neo4j (LLM stack only): ./scripts/start_stack.sh --no-neo4j"
echo "First Langfuse boot: wait for langfuse-web 'Ready', then create API keys in the UI."
echo "Stop: ./scripts/stop_stack.sh"
echo ""

exec docker compose "${STACK_PROFILE_FLAGS[@]}" up "${COMPOSE_ARGS[@]}"
