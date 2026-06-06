from __future__ import annotations

from typing import Any

from bom_graph.hybrid_store import UnifiedBomContextStore
from bom_graph.lance_graph_store import LanceGraphStore


SUPPLIERS: list[dict[str, Any]] = [
    {"id": "SUP-001", "company_name": "Nihon Steel", "country": "JP", "risk_level": "High"},
    {"id": "SUP-002", "company_name": "Euro Brass GmbH", "country": "DE", "risk_level": "Medium"},
    {"id": "SUP-003", "company_name": "Pacific Plastics", "country": "US", "risk_level": "Low"},
]

PRODUCTS: list[dict[str, Any]] = [
    {"id": "PROD-900", "name": "Industrial Pump", "version": "v3.2"},
    {"id": "PROD-901", "name": "Servo Motor Drive", "version": "v2.1"},
    {"id": "PROD-902", "name": "Valve Manifold", "version": "v1.4"},
]

PROCESSES: list[dict[str, Any]] = [
    {"id": "PROC-10", "name": "CNC Machining", "work_center": "WC-1", "cycle_time_min": 22.0},
    {"id": "PROC-20", "name": "Heat Treatment", "work_center": "WC-7", "cycle_time_min": 35.0},
    {"id": "PROC-30", "name": "Final Assembly", "work_center": "WC-12", "cycle_time_min": 48.0},
    {"id": "PROC-40", "name": "Functional Test", "work_center": "WC-15", "cycle_time_min": 18.0},
]

# component_id -> supplier, products[], input processes[]
COMPONENT_BOM: list[dict[str, Any]] = [
    {
        "component": {"id": "COMP-100", "name": "Frame", "material": "Steel", "cost": 1500.0},
        "supplier": "SUP-001",
        "products": ["PROD-900"],
        "processes": ["PROC-10", "PROC-20"],
        "lead_time_days": 21,
    },
    {
        "component": {"id": "COMP-101", "name": "Valve", "material": "Brass", "cost": 600.0},
        "supplier": "SUP-002",
        "products": ["PROD-900", "PROD-902"],
        "processes": ["PROC-30"],
        "lead_time_days": 12,
    },
    {
        "component": {"id": "COMP-102", "name": "Housing", "material": "Steel", "cost": 1100.0},
        "supplier": "SUP-001",
        "products": ["PROD-900"],
        "processes": ["PROC-10"],
        "lead_time_days": 18,
    },
    {
        "component": {"id": "COMP-103", "name": "Drive Shaft", "material": "Steel", "cost": 890.0},
        "supplier": "SUP-001",
        "products": ["PROD-901"],
        "processes": ["PROC-10", "PROC-20"],
        "lead_time_days": 16,
    },
    {
        "component": {"id": "COMP-104", "name": "Bearing Set", "material": "Steel", "cost": 320.0},
        "supplier": "SUP-001",
        "products": ["PROD-901"],
        "processes": ["PROC-30"],
        "lead_time_days": 10,
    },
    {
        "component": {"id": "COMP-105", "name": "Stator Lamination", "material": "Steel", "cost": 740.0},
        "supplier": "SUP-001",
        "products": ["PROD-901"],
        "processes": ["PROC-10"],
        "lead_time_days": 20,
    },
    {
        "component": {"id": "COMP-106", "name": "Copper Winding", "material": "Brass", "cost": 410.0},
        "supplier": "SUP-002",
        "products": ["PROD-901"],
        "processes": ["PROC-30"],
        "lead_time_days": 14,
    },
    {
        "component": {"id": "COMP-107", "name": "End Cap", "material": "Steel", "cost": 95.0},
        "supplier": "SUP-003",
        "products": ["PROD-901"],
        "processes": ["PROC-30"],
        "lead_time_days": 8,
    },
    {
        "component": {"id": "COMP-108", "name": "Seal Ring", "material": "Brass", "cost": 45.0},
        "supplier": "SUP-002",
        "products": ["PROD-900", "PROD-902"],
        "processes": ["PROC-30"],
        "lead_time_days": 7,
    },
    {
        "component": {"id": "COMP-109", "name": "Manifold Body", "material": "Steel", "cost": 980.0},
        "supplier": "SUP-003",
        "products": ["PROD-902"],
        "processes": ["PROC-10"],
        "lead_time_days": 15,
    },
    {
        "component": {"id": "COMP-110", "name": "Port Insert", "material": "Brass", "cost": 120.0},
        "supplier": "SUP-002",
        "products": ["PROD-902"],
        "processes": ["PROC-30"],
        "lead_time_days": 9,
    },
    {
        "component": {"id": "COMP-111", "name": "Gasket Kit", "material": "Brass", "cost": 55.0},
        "supplier": "SUP-002",
        "products": ["PROD-902"],
        "processes": ["PROC-30", "PROC-40"],
        "lead_time_days": 6,
    },
]

PRODUCT_PROCESSES: list[tuple[str, str]] = [
    ("PROD-900", "PROC-30"),
    ("PROD-900", "PROC-40"),
    ("PROD-901", "PROC-30"),
    ("PROD-901", "PROC-40"),
    ("PROD-902", "PROC-30"),
    ("PROD-902", "PROC-40"),
]


def seed_complex_bom(
    graph: LanceGraphStore,
    unified: UnifiedBomContextStore | None = None,
) -> dict[str, int]:
    """
    Load a multi-product BOM: 3 suppliers, 3 products, 4 processes, 12 components.

    Writes are split across three domain LanceDB datasets under the graph store base
    path (``ebom/``, ``routing/``, ``sourcing/``). Components are replicated in each
    domain that references them; edges are routed by type.

    Every write goes through ontology validators in LanceGraphStore / UnifiedBomContextStore.
    Invalid payloads raise pydantic.ValidationError or ValueError (edge constraints).

    Returns counts for logging. Prefer a fresh ``data/lancedb`` when re-seeding.
    """
    for supplier in SUPPLIERS:
        graph.add_node("Supplier", supplier)
    for product in PRODUCTS:
        graph.add_node("Product", product)
    for process in PROCESSES:
        graph.add_node("Process", process)

    for row in COMPONENT_BOM:
        comp = row["component"]
        if unified is not None:
            unified.upsert_component(comp)
        else:
            graph.add_node("Component", comp)

        cid = comp["id"]
        graph.add_edge(
            {
                "source_label": "Component",
                "source_id": cid,
                "target_label": "Supplier",
                "target_id": row["supplier"],
                "edge_type": "SUPPLIED_BY",
                "properties": {"lead_time_days": row.get("lead_time_days", 14)},
            }
        )
        for pid in row["products"]:
            graph.add_edge(
                {
                    "source_label": "Component",
                    "source_id": cid,
                    "target_label": "Product",
                    "target_id": pid,
                    "edge_type": "USED_IN",
                    "properties": {},
                }
            )
        for proc in row["processes"]:
            graph.add_edge(
                {
                    "source_label": "Component",
                    "source_id": cid,
                    "target_label": "Process",
                    "target_id": proc,
                    "edge_type": "INPUT_OF",
                    "properties": {"qty": 1},
                }
            )

    for product_id, process_id in PRODUCT_PROCESSES:
        graph.add_edge(
            {
                "source_label": "Product",
                "source_id": product_id,
                "target_label": "Process",
                "target_id": process_id,
                "edge_type": "PRODUCED_BY",
                "properties": {},
            }
        )

    return {
        "suppliers": len(SUPPLIERS),
        "products": len(PRODUCTS),
        "processes": len(PROCESSES),
        "components": len(COMPONENT_BOM),
    }
