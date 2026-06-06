#!/usr/bin/env python3
"""Verify Langfuse connectivity and recent bom-agent-run traces."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app.agent.telemetry import _langfuse_client, langfuse_configured


def main() -> int:
    print("Langfuse telemetry check")
    print(f"  LANGFUSE_HOST: {os.getenv('LANGFUSE_HOST') or os.getenv('LANGFUSE_BASE_URL') or '(default)'}")
    print(f"  keys set: {langfuse_configured()}")

    client = _langfuse_client()
    if client is None:
        print("\nFAIL: Langfuse client not available.")
        print("  uv sync --extra observability")
        print("  uv run --extra observability python scripts/verify_langfuse_telemetry.py")
        print("  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env")
        return 1

    if not client.auth_check():
        print("\nFAIL: auth_check() returned false (wrong host or keys).")
        return 1

    print("  auth_check: OK")

    try:
        response = client.api.trace.list(limit=10)
        rows = getattr(response, "data", None) or []
    except Exception as exc:
        print(f"\nWARN: could not list traces: {exc}")
        return 0

    bom = [t for t in rows if getattr(t, "name", None) == "bom-agent-run"]
    print(f"\nRecent traces (up to 10): {len(rows)}")
    for trace in rows[:5]:
        print(f"  - {getattr(trace, 'name', '?')} id={getattr(trace, 'id', '?')}")

    if bom:
        print(f"\nOK: found {len(bom)} bom-agent-run trace(s). Open Langfuse UI -> Traces.")
    else:
        print("\nNo bom-agent-run traces yet. Run an analysis, then re-run this script.")
        print("  curl -X POST http://127.0.0.1:8080/v1/agent/run \\")
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"goal":"Analyze supplier impact for SUP-002","mode":"tools"}\'')

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
