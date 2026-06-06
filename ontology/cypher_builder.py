"""Generate Cypher from ontology/schema.py — SSOT for patterns and RETURN columns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ontology.schema import ALLOWED_EDGES, EdgeType, NodeLabel

FilterMode = Literal["anchor_property", "source_id_in", "endpoint_pair"]

_ID_PATTERN = __import__("re").compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class CypherQuerySpec:
    """Named query recipe derived from ontology edge semantics."""

    query_name: str
    edge_type: EdgeType
    filter_mode: FilterMode
    anchor_label: NodeLabel | None = None
    anchor_param: str | None = None
    order_by: tuple[str, ...] = ()
    aggregate: bool = False


NODE_ALIASES: dict[NodeLabel, str] = {
    "Component": "c",
    "Supplier": "s",
    "Product": "p",
    "Process": "pr",
}

_NODE_FIELD_ALIASES: dict[NodeLabel, dict[str, str]] = {
    "Component": {
        "id": "component_id",
        "name": "component_name",
        "material": "material",
        "cost": "cost",
    },
    "Supplier": {
        "id": "supplier_id",
        "company_name": "supplier_name",
        "country": "country",
        "risk_level": "risk_level",
    },
    "Product": {
        "id": "product_id",
        "name": "product_name",
        "version": "product_version",
    },
    "Process": {
        "id": "process_id",
        "name": "process_name",
        "work_center": "work_center",
        "cycle_time_min": "cycle_time_min",
    },
}

_EDGE_PROPERTY_ALIASES: dict[EdgeType, dict[str, str]] = {
    "SUPPLIED_BY": {"lead_time_days": "lead_time_days"},
    "USED_IN": {},
    "INPUT_OF": {},
    "PRODUCED_BY": {},
}

QUERY_SPECS: dict[str, CypherQuerySpec] = {
    "components_by_supplier": CypherQuerySpec(
        query_name="components_by_supplier",
        edge_type="SUPPLIED_BY",
        filter_mode="anchor_property",
        anchor_label="Supplier",
        anchor_param="supplier_id",
        order_by=("c.cost DESC",),
    ),
    "products_by_components": CypherQuerySpec(
        query_name="products_by_components",
        edge_type="USED_IN",
        filter_mode="source_id_in",
        order_by=("p.id", "c.id"),
    ),
    "processes_by_components": CypherQuerySpec(
        query_name="processes_by_components",
        edge_type="INPUT_OF",
        filter_mode="source_id_in",
        order_by=("pr.work_center", "c.id"),
    ),
    "supplier_counts_by_components": CypherQuerySpec(
        query_name="supplier_counts_by_components",
        edge_type="SUPPLIED_BY",
        filter_mode="source_id_in",
        aggregate=True,
    ),
    "impact_products_by_components": CypherQuerySpec(
        query_name="impact_products_by_components",
        edge_type="USED_IN",
        filter_mode="source_id_in",
        order_by=("c.cost DESC", "p.id"),
    ),
    "direct_component_product_link": CypherQuerySpec(
        query_name="direct_component_product_link",
        edge_type="USED_IN",
        filter_mode="endpoint_pair",
    ),
}


def validate_graph_id(value: str) -> str:
    if not _ID_PATTERN.match(value):
        raise ValueError(f"Invalid id: {value!r}")
    return value


def alias_for(label: NodeLabel) -> str:
    return NODE_ALIASES[label]


def edge_endpoints(edge_type: EdgeType) -> tuple[NodeLabel, NodeLabel]:
    return ALLOWED_EDGES[edge_type]


def _return_node_columns(label: NodeLabel) -> list[str]:
    alias = alias_for(label)
    return [f"{alias}.{field} AS {out}" for field, out in _NODE_FIELD_ALIASES[label].items()]


def _return_edge_columns(edge_type: EdgeType, rel_var: str = "r") -> list[str]:
    return [
        f"{rel_var}.{prop} AS {out}" for prop, out in _EDGE_PROPERTY_ALIASES.get(edge_type, {}).items()
    ]


def _match_line(
    spec: CypherQuerySpec,
    *,
    source_id: str | None = None,
    target_id: str | None = None,
) -> str:
    source_label, target_label = edge_endpoints(spec.edge_type)
    source = alias_for(source_label)
    target = alias_for(target_label)
    has_edge_props = bool(_EDGE_PROPERTY_ALIASES.get(spec.edge_type))
    rel = f"r:{spec.edge_type}" if has_edge_props else f":{spec.edge_type}"

    if spec.filter_mode == "endpoint_pair":
        if not source_id or not target_id:
            raise ValueError("endpoint_pair requires source_id and target_id")
        return (
            f"MATCH ({source}:{source_label} {{id: '{validate_graph_id(source_id)}'}})-[{rel}]->"
            f"({target}:{target_label} {{id: '{validate_graph_id(target_id)}'}})"
        )

    if spec.filter_mode == "anchor_property" and spec.anchor_label == target_label and spec.anchor_param:
        return (
            f"MATCH ({source}:{source_label})-[{rel}]->"
            f"({target}:{target_label} {{id: ${spec.anchor_param}}})"
        )

    return f"MATCH ({source}:{source_label})-[{rel}]->({target}:{target_label})"


def _where_clause(spec: CypherQuerySpec, *, component_ids_literal: str | None) -> str:
    if spec.filter_mode == "source_id_in":
        if not component_ids_literal:
            raise ValueError("source_id_in requires component_ids_literal")
        source_label, _ = edge_endpoints(spec.edge_type)
        source = alias_for(source_label)
        return f"WHERE {source}.id IN [{component_ids_literal}]"
    return ""


def _return_clause(spec: CypherQuerySpec) -> str:
    source_label, target_label = edge_endpoints(spec.edge_type)
    source = alias_for(source_label)
    target_alias = alias_for(target_label)

    if spec.aggregate and spec.edge_type == "SUPPLIED_BY":
        return f"RETURN {source}.id AS component_id, count({alias_for('Supplier')}) AS supplier_count"

    if spec.query_name == "impact_products_by_components":
        return (
            "RETURN\n"
            f"  {source}.id AS component_id,\n"
            f"  {source}.name AS component_name,\n"
            f"  {source}.cost AS component_cost,\n"
            f"  {target_alias}.id AS product_id,\n"
            f"  {target_alias}.name AS product_name"
        )

    if spec.query_name == "direct_component_product_link":
        return (
            f"RETURN {source}.id AS from_component_id, "
            f"{target_alias}.id AS to_product_id, "
            f"'{spec.edge_type}' AS edge_type"
        )

    columns: list[str] = []
    if source_label == "Component":
        columns.extend(_return_node_columns("Component"))
    if target_label == "Supplier":
        columns.extend(_return_node_columns("Supplier"))
    if target_label == "Product":
        columns.extend(_return_node_columns("Product"))
    if target_label == "Process":
        columns.extend(_return_node_columns("Process"))
    if _EDGE_PROPERTY_ALIASES.get(spec.edge_type):
        columns.extend(_return_edge_columns(spec.edge_type))

    return "RETURN\n  " + ",\n  ".join(columns)


def build_query(
    spec: CypherQuerySpec,
    *,
    component_ids_literal: str | None = None,
    source_id: str | None = None,
    target_id: str | None = None,
) -> str:
    parts = [_match_line(spec, source_id=source_id, target_id=target_id)]
    where = _where_clause(spec, component_ids_literal=component_ids_literal)
    if where:
        parts.append(where)
    parts.append(_return_clause(spec))
    if spec.order_by:
        parts.append(f"ORDER BY {', '.join(spec.order_by)}")
    return "\n".join(parts).strip()


def build_query_by_name(
    name: str,
    *,
    component_ids_literal: str | None = None,
    source_id: str | None = None,
    target_id: str | None = None,
) -> str:
    if name not in QUERY_SPECS:
        raise KeyError(f"Unknown ontology query spec: {name}")
    return build_query(
        QUERY_SPECS[name],
        component_ids_literal=component_ids_literal,
        source_id=source_id,
        target_id=target_id,
    )


def yields_for_spec(spec: CypherQuerySpec) -> list[str]:
    """Column names returned by this query spec (for agent catalog export)."""
    if spec.aggregate and spec.edge_type == "SUPPLIED_BY":
        return ["component_id", "supplier_count"]
    if spec.query_name == "impact_products_by_components":
        return [
            "component_id",
            "component_name",
            "component_cost",
            "product_id",
            "product_name",
        ]
    if spec.query_name == "direct_component_product_link":
        return ["from_component_id", "to_product_id", "edge_type"]

    source_label, target_label = edge_endpoints(spec.edge_type)
    columns: list[str] = []
    if source_label == "Component":
        columns.extend(_NODE_FIELD_ALIASES["Component"].values())
    if target_label == "Supplier":
        columns.extend(_NODE_FIELD_ALIASES["Supplier"].values())
    if target_label == "Product":
        columns.extend(_NODE_FIELD_ALIASES["Product"].values())
    if target_label == "Process":
        columns.extend(_NODE_FIELD_ALIASES["Process"].values())
    columns.extend(_EDGE_PROPERTY_ALIASES.get(spec.edge_type, {}).values())
    return columns


def export_query_spec_entry(spec: CypherQuerySpec) -> dict[str, object]:
    source_label, target_label = edge_endpoints(spec.edge_type)
    entry: dict[str, object] = {
        "edge_type": spec.edge_type,
        "direction": f"{source_label}->{target_label}",
        "filter_mode": spec.filter_mode,
        "yields": yields_for_spec(spec),
    }
    if spec.anchor_label:
        entry["anchor"] = {"label": spec.anchor_label, "param": spec.anchor_param}
    if spec.order_by:
        entry["order_by"] = list(spec.order_by)
    if spec.aggregate:
        entry["aggregate"] = True
    return entry
