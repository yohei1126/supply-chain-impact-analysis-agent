"""Ontology must stay free of app, pipeline, and storage-framework imports."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_ROOT = REPO_ROOT / "ontology"

# Third-party modules allowed inside ontology/ (besides stdlib).
ALLOWED_THIRD_PARTY = frozenset({"pydantic"})

# Top-level package prefixes that must never appear in ontology imports.
FORBIDDEN_PREFIXES = (
    "app",
    "pipeline",
    "lancedb",
    "duckdb",
    "fastapi",
    "httpx",
    "uvicorn",
    "numpy",
    "langfuse",
    "litellm",
    "skills",
    "bom_graph",
)


def _module_roots(module: str | None) -> list[str]:
    if not module:
        return []
    return module.split(".")


def _collect_import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_ontology_python_files_only_import_allowed_modules() -> None:
    offenders: list[str] = []
    for path in sorted(ONTOLOGY_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for root in _collect_import_roots(tree):
            if root == "ontology":
                continue
            if root in ALLOWED_THIRD_PARTY:
                continue
            if root in FORBIDDEN_PREFIXES or any(
                root == prefix or root.startswith(f"{prefix}.") for prefix in FORBIDDEN_PREFIXES
            ):
                offenders.append(f"{path.relative_to(REPO_ROOT)}: forbidden import root {root!r}")
                continue
            # stdlib: reject unknown third-party unless explicitly allowed
            if root not in _STDLIB_TOP_LEVEL:
                offenders.append(
                    f"{path.relative_to(REPO_ROOT)}: unexpected third-party import root {root!r}"
                )
    assert not offenders, "Ontology import violations:\n" + "\n".join(offenders)


# Common stdlib top-level names (Python 3.10+). Incomplete but sufficient for guardrail.
_STDLIB_TOP_LEVEL = frozenset(
    {
        "__future__",
        "abc",
        "ast",
        "collections",
        "copy",
        "dataclasses",
        "datetime",
        "enum",
        "functools",
        "io",
        "itertools",
        "json",
        "pathlib",
        "re",
        "sys",
        "textwrap",
        "typing",
        "uuid",
    }
)
