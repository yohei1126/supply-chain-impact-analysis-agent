# Scenario → catalog mapping

Maps user intents to **query-catalog.json** recipes. Schema details live in **bom-ontology** assets only.

## Supplier disruption

**User intent:** Which parts and finished goods are exposed if a supplier fails?

**Catalog path:** `federation_recipes.supplier_disruption_impact`

| Step | Query | Domain |
|------|-------|--------|
| 1 | `components_by_supplier` | sourcing |
| 2 | `impact_products_by_components` | ebom |

**Bridge:** `component_id` from step 1 → filter step 2.

**Tool shortcut:** `bom_supplier_impact` (runtime applies the same recipe chain).

## Supply path

**User intent:** How does a component relate to a finished product through the BOM?

**Catalog path:**

1. Try `direct_component_product_link` on **ebom** (single-hop `USED_IN`).
2. If multi-hop (component → process → product), plan separate domain queries or use `bom_supply_path`.

Allowed edge types for multi-hop: `USED_IN`, `INPUT_OF`, `PRODUCED_BY` (see `graph-context.json` domains).

## Manufacturing exposure

**User intent:** Which work centers / processes consume affected components?

**Catalog path:** `federation_recipes.supplier_disruption_with_routing` (adds `processes_by_components` on **routing**).

## Component search

**User intent:** Find catalog parts like a description, then trace suppliers.

**Flow:**

1. Resolve candidates via component master text search (name/material in DuckDB).
2. For each resolved `component_id`, use sourcing/ebom catalog queries or `bom_supplier_impact` on inferred suppliers.

## Indirect questions

Examples omit `SUP-xxx` / `COMP-xxx` on purpose. Resolve supplier or part names from `ontology.json` node fields, then select the catalog recipe above.

See [cypher-compose.md](cypher-compose.md) for the full composition checklist.
