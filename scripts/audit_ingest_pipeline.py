#!/usr/bin/env python3
"""Async Graph Contract on_ingest audit pipeline (L4 batch job for data stewards).

Runs quality.on_ingest and quality.on_ingest_audit checks against a live Neo4j
graph and emits a human-readable or JSON violation report.

Usage:
  uv run python scripts/audit_ingest_pipeline.py
  uv run python scripts/audit_ingest_pipeline.py --json --output reports/ingest-audit.json
  uv run python scripts/seed_complex_bom.py --reset
  uv run python scripts/audit_ingest_pipeline.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.storage.neo4j_config import get_driver, verify_connectivity
from app.validation.ingest_audit_pipeline import (
    export_violation_report,
    format_ingest_audit_pipeline_report,
    run_ingest_audit_pipeline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Graph Contract on_ingest audit pipeline (async batch)"
    )
    parser.add_argument(
        "--duckdb-path",
        default="data/bom.duckdb",
        help="Component master DuckDB path for bridge checks",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print steward JSON violation report to stdout",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON violation report to this file",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print summary line on success",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    driver = get_driver()
    try:
        verify_connectivity(driver)
        report = run_ingest_audit_pipeline(driver, duckdb_path=args.duckdb_path)
        payload = export_violation_report(report)

        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif args.quiet and report.passed:
            print(
                f"on_ingest audit pipeline: PASS "
                f"(Graph Contract v{report.contract_version})"
            )
        else:
            print(format_ingest_audit_pipeline_report(report))

        if not report.passed:
            sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
