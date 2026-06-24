#!/usr/bin/env python3
"""L3 post-load conformance audit for Neo4j domain graphs.

Runs Cypher probes derived from ontology/schema.py and domains/registry.py,
then re-validates node and edge payloads with Pydantic.

Usage:
  uv run python scripts/audit_neo4j.py
  uv run python scripts/seed_complex_bom.py --reset && uv run python scripts/audit_neo4j.py
"""

from __future__ import annotations

import argparse
import sys

from app.storage.neo4j_config import get_driver, verify_connectivity
from app.validation.neo4j_l3_audit import format_report, run_l3_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="L3 Neo4j ontology conformance audit")
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
        report = run_l3_audit(driver)
    finally:
        driver.close()

    if args.quiet and report.passed:
        print("L3 audit: PASS")
    else:
        print(format_report(report))

    if not report.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
