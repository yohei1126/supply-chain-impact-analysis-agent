# Exploration workflows

## Supplier impact

**Question:** Which components and products are affected if supplier `S` is disrupted?

1. Start from `Supplier` node `S`.
2. Traverse incoming `SUPPLIED_BY` edges to `Component` nodes.
3. For each component, follow `USED_IN` to `Product` nodes.
4. Return component/product pairs with cost and lead-time context when available.

Tool: `bom_supplier_impact` with `supplier_id`.

## Shortest supply path

**Question:** How does component `C` connect to product `P`?

Traverse only: `USED_IN`, `INPUT_OF`, `PRODUCED_BY`.

Tool: `bom_supply_path` with `from_component_id`, `to_product_id`.

## Hybrid vector -> rdb -> graph

**Question:** Find parts similar to a natural-language query, then explain supply impact.

1. **Vector (LanceDB):** similarity search over component embeddings.
2. **RDB (DuckDB):** fetch authoritative attributes (name, material, cost).
3. **Graph (LanceGraph):** run supplier impact or path analysis on resolved component IDs.

Implementation: `UnifiedBomContextStore.find_supplier_impact_for_query()`.
