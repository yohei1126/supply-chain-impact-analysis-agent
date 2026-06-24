"""Graph Contract loader and registry alignment."""

from __future__ import annotations

import pytest

from app.validation.contract_loader import assert_contract_matches_registry, get_graph_contract
from ontology.contract.graph_contract import load_graph_contract


def test_load_graph_contract_from_yaml() -> None:
    contract = load_graph_contract()
    assert contract.version == "1.0.0"
    assert set(contract.domains) == {"ebom", "routing", "sourcing"}


def test_graph_contract_matches_registry() -> None:
    contract = load_graph_contract()
    assert_contract_matches_registry(contract)


def test_get_graph_contract_is_cached() -> None:
    assert get_graph_contract() is get_graph_contract()


def test_validate_edge_rejects_wrong_domain() -> None:
    contract = load_graph_contract()
    with pytest.raises(ValueError, match="not allowed in graph ebom"):
        contract.validate_edge("ebom", "SUPPLIED_BY", "Component", "Supplier")


def test_validate_node_rejects_wrong_domain() -> None:
    contract = load_graph_contract()
    with pytest.raises(ValueError, match="Supplier.*not allowed in graph ebom"):
        contract.validate_node("ebom", "Supplier")
