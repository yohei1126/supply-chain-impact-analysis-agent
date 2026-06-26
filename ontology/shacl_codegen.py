"""Generate SHACL shapes (Turtle) from ontology/schema.py for Neosemantics L3 validation."""

from __future__ import annotations

from typing import Any

from ontology.schema import ALLOWED_EDGES, export_schema_bundle

BOM_NS = "neo4j://graph.schema#"
SHAPES_HEADER = f"""@prefix bom: <{BOM_NS}> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

"""

STORAGE_PROPERTY_SPECS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("graph_id", {"datatype": "xsd:string", "minLength": 1}),
    ("as_of", {"datatype": "xsd:string", "minLength": 1}),
    ("graph_contract_version", {"datatype": "xsd:string", "minLength": 1}),
)


def _turtle_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _property_shape_block(path: str, constraints: dict[str, Any]) -> str:
    lines = [f"  sh:property [ sh:path bom:{path} ;"]
    if "datatype" in constraints:
        lines.append(f"    sh:datatype {constraints['datatype']} ;")
    if "minLength" in constraints:
        lines.append(f"    sh:minLength {constraints['minLength']} ;")
    if "maxLength" in constraints:
        lines.append(f"    sh:maxLength {constraints['maxLength']} ;")
    if "minExclusive" in constraints:
        lines.append(f"    sh:minExclusive {constraints['minExclusive']} ;")
    if "in_values" in constraints:
        values = " ".join(f'"{_turtle_string(item)}"' for item in constraints["in_values"])
        lines.append(f"    sh:in ( {values} ) ;")
    min_count = constraints.get("minCount", 1)
    max_count = constraints.get("maxCount", 1)
    lines.append(f"    sh:minCount {min_count} ;")
    lines.append(f"    sh:maxCount {max_count} ;")
    lines.append("  ] ;")
    return "\n".join(lines)


def _constraints_from_json_property(prop: dict[str, Any]) -> dict[str, Any]:
    constraints: dict[str, Any] = {"minCount": 1, "maxCount": 1}
    prop_type = prop.get("type")
    if prop_type == "string":
        constraints["datatype"] = "xsd:string"
        if "minLength" in prop:
            constraints["minLength"] = prop["minLength"]
        if "maxLength" in prop:
            constraints["maxLength"] = prop["maxLength"]
        if "enum" in prop:
            constraints["in_values"] = list(prop["enum"])
        return constraints
    if prop_type == "number":
        if prop.get("exclusiveMinimum") is not None:
            constraints["minExclusive"] = prop["exclusiveMinimum"]
        return constraints
    if prop_type == "integer":
        constraints["datatype"] = "xsd:integer"
        if prop.get("exclusiveMinimum") is not None:
            constraints["minExclusive"] = prop["exclusiveMinimum"]
        return constraints
    raise ValueError(f"Unsupported SHACL property schema: {prop!r}")


def _relationship_shape_block(edge_type: str, target_label: str) -> str:
    return "\n".join(
        [
            f"  sh:property [ sh:path bom:{edge_type} ;",
            f"    sh:class bom:{target_label} ;",
            "    sh:nodeKind sh:IRI ;",
            "  ] ;",
        ]
    )


def _node_shape(label: str, node_schema: dict[str, Any]) -> str:
    properties = node_schema["properties"]
    skip_keys = {"label"}
    blocks: list[str] = [
        f"bom:{label}Shape a sh:NodeShape ;",
        f"  sh:targetClass bom:{label} ;",
    ]
    for name, prop in properties.items():
        if name in skip_keys:
            continue
        blocks.append(_property_shape_block(name, _constraints_from_json_property(prop)))
    for name, constraints in STORAGE_PROPERTY_SPECS:
        blocks.append(_property_shape_block(name, dict(constraints)))
    for edge_type, (source_label, target_label) in ALLOWED_EDGES.items():
        if source_label == label:
            blocks.append(_relationship_shape_block(edge_type, target_label))
    blocks[-1] = blocks[-1].rstrip(" ;") + " ."
    return "\n".join(blocks)


def export_shacl_ttl() -> str:
    """Return SHACL Turtle generated from the live ontology schema."""
    bundle = export_schema_bundle()
    shapes = [_node_shape(label, schema) for label, schema in bundle["nodes"].items()]
    return SHAPES_HEADER + "\n\n".join(shapes) + "\n"


__all__ = ["BOM_NS", "export_shacl_ttl"]
