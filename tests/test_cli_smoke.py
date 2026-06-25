"""Subprocess smoke tests for CLI entrypoints not covered by unit tests alone."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(
    script: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["DEMO_NONINTERACTIVE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=merged,
        check=False,
    )


@pytest.mark.usefixtures("graph_store")
def test_demo_federation_cli() -> None:
    proc = _run_cli(
        REPO_ROOT / "scripts" / "demo_federation.py",
        "--reset",
        "--supplier-id",
        "SUP-002",
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "impact_score" in proc.stdout


@pytest.mark.usefixtures("graph_store")
def test_demo_graph_cli() -> None:
    proc = _run_cli(REPO_ROOT / "scripts" / "demo.py")
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "supplier_impact result" in proc.stdout
    assert "supply_path result" in proc.stdout


@pytest.mark.usefixtures("graph_store")
def test_demo_agent_cli(tmp_path: Path) -> None:
    duckdb = tmp_path / "bom.duckdb"
    proc = _run_cli(
        REPO_ROOT / "scripts" / "demo_agent.py",
        env={"BOM_DUCKDB_PATH": str(duckdb)},
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "Autonomous run result" in proc.stdout


@pytest.mark.usefixtures("graph_store")
@pytest.mark.parametrize(
    ("script", "needle"),
    [
        ("sourcing.py", "SUPPLIED_BY"),
        ("ebom.py", "USED_IN"),
        ("routing.py", "routing edges"),
    ],
)
def test_ingest_domain_cli(script: str, needle: str) -> None:
    proc = _run_cli(REPO_ROOT / "scripts" / "ingest" / script)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert needle in proc.stdout
    assert "L3 audit: PASS" in proc.stdout


def test_sync_ontology_cli() -> None:
    """Validate SSOT export script (Graph Contract + generated JSON assets)."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "sync_ontology.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "Graph Contract" in proc.stdout
