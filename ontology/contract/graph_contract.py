"""Graph Contract models and loader (YAML SSOT: graph_context.yaml)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ontology.schema import ALLOWED_EDGES

CONTRACT_PATH = Path(__file__).resolve().parent / "graph_context.yaml"


class EdgeSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_label: str = Field(alias="from")
    to_label: str = Field(alias="to")
    traverse_out: list[str] | None = None
    traverse_in_from: list[str] | None = None


class DomainSpec(BaseModel):
    graph_id: str
    owner_team: str
    sla_hours: int
    nodes: list[str]
    edges: dict[str, EdgeSpec]


class BridgeRule(BaseModel):
    entity: str
    key: str
    graphs: list[str]
    rule: str


class FederationStep(BaseModel):
    domain: str
    edge: str
    direction: str | None = None
    from_ref: str | None = Field(default=None, alias="from")
    yields: str


class FederationJoin(BaseModel):
    name: str
    steps: list[FederationStep]


class QualitySpec(BaseModel):
    on_ingest: list[str] = Field(default_factory=list)
    on_ingest_audit: list[str] = Field(default_factory=list)
    on_federate: list[dict[str, Any]] = Field(default_factory=list)


class GraphContract(BaseModel):
    version: str
    meta: dict[str, Any]
    identity: dict[str, Any]
    domains: dict[str, DomainSpec]
    federation: dict[str, Any]
    quality: QualitySpec

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphContract:
        contract = cls.model_validate(data)
        contract.assert_consistency_with_schema()
        return contract

    @classmethod
    def load(cls, path: Path | None = None) -> GraphContract:
        contract_path = path or CONTRACT_PATH
        raw = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Graph Contract YAML must be a mapping: {contract_path}")
        return cls.from_dict(raw)

    def assert_consistency_with_schema(self) -> None:
        """Ensure YAML edge shapes use ontology vocabulary and ALLOWED_EDGES."""
        valid_nodes = frozenset({"Component", "Process", "Supplier", "Product"})
        for graph_id, domain in self.domains.items():
            if domain.graph_id != graph_id:
                raise ValueError(f"domain key {graph_id!r} has graph_id {domain.graph_id!r}")
            unknown_nodes = set(domain.nodes) - valid_nodes
            if unknown_nodes:
                raise ValueError(f"domain {graph_id} has unknown nodes: {sorted(unknown_nodes)}")
            for edge_type, edge_spec in domain.edges.items():
                if edge_type not in ALLOWED_EDGES:
                    raise ValueError(f"domain {graph_id} declares unknown edge {edge_type!r}")
                allowed_source, allowed_target = ALLOWED_EDGES[edge_type]  # type: ignore[index]
                if (edge_spec.from_label, edge_spec.to_label) != (allowed_source, allowed_target):
                    raise ValueError(
                        f"domain {graph_id} edge {edge_type} endpoints "
                        f"{edge_spec.from_label}->{edge_spec.to_label} "
                        f"!= schema {allowed_source}->{allowed_target}"
                    )

        for join in self.federation_joins():
            for step in join.steps:
                if step.domain not in self.domains:
                    raise ValueError(f"join {join.name} references unknown domain {step.domain!r}")
                if step.edge not in self.domains[step.domain].edges:
                    raise ValueError(
                        f"join {join.name} references edge {step.edge!r} "
                        f"not declared in domain {step.domain!r}"
                    )

    def federation_joins(self) -> list[FederationJoin]:
        raw_joins = self.federation.get("joins", [])
        return [FederationJoin.model_validate(item) for item in raw_joins]

    def join_plan(self, name: str) -> FederationJoin:
        for join in self.federation_joins():
            if join.name == name:
                return join
        raise ValueError(f"unknown federation join: {name}")

    def on_federate_rules(self) -> dict[str, Any]:
        """Flatten quality.on_federate list entries into one rule map."""
        rules: dict[str, Any] = {}
        for item in self.quality.on_federate:
            if isinstance(item, dict):
                rules.update(item)
        return rules

    def on_ingest_checks(self) -> tuple[str, ...]:
        return tuple(self.quality.on_ingest)

    def on_ingest_audit_checks(self) -> tuple[str, ...]:
        return tuple(self.quality.on_ingest_audit)

    def validate_node(self, graph_id: str, node_label: str) -> None:
        domain = self.domains.get(graph_id)
        if domain is None:
            raise ValueError(f"unknown graph_id: {graph_id}")
        if node_label not in domain.nodes:
            raise ValueError(f"node type {node_label} is not allowed in graph {graph_id}")

    def validate_edge(
        self,
        graph_id: str,
        edge_type: str,
        source_label: str,
        target_label: str,
    ) -> None:
        domain = self.domains.get(graph_id)
        if domain is None:
            raise ValueError(f"unknown graph_id: {graph_id}")
        if edge_type not in domain.edges:
            raise ValueError(f"edge {edge_type} is not allowed in graph {graph_id}")
        spec = domain.edges[edge_type]
        if (source_label, target_label) != (spec.from_label, spec.to_label):
            raise ValueError(
                f"Graph Contract edge violation: {edge_type} in {graph_id} "
                f"requires {spec.from_label} -> {spec.to_label}, "
                f"got {source_label} -> {target_label}"
            )


@lru_cache(maxsize=1)
def load_graph_contract() -> GraphContract:
    return GraphContract.load()


__all__ = [
    "CONTRACT_PATH",
    "BridgeRule",
    "DomainSpec",
    "EdgeSpec",
    "FederationJoin",
    "GraphContract",
    "QualitySpec",
    "load_graph_contract",
]
