from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainBundle:
    """Org-owned metadata for one logical graph domain."""

    graph_id: str
    name: str
    owner_team: str
    source_systems: tuple[str, ...]
    nodes: frozenset[str]
    edges: frozenset[str]
    description: str
