# Cypher composition protocol

Use this playbook with **generated assets only**. Never copy edge tables or MATCH strings into chat; read them from JSON at runtime.

## 1. Load assets in order

| Step | Asset | Purpose |
|------|-------|---------|
| 1 | `bom-ontology/assets/ontology.json` | Legal node types and `edges.allowed_pairs` |
| 2 | `bom-graph-explorer/assets/graph-context.json` | Which edges belong to `sourcing`, `ebom`, `routing` |
| 3 | `bom-graph-explorer/assets/query-catalog.json` | Named recipes and federation step lists |
| 4 | `bom-graph-explorer/assets/cypher-engine-profile.json` | Engine limits (Neo4j 5.x per domain database) |

## 2. Choose a strategy

**A. Named recipe exists** — use `query-catalog.json` → `queries.<name>`:

- Pick `graph_id` from the recipe entry.
- Use `edge_type`, `direction`, `filter_mode`, and `anchor` / `yields` as the contract.
- For federation, follow `federation_recipes` step order and join on `bridge` (usually `component_id`).

**B. No recipe fits** — compose one **single-domain, single-edge-type** query:

1. Confirm the edge is in `ontology.json` → `edges.allowed_pairs`.
2. Confirm the edge is listed under `graph-context.json` → `domains.<graph_id>.edges`.
3. Write `MATCH (source:FromLabel)-[:EDGE]->(target:ToLabel)` using the **exact** from/to labels from `allowed_pairs`.
4. Add `WHERE` only on labels/properties allowed for that domain.
5. Do not cross domains in one Cypher string — join in a second step on `identity.bridges`.

## 3. Federation joins

From `graph-context.json`:

- Master bridge: **Component.id** across `sourcing`, `ebom`, `routing`.
- Product.id bridges `ebom` and `routing` only.

Typical disruption flow (`federation_recipes.supplier_disruption_impact`):

1. `sourcing` — `components_by_supplier` (anchor `supplier_id`) → yields `component_id`
2. `ebom` — `impact_products_by_components` (filter component ids) → yields `product_id`

Optional third step: `routing` — `processes_by_components`.

## 4. Pre-flight checklist

Before emitting Cypher, verify:

- [ ] Every `EDGE` in `MATCH` is in `allowed_pairs` with correct **direction** (source → target).
- [ ] Every node label appears in the target domain's `nodes` list.
- [ ] Query targets **one** `graph_id` per execute call.
- [ ] Federation carries `component_id` (or documented bridge key) between steps.
- [ ] Use parameterized queries (`$supplier_id`, `$ids`) where the engine profile allows.
- [ ] Prefer catalog query names over ad-hoc patterns when a recipe matches the user goal.

## 5. Map user language to graph (indirect goals)

Resolve entities from **ontology field semantics**, not from memorized IDs:

| User clue | Graph hint |
|-----------|------------|
| Country + material + supplier role | `Supplier` node (`country`, supplier name) → `components_by_supplier` |
| Part name / role (e.g. drive shaft) | `Component.name` → then path or impact recipes |
| Product line name | `Product.name` → pair with component for `direct_component_product_link` or path tools |
| Similar parts / shortage wording | component master search first, then catalog impact queries on resolved `component_id` |

When IDs are unknown, plan **resolve then query** (LLM inference or component master search), then call tools or emit catalog-based Cypher with resolved ids.

## 6. When to call tools instead of raw Cypher

If the host exposes `bom_supplier_impact` or `bom_supply_path`, prefer tools for execution. Use this protocol to **validate** tool choice and to explain which catalog recipes the runtime should apply.
