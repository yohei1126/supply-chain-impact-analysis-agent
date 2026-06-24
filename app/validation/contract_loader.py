"""Load Graph Contract and align with domains/registry.py."""

from __future__ import annotations

from functools import lru_cache

from domains.registry import DOMAIN_GRAPHS
from ontology.contract.graph_contract import GraphContract
from ontology.contract.graph_contract import load_graph_contract as _load_contract


def assert_contract_matches_registry(contract: GraphContract) -> None:
    for graph_id, registry_spec in DOMAIN_GRAPHS.items():
        if graph_id not in contract.domains:
            raise ValueError(f"Graph Contract missing domain {graph_id!r}")
        domain = contract.domains[graph_id]
        yaml_nodes = set(domain.nodes)
        registry_nodes = set(registry_spec["nodes"])
        if yaml_nodes != registry_nodes:
            raise ValueError(
                f"domain {graph_id} nodes mismatch: contract={sorted(yaml_nodes)} "
                f"registry={sorted(registry_nodes)}"
            )
        yaml_edges = set(domain.edges)
        registry_edges = set(registry_spec["edges"])
        if yaml_edges != registry_edges:
            raise ValueError(
                f"domain {graph_id} edges mismatch: contract={sorted(yaml_edges)} "
                f"registry={sorted(registry_edges)}"
            )


@lru_cache(maxsize=1)
def get_graph_contract() -> GraphContract:
    contract = _load_contract()
    assert_contract_matches_registry(contract)
    return contract


__all__ = ["assert_contract_matches_registry", "get_graph_contract"]
