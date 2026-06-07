import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "bom-graph-explorer" / "scripts" / "explore_graph.py"


@pytest.mark.usefixtures("graph_store")
def test_skill_explore_script_supplier_impact(tmp_path) -> None:
    duckdb = tmp_path / "bom.duckdb"

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed",
            "--reset",
            "--mode",
            "supplier-impact",
            "--supplier-id",
            "SUP-001",
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
