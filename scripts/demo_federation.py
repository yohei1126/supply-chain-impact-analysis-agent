#!/usr/bin/env python3
"""
Federated domain graph demo: per-domain synthetic data, validation, load, query, analysis.

Flow:
  1. Generate synthetic datasets independently per domain (sourcing / ebom / routing)
  2. Validate each dataset against ontology/schema.py (Pydantic)
  3. Load into separate Neo4j databases (ebom, routing, sourcing)
  4. Query each domain graph locally
  5. Federate on Component.id for a disruption scenario (default: SUP-001)
  6. Surface problems and mitigation recommendations

Usage:
  uv run python scripts/demo_federation.py --reset
  DEMO_NONINTERACTIVE=1 uv run python scripts/demo_federation.py --reset --supplier-id SUP-001
"""

from __future__ import annotations

import argparse
import json
import sys

from demo_interactive import explain, prompt, section, show, wait

from app.federation.analysis import (
    FederatedAnalysis,
    analyze_supplier_disruption,
    query_ebom_for_components,
    query_routing_for_components,
    query_sourcing_for_supplier,
)
from app.federation.graph_store import GraphStore
from app.storage.neo4j_config import reset_neo4j
from pipeline.demo.domain_datasets import (
    build_all_domain_datasets,
    dataset_summary,
    validate_all_datasets,
)
from pipeline.demo.load_domains import load_all_domains_separately


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Federated three-domain graph demo")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear Neo4j domain databases before loading",
    )
    parser.add_argument("--supplier-id", default="", help="Disrupted supplier (default: SUP-001)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    supplier_id = args.supplier_id or prompt("Disrupted supplier_id", "SUP-001")

    section(
        "Step 1 — Generate synthetic data per domain",
        intro=(
            "Each organization-owned slice builds its own node/edge bundle from shared\n"
            "component master rows (pipeline/demo/sample_data.py)."
        ),
    )
    datasets = build_all_domain_datasets()
    summaries = {gid: dataset_summary(ds) for gid, ds in datasets.items()}
    show(
        "Domain datasets (generated)",
        summaries,
        commentary="Independent bundles before validation.",
    )
    wait()

    section(
        "Step 2 — Validate against ontology",
        intro="Every node and edge is checked with ontology/schema.py validators.",
    )
    validation = validate_all_datasets(datasets)
    errors = {gid: errs for gid, errs in validation.items() if errs}
    if errors:
        print("Validation failed:", json.dumps(errors, indent=2), file=sys.stderr)
        sys.exit(1)
    show(
        "Validation",
        {gid: "ok" for gid in datasets},
        commentary="All domain datasets passed Pydantic validation.",
    )
    wait()

    section(
        "Step 3 — Load into separate domain graphs",
        intro="Neo4j databases: ebom, routing, sourcing (one database per graph_id).",
    )

    graph = GraphStore()
    try:
        if args.reset:
            reset_neo4j(graph.driver)

        load_stats = load_all_domains_separately(graph)
        show("Load stats", load_stats, commentary="Each domain graph loaded independently.")
        wait()

        section(
            "Step 4 — Query each domain graph",
            intro="Domain-local reads before cross-graph federation.",
        )
        sourcing_q = query_sourcing_for_supplier(graph, supplier_id)
        component_ids = {r["component_id"] for r in sourcing_q.rows}
        ebom_q = query_ebom_for_components(graph, component_ids)
        routing_q = query_routing_for_components(graph, component_ids)
        for result in (sourcing_q, ebom_q, routing_q):
            show(
                f"{result.graph_id} / {result.query_name}",
                {
                    "summary": result.summary,
                    "rows": result.rows[:5],
                    "truncated": len(result.rows) > 5,
                },
                commentary=result.summary,
            )
        wait()

        section(
            "Step 5 — Federate and analyze disruption",
            intro=f"Scenario: supplier disruption on {supplier_id} (join on Component.id).",
        )
        analysis = analyze_supplier_disruption(graph, supplier_id)
        _show_analysis(analysis)
        wait()
    finally:
        graph.close()

    section(
        "Demo complete",
        intro=(
            "Reseed all domains: uv run python scripts/demo_federation.py --reset\n"
            "Full stack agent UI: uv run python -m app.agent"
        ),
    )


def _show_analysis(analysis: FederatedAnalysis) -> None:
    show(
        "Federated impact rows",
        analysis.federated_rows[:8],
        commentary=f"impact_score={analysis.impact_score} (deterministic formula)",
    )
    show(
        "Problems found",
        [
            {
                "severity": p.severity,
                "category": p.category,
                "message": p.message,
                "evidence": p.evidence,
            }
            for p in analysis.problems
        ],
        commentary="Derived only from domain query results — no fabricated IDs.",
    )
    show(
        "Mitigation recommendations",
        [
            {
                "priority": m.priority,
                "action": m.action,
                "owner": m.owner_team,
                "evidence": m.evidence,
            }
            for m in analysis.mitigations
        ],
        commentary=(
            "Template actions tagged by owning team (procurement / engineering / manufacturing)."
        ),
    )
    explain(
        f"Scenario {analysis.scenario} complete.\n"
        f"Products at risk: {len({r['product_id'] for r in analysis.federated_rows})}\n"
        f"Components affected: {len({r['component_id'] for r in analysis.federated_rows})}"
    )


if __name__ == "__main__":
    main()
