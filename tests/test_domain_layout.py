"""Layout guardrails for domains/ organization slices (no Neo4j)."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from domains.registry import DOMAIN_GRAPHS, GraphId

REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAINS_ROOT = REPO_ROOT / "domains"


@pytest.mark.parametrize("graph_id", tuple(DOMAIN_GRAPHS.keys()))
def test_domain_package_has_bundle_and_pipeline(graph_id: GraphId) -> None:
    domain_dir = DOMAINS_ROOT / graph_id
    assert domain_dir.is_dir(), f"missing domains/{graph_id}/"
    assert (domain_dir / "bundle.py").is_file()
    assert (domain_dir / "pipeline.py").is_file()
    assert (domain_dir / "__init__.py").is_file()


@pytest.mark.parametrize("graph_id", tuple(DOMAIN_GRAPHS.keys()))
def test_domain_bundle_matches_registry(graph_id: GraphId) -> None:
    mod = importlib.import_module(f"domains.{graph_id}.bundle")
    bundle = mod.BUNDLE
    registry = DOMAIN_GRAPHS[graph_id]
    assert bundle.graph_id == graph_id
    assert set(bundle.nodes) == registry["nodes"]
    assert set(bundle.edges) == registry["edges"]
