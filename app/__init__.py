from app.agent import BomAgentContext, BomAutonomousAgent
from app.component_master_store import ComponentMasterStore
from app.exploration import ExplorationResult, GraphExplorer
from app.federation.graph_store import GraphStore
from app.storage.neo4j_domain_store import Neo4jDomainStore
from app.tools import exploration_tool_definitions, run_exploration_tool
from domains.registry import DOMAIN_GRAPHS, GraphId
from ontology.schema import (
    ALLOWED_EDGES,
    ComponentNode,
    ProcessNode,
    ProductNode,
    RelationEdge,
    SupplierNode,
)
from pipeline.demo.seed import seed_complex_bom

# Backward-compatible aliases
LanceGraphStore = GraphStore
UnifiedBomContextStore = ComponentMasterStore
DomainLanceGraphStore = Neo4jDomainStore

__all__ = [
    "ALLOWED_EDGES",
    "BomAgentContext",
    "BomAutonomousAgent",
    "ComponentMasterStore",
    "ComponentNode",
    "DOMAIN_GRAPHS",
    "DomainLanceGraphStore",
    "ExplorationResult",
    "GraphExplorer",
    "GraphId",
    "GraphStore",
    "LanceGraphStore",
    "Neo4jDomainStore",
    "ProcessNode",
    "ProductNode",
    "RelationEdge",
    "SupplierNode",
    "UnifiedBomContextStore",
    "exploration_tool_definitions",
    "run_exploration_tool",
    "seed_complex_bom",
]
