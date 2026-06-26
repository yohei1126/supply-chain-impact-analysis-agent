#!/usr/bin/env python3
"""Run G* agent grounding benchmarks against the seeded demo graph.

Usage:
  uv run python scripts/seed_complex_bom.py --reset
  uv run python scripts/eval_agent_grounding.py
  uv run python scripts/eval_agent_grounding.py --json --output reports/grounding.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.agent.context import BomAgentContext
from app.agent.grounding import (
    AGENT_GROUNDING_BENCHMARKS,
    evaluate_agent_run,
    export_grounding_report,
)
from app.agent.runner import BomAutonomousAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="G* agent grounding benchmark runner")
    parser.add_argument("--duckdb-path", default="data/bom.duckdb")
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    parser.add_argument("--output", type=Path, help="Write JSON report to this file")
    parser.add_argument("--quiet", action="store_true", help="Only print summary on success")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path.cwd()
    ctx = BomAgentContext.create(repo_root=repo_root, duckdb_path=args.duckdb_path)
    agent = BomAutonomousAgent(ctx)
    cases: list[dict] = []
    passed = True

    try:
        for case in AGENT_GROUNDING_BENCHMARKS:
            result = agent.run(case["goal"], mode="tools")
            report = evaluate_agent_run(result)
            case_passed = report.passed
            passed = passed and case_passed
            cases.append(
                {
                    "id": case["id"],
                    "goal": case["goal"],
                    "passed": case_passed,
                    "tools": [call.name for call in result.tool_calls],
                    "grounding": export_grounding_report(report),
                }
            )

        payload = {
            "format": "bom-grounding-benchmark-report",
            "version": 1,
            "passed": passed,
            "cases": cases,
        }

        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif args.quiet and passed:
            print(f"agent grounding benchmarks: PASS ({len(cases)} cases)")
        else:
            for case in cases:
                status = "PASS" if case["passed"] else "FAIL"
                print(f"[{status}] {case['id']}")

        if not passed:
            sys.exit(1)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
