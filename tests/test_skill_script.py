import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "bom-graph-explorer" / "scripts" / "explore_graph.py"


def test_skill_explore_script_supplier_impact(tmp_path) -> None:
    lancedb = tmp_path / "lancedb"
    duckdb = tmp_path / "bom.duckdb"

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed",
            "--mode",
            "supplier-impact",
            "--supplier-id",
            "SUP-001",
            "--lancedb-path",
            str(lancedb),
            "--duckdb-path",
            str(duckdb),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(proc.stdout)
    assert isinstance(payload, list)
    assert payload
    assert payload[0]["component_id"] == "COMP-100"
