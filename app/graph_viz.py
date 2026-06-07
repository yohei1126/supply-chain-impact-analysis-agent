from __future__ import annotations

from typing import Any

from app.agent.types import ToolCall

NodeKey = tuple[str, str]

LABEL_COLORS = {
    "Supplier": "#e8a838",
    "Component": "#5b9bd5",
    "Product": "#5ecf8a",
    "Process": "#b088f9",
}


def extract_seed_keys(
    tool_calls: list[ToolCall],
    results: list[dict[str, Any]],
) -> set[NodeKey]:
    """Collect node keys referenced by tool calls and their JSON results."""
    seeds: set[NodeKey] = set()

    for call, result in zip(tool_calls, results):
        args = call.arguments
        if call.name == "bom_supplier_impact":
            seeds.add(("Supplier", str(args.get("supplier_id", ""))))
        elif call.name == "bom_supply_path":
            seeds.add(("Component", str(args.get("from_component_id", ""))))
            seeds.add(("Product", str(args.get("to_product_id", ""))))

        op = result.get("operation", call.name)
        data = result.get("data") or []

        if op == "supplier_impact":
            for row in data:
                if row.get("supplier_id"):
                    seeds.add(("Supplier", row["supplier_id"]))
                if row.get("component_id"):
                    seeds.add(("Component", row["component_id"]))
                if row.get("product_id"):
                    seeds.add(("Product", row["product_id"]))
        elif op == "supply_path":
            for block in data:
                for node in block.get("nodes") or []:
                    labels = node.get("labels") or []
                    if labels and node.get("id"):
                        seeds.add((labels[0], node["id"]))

    return {(label, node_id) for label, node_id in seeds if label and node_id}


def build_graph_view(store: Any, seeds: set[NodeKey], *, expand_hops: int = 1) -> dict[str, Any]:
    """
    Export an induced subgraph for visualization (nodes + edges).

    expand_hops: include neighbors up to N hops from seed nodes.
    """
    all_nodes = store._all_nodes()
    all_edges = store._all_edges()
    node_by_key = {(n["label"], n["id"]): n for n in all_nodes}

    active: set[NodeKey] = set(seeds)
    for _ in range(max(0, expand_hops)):
        next_active: set[NodeKey] = set(active)
        for edge in all_edges:
            src: NodeKey = (edge["source_label"], edge["source_id"])
            tgt: NodeKey = (edge["target_label"], edge["target_id"])
            if src in active or tgt in active:
                next_active.add(src)
                next_active.add(tgt)
        active = next_active

    vis_nodes: list[dict[str, Any]] = []
    for key in sorted(active):
        raw = node_by_key.get(key)
        if not raw:
            continue
        props = raw.get("properties") or {}
        label = key[0]
        name = props.get("name") or props.get("company_name") or key[1]
        vis_nodes.append(
            {
                "id": f"{label}:{key[1]}",
                "label": label,
                "entity_id": key[1],
                "title": f"{label} {key[1]}\n{name}",
                "display": f"{name}\n({key[1]})",
                "color": LABEL_COLORS.get(label, "#8b9cb3"),
                "seed": key in seeds,
            }
        )

    node_ids = {n["id"] for n in vis_nodes}
    vis_edges: list[dict[str, Any]] = []
    for edge in all_edges:
        src_id = f"{edge['source_label']}:{edge['source_id']}"
        tgt_id = f"{edge['target_label']}:{edge['target_id']}"
        if src_id in node_ids and tgt_id in node_ids:
            vis_edges.append(
                {
                    "from": src_id,
                    "to": tgt_id,
                    "label": edge["edge_type"],
                    "arrows": "to",
                }
            )

    return {
        "nodes": vis_nodes,
        "edges": vis_edges,
        "seed_count": len(seeds),
        "node_count": len(vis_nodes),
        "edge_count": len(vis_edges),
    }


def graph_view_for_run(store: Any, tool_calls: list[ToolCall], results: list[dict[str, Any]]) -> dict[str, Any]:
    seeds = extract_seed_keys(tool_calls, results)
    if not seeds:
        return {"nodes": [], "edges": [], "seed_count": 0, "node_count": 0, "edge_count": 0}
    return build_graph_view(store, seeds, expand_hops=1)
