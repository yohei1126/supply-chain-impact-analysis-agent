from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.agent.registry import ToolRegistry
from app.agent.skills import build_system_prompt
from app.exploration import GraphExplorer
from app.hybrid_store import UnifiedBomContextStore
from app.federation.graph_store import LanceGraphStore


@dataclass
class BomAgentContext:
    repo_root: Path
    lancedb_path: str
    duckdb_path: str
    graph: LanceGraphStore
    hybrid: UnifiedBomContextStore
    explorer: GraphExplorer
    tools: ToolRegistry

    @classmethod
    def create(
        cls,
        repo_root: Path | None = None,
        lancedb_path: str = "data/lancedb",
        duckdb_path: str = "data/bom.duckdb",
    ) -> "BomAgentContext":
        root = repo_root or Path.cwd()
        graph = LanceGraphStore(lancedb_path=lancedb_path)
        hybrid = UnifiedBomContextStore(
            graph_store=graph,
            duckdb_path=duckdb_path,
            lancedb_path=lancedb_path,
        )
        explorer = GraphExplorer(graph)
        return cls(
            repo_root=root,
            lancedb_path=lancedb_path,
            duckdb_path=duckdb_path,
            graph=graph,
            hybrid=hybrid,
            explorer=explorer,
            tools=ToolRegistry(explorer=explorer, hybrid=hybrid),
        )

    def system_prompt(self) -> str:
        return build_system_prompt(self.repo_root)

    def close(self) -> None:
        self.hybrid.close()
