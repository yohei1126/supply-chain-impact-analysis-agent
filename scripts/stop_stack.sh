#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/stack_profiles.sh"

SKIP_NEO4J=false
DOWN_ARGS=()

for arg in "$@"; do
  if [[ "$arg" == "--no-neo4j" ]]; then
    SKIP_NEO4J=true
  elif [[ "$arg" == "--neo4j" ]]; then
    : # backward compatible no-op
  else
    DOWN_ARGS+=("$arg")
  fi
done

resolve_stack_profiles "$SKIP_NEO4J"

echo "Stopping Docker stack (${STACK_PROFILES[*]})"
if [[ ${#DOWN_ARGS[@]} -gt 0 ]]; then
  exec docker compose "${STACK_PROFILE_FLAGS[@]}" down "${DOWN_ARGS[@]}"
else
  exec docker compose "${STACK_PROFILE_FLAGS[@]}" down
fi
