"""Relative Markdown links must resolve to existing repo files or directories."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"\]\(([^)#]+)")
SKIP_DIR_PARTS = frozenset({".venv", ".pytest_cache", "node_modules", ".git"})


def _iter_markdown_files(root: Path) -> list[Path]:
    return [md for md in root.rglob("*.md") if not SKIP_DIR_PARTS.intersection(md.parts)]


def _markdown_targets(text: str) -> list[str]:
    """Extract link targets, ignoring fenced and inline code spans."""
    without_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    without_code = re.sub(r"`[^`]+`", "", without_fences)
    return [match.group(1).strip() for match in LINK_PATTERN.finditer(without_code)]


def find_broken_internal_links(root: Path = REPO_ROOT) -> list[tuple[Path, str]]:
    """Return sorted (markdown file, target) pairs for unresolved internal links."""
    broken: list[tuple[Path, str]] = []
    root_resolved = root.resolve()

    for md in _iter_markdown_files(root):
        for target in _markdown_targets(md.read_text(encoding="utf-8")):
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue

            resolved = (md.parent / target).resolve()
            root_target = (root / target).resolve()
            if resolved.is_file() or root_target.is_file():
                continue
            if resolved.exists() or root_target.exists():
                continue

            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                continue

            broken.append((md.relative_to(root), target))

    return sorted(set(broken))


def test_markdown_internal_links() -> None:
    broken = find_broken_internal_links()
    if broken:
        lines = "\n".join(f"  {md}: {target}" for md, target in broken)
        raise AssertionError(f"Broken internal Markdown links ({len(broken)}):\n{lines}")
