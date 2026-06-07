#!/usr/bin/env bash
# Shared Docker Compose profile resolution for start_stack.sh / stop_stack.sh.
# Source from other scripts; do not execute directly.

resolve_stack_profiles() {
  local skip_neo4j="${1:-false}"
  if [[ "$skip_neo4j" == true ]]; then
    STACK_PROFILES=(langfuse litellm)
  else
    STACK_PROFILES=(langfuse litellm neo4j)
  fi
  STACK_PROFILE_FLAGS=()
  for profile in "${STACK_PROFILES[@]}"; do
    STACK_PROFILE_FLAGS+=(--profile "$profile")
  done
}
