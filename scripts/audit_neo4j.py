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
from app.validation.pipeline_gate import L3ConformanceError, require_l3_conformance


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
        require_l3_conformance(driver, quiet=args.quiet)
    except L3ConformanceError:
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
