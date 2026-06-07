from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class ComponentNode(BaseModel):
    id: str = Field(..., min_length=1, description="Component identifier")
    name: str = Field(..., min_length=1, description="Component name")
    material: str = Field(..., min_length=1, description="Material")
    cost: float = Field(..., gt=0.0, description="Unit cost")
    label: Literal["Component"] = "Component"


class ProcessNode(BaseModel):
    id: str = Field(..., min_length=1, description="Process identifier")
    name: str = Field(..., min_length=1, description="Process name")
    work_center: str = Field(..., min_length=1, description="Work center")
    cycle_time_min: float = Field(..., gt=0.0, description="Standard cycle time (minutes)")
    label: Literal["Process"] = "Process"


class SupplierNode(BaseModel):
    id: str = Field(..., min_length=1, description="Supplier identifier")
    company_name: str = Field(..., min_length=1, description="Company name")
    country: str = Field(
        ..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code"
    )
    risk_level: Literal["Low", "Medium", "High"] = "Medium"
    label: Literal["Supplier"] = "Supplier"

    @field_validator("country")
    @classmethod
    def country_upper(cls, value: str) -> str:
        return value.upper()


class ProductNode(BaseModel):
    id: str = Field(..., min_length=1, description="Product identifier")
    name: str = Field(..., min_length=1, description="Product name")
    version: str = Field(..., min_length=1, description="Version or revision")
    label: Literal["Product"] = "Product"


Node = ComponentNode | ProcessNode | SupplierNode | ProductNode
NodeLabel = Literal["Component", "Process", "Supplier", "Product"]
EdgeType = Literal["USED_IN", "PRODUCED_BY", "SUPPLIED_BY", "INPUT_OF"]


ALLOWED_EDGES: dict[EdgeType, tuple[NodeLabel, NodeLabel]] = {
    "USED_IN": ("Component", "Product"),
    "PRODUCED_BY": ("Product", "Process"),
    "SUPPLIED_BY": ("Component", "Supplier"),
    "INPUT_OF": ("Component", "Process"),
}


class RelationEdge(BaseModel):
    source_label: NodeLabel
    source_id: str
    target_label: NodeLabel
    target_id: str
    edge_type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_domain_and_range(self) -> RelationEdge:
        expected_source, expected_target = ALLOWED_EDGES[self.edge_type]
        if (self.source_label, self.target_label) != (expected_source, expected_target):
            raise ValueError(
                "Edge constraint violation: "
                f"{self.edge_type} only allows {expected_source} -> {expected_target}"
            )
        return self


def validate_node_payload(node_type: str, payload: dict[str, Any]) -> Node:
    mapping = {
        "Component": ComponentNode,
        "Process": ProcessNode,
        "Supplier": SupplierNode,
        "Product": ProductNode,
    }
    if node_type not in mapping:
        raise ValueError(f"Unknown node type: {node_type}")
    return cast(Node, mapping[node_type](**payload))


def export_schema_bundle() -> dict[str, Any]:
    return {
        "nodes": {
            "Component": ComponentNode.model_json_schema(),
            "Process": ProcessNode.model_json_schema(),
            "Supplier": SupplierNode.model_json_schema(),
            "Product": ProductNode.model_json_schema(),
        },
        "edges": {
            "RelationEdge": RelationEdge.model_json_schema(),
            "allowed_pairs": ALLOWED_EDGES,
        },
    }


__all__ = [
    "ALLOWED_EDGES",
    "ComponentNode",
    "ProcessNode",
    "ProductNode",
    "RelationEdge",
    "SupplierNode",
    "ValidationError",
    "export_schema_bundle",
    "validate_node_payload",
]
