"""Manufacturing supply-chain ontology — platform-independent schema and contracts.

Depends only on Pydantic and the standard library. Imported by domains/, app/,
pipeline/, and export scripts; must not import storage, agent, or skill layers.
"""

from ontology.schema import (
    ALLOWED_EDGES,
    ComponentNode,
    ProcessNode,
    ProductNode,
    RelationEdge,
    SupplierNode,
    export_schema_bundle,
    validate_node_payload,
)

__all__ = [
    "ALLOWED_EDGES",
    "ComponentNode",
    "ProcessNode",
    "ProductNode",
    "RelationEdge",
    "SupplierNode",
    "export_schema_bundle",
    "validate_node_payload",
]
