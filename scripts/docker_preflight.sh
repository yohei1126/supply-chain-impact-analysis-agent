#!/usr/bin/env bash
# Source from compose scripts: ensures Docker daemon is reachable (Colima, Docker Desktop, etc.)

if docker info >/dev/null 2>&1; then
  :
else
  echo "Error: Docker daemon is not running." >&2
  echo "" >&2

  if command -v colima >/dev/null 2>&1; then
    echo "Colima is installed but not running. Start it, then retry:" >&2
    echo "  colima start" >&2
  elif [[ "$(uname -s)" == "Darwin" ]]; then
    echo "On macOS, start Docker Desktop or Colima:" >&2
    echo "  colima start" >&2
  else
    echo "Start your Docker service (e.g. systemctl start docker)." >&2
  fi

  echo "" >&2
  echo "Verify: docker info" >&2
  exit 1
fi
