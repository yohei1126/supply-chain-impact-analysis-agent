import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "bom-graph-explorer" / "scripts" / "explore_graph.py"


@pytest.mark.usefixtures("graph_store")
@pytest.mark.parametrize(
    ("mode", "extra_args", "assertion"),
    [
        (
            "supplier-impact",
            ["--supplier-id", "SUP-001"],
            lambda payload: isinstance(payload, list) and payload[0]["component_id"] == "COMP-100",
        ),
        (
            "shortest-path",
            ["--from-component-id", "COMP-103", "--to-product-id", "PROD-901"],
            lambda payload: isinstance(payload, list) and payload[0]["nodes"],
        ),
        (
            "vector-impact",
            ["--query", "shaft"],
            lambda payload: (
                isinstance(payload, list) and payload[0]["query_component"] == "COMP-103"
            ),
        ),
    ],
)
def test_skill_explore_script_modes(
    tmp_path: Path,
    mode: str,
    extra_args: list[str],
    assertion,
) -> None:
    duckdb = tmp_path / "bom.duckdb"

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seed",
            "--reset",
            "--mode",
            mode,
            "--duckdb-path",
            str(duckdb),
            *extra_args,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(proc.stdout)
    assert assertion(payload)
