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
NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-7474}"
NEO4J_BOLT_PORT="${NEO4J_BOLT_PORT:-7687}"
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-litellm-local}"

PROFILES=(langfuse litellm)
COMPOSE_ARGS=()
USE_NEO4J=false

for arg in "$@"; do
  if [[ "$arg" == "--neo4j" ]]; then
    USE_NEO4J=true
  else
    COMPOSE_ARGS+=("$arg")
  fi
done

if [[ "$USE_NEO4J" == true ]]; then
  PROFILES+=(neo4j)
fi

PROFILE_FLAGS=()
for profile in "${PROFILES[@]}"; do
  PROFILE_FLAGS+=(--profile "$profile")
done

echo "Starting Docker stack (${PROFILES[*]})"
echo "  Langfuse UI:  http://127.0.0.1:${LANGFUSE_PORT}"
echo "  LiteLLM API:  http://127.0.0.1:${LITELLM_PORT}/v1"
if [[ "$USE_NEO4J" == true ]]; then
  echo "  Neo4j Browser: http://127.0.0.1:${NEO4J_HTTP_PORT}"
  echo "  Neo4j Bolt:    bolt://127.0.0.1:${NEO4J_BOLT_PORT}"
fi
echo ""
echo "BOM agent (.env):"
echo "  LANGFUSE_HOST=http://localhost:${LANGFUSE_PORT}"
echo "  OPENAI_API_BASE=http://127.0.0.1:${LITELLM_PORT}/v1"
echo "  OPENAI_API_KEY=\${LITELLM_MASTER_KEY}"
echo "  OPENAI_MODEL=bom-gemini-3.5-flash"
if [[ "$USE_NEO4J" == true ]]; then
  echo "  BOM_NEO4J_URI=bolt://localhost:${NEO4J_BOLT_PORT}"
  echo "  BOM_NEO4J_USER=neo4j"
  echo "  BOM_NEO4J_PASSWORD=password"
fi
echo ""
echo "Optional Neo4j profile: ./scripts/run_docker_stack.sh --neo4j -d"
echo "First Langfuse boot: wait for langfuse-web 'Ready', then create API keys in the UI."
echo "Stop: docker compose ${PROFILE_FLAGS[*]} down"
echo ""

exec docker compose "${PROFILE_FLAGS[@]}" up "${COMPOSE_ARGS[@]}"
