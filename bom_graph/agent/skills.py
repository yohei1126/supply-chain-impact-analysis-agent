from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillPackage:
    name: str
    skill_md: str
    references: dict[str, str]
    assets: dict[str, Path]


def load_skill_package(repo_root: Path, skill_name: str) -> SkillPackage:
    root = repo_root / "skills" / skill_name
    skill_md_path = root / "SKILL.md"
    if not skill_md_path.exists():
        raise FileNotFoundError(f"Skill not found: {root}")

    references: dict[str, str] = {}
    ref_dir = root / "references"
    if ref_dir.is_dir():
        for path in sorted(ref_dir.glob("*.md")):
            references[path.name] = path.read_text(encoding="utf-8")

    assets: dict[str, Path] = {}
    assets_dir = root / "assets"
    if assets_dir.is_dir():
        for path in sorted(assets_dir.iterdir()):
            if path.is_file():
                assets[path.name] = path

    return SkillPackage(
        name=skill_name,
        skill_md=skill_md_path.read_text(encoding="utf-8"),
        references=references,
        assets=assets,
    )


def build_system_prompt(repo_root: Path) -> str:
    ontology = load_skill_package(repo_root, "bom-ontology")
    explorer = load_skill_package(repo_root, "bom-graph-explorer")

    ontology_json = ""
    ontology_path = ontology.assets.get("ontology.json")
    if ontology_path and ontology_path.exists():
        bundle = json.loads(ontology_path.read_text(encoding="utf-8"))
        ontology_json = json.dumps(bundle, ensure_ascii=False, indent=2)

    parts = [
        "# System context (Agent Skills)",
        "",
        "## bom-ontology",
        ontology.skill_md,
        "",
        "## bom-graph-explorer",
        explorer.skill_md,
    ]
    if ontology_json:
        parts.extend(["", "## ontology.json (SSOT)", ontology_json])

    for name, body in explorer.references.items():
        parts.extend(["", f"## reference: {name}", body])

    return "\n".join(parts)
