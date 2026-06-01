import pytest

from bom_graph.schema import RelationEdge, validate_node_payload


def test_validate_node_payload_unknown_type_raises() -> None:
    with pytest.raises(ValueError):
        validate_node_payload("UnknownType", {"id": "X"})


def test_relation_edge_allows_valid_pair() -> None:
    edge = RelationEdge(
        source_label="Component",
        source_id="COMP-1",
        target_label="Supplier",
        target_id="SUP-1",
        edge_type="SUPPLIED_BY",
        properties={"lead_time_days": 10},
    )
    assert edge.edge_type == "SUPPLIED_BY"


def test_relation_edge_rejects_invalid_pair() -> None:
    with pytest.raises(ValueError):
        RelationEdge(
            source_label="Supplier",
            source_id="SUP-1",
            target_label="Component",
            target_id="COMP-1",
            edge_type="SUPPLIED_BY",
            properties={},
        )
