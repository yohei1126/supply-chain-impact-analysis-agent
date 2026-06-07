from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.agent.registry import ToolRegistry
from app.agent.skills import build_system_prompt
from app.component_master_store import ComponentMasterStore
from app.exploration import GraphExplorer
from app.federation.graph_store import GraphStore


@dataclass
class BomAgentContext:
    repo_root: Path
    duckdb_path: str
    graph: GraphStore
    component_master: ComponentMasterStore
    explorer: GraphExplorer
    tools: ToolRegistry
    _owned_graph: bool = field(default=True, repr=False)

    @classmethod
    def create(
        cls,
        repo_root: Path | None = None,
        duckdb_path: str = "data/bom.duckdb",
        *,
        graph: GraphStore | None = None,
        neo4j_uri: str | None = None,
        neo4j_auth: tuple[str, str] | None = None,
    ) -> "BomAgentContext":
        root = repo_root or Path.cwd()
        owned_graph = graph is None
        graph = graph or GraphStore(uri=neo4j_uri, auth=neo4j_auth)
        component_master = ComponentMasterStore(graph_store=graph, duckdb_path=duckdb_path)
        explorer = GraphExplorer(graph)
        return cls(
            repo_root=root,
            duckdb_path=duckdb_path,
            graph=graph,
            component_master=component_master,
            explorer=explorer,
            tools=ToolRegistry(explorer=explorer),
            _owned_graph=owned_graph,
        )

    def system_prompt(self) -> str:
        return build_system_prompt(self.repo_root)

    def close(self) -> None:
        self.component_master.close()
        if self._owned_graph:
            self.graph.close()
