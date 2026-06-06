# Ontology on LanceDB: schema-light storage, application-layer meaning

How to think about **LanceDB** (schemaless / schema-light) versus a **useful enterprise ontology** (schema, constraints, semantics) that preserves integrity across three domain graphs and supports **logical federation** by an AI agent.

**Audience:** data stewards, ontology authors, and agent developers.

**Related:** [graph-context.md](graph-context.md) (cross-graph federation contract), [enterprise-graph-design.md](enterprise-graph-design.md), [supply-chain-disruption-response.md](supply-chain-disruption-response.md), [AGENTS.md](../AGENTS.md) (authoring SSOT in `ontology/schema.py`).

---

## 1. Is LanceDB schemaless or schema-light?

**Short answer:** Treat LanceDB as **schema-light storage**, not as your ontology engine.

| Aspect | LanceDB behavior | This repository |
|--------|------------------|-----------------|
| Table creation | Infers schema from first batch; columns can evolve | `graph_nodes`, `graph_edges`, `component_vectors` |
| Column typing | Arrow types per column; flexible adds | Fixed thin columns + `properties_json` blob |
| Constraints | No foreign keys, no CHECK, no graph semantics | None at DB level |
| Referential integrity | Not enforced | `LanceGraphStore.add_edge` checks endpoints in Python |
| Domain validation | Not enforced | Pydantic in `ontology/schema.py` on write |

### 1.1 What Lance actually stores (graph)

```text
graph_nodes:  id, label, properties_json
graph_edges:  source_id, source_label, target_id, target_label, edge_type, properties_json
```

- **`label`** — coarse node kind (`Component`, `Product`, …).
- **`properties_json`** — **schema-free** at the Lance layer; shape is enforced only when code calls `validate_node_payload`.
- **Edge columns** — structural hint only; Lance does not know that `SUPPLIED_BY` must be Component → Supplier.

So: the **physical model is intentionally generic** (property-graph-as-rows). That is a feature for multi-domain graphs on one engine, not a substitute for an ontology.

### 1.2 Comparison to “schema-full” stores

| Capability | RDB (DuckDB) | LanceDB (this use) | Ontology layer (Pydantic + bundles) |
|------------|--------------|--------------------|-------------------------------------|
| Column types | Enforced | Light / evolvable | Per node type in JSON Schema export |
| FK / referential integrity | Can enforce | No | App on write + audit jobs |
| Graph edge rules | N/A | No | `ALLOWED_EDGES` + domain bundles |
| Semantics for agents | No | No | Skill + federation contract |
| Vector search | Separate | Native table | Embedding policy outside ontology |

**Implication:** If you rely on Lance alone, you get a **bag of labeled JSON**. Enterprise usefulness comes from **layers above Lance**.

---

## 2. What “ontology” means in this stack

Avoid equating ontology with “OWL file” or “Lance column list”. For manufacturing supply-chain graphs on Lance, a **practical ontology** is a **versioned contract** with four parts:

| Part | Question it answers | Where it lives |
|------|---------------------|----------------|
| **Schema** | What fields does each node type have? | `ontology/schema.py` → `ontology.json` |
| **Constraints** | What values and relationships are legal? | Pydantic validators, `ALLOWED_EDGES`, domain subsets |
| **Semantics** | What do types and edges *mean* in business language? | Skill prose, edge glossary, federation doc |
| **Integrity policy** | How are writes and cross-graph IDs kept consistent? | Ingest code, DuckDB master, audit playbooks |

```text
                    ┌─────────────────────────────────┐
                    │  Semantics (agents + humans)     │
                    │  glossary, domains, playbooks    │
                    └───────────────┬─────────────────┘
                                    │ informs
                    ┌───────────────▼─────────────────┐
                    │  Constraints (validation)        │
                    │  Pydantic, ALLOWED_EDGES, graph_id│
                    └───────────────┬─────────────────┘
                                    │ enforced on write
                    ┌───────────────▼─────────────────┐
                    │  Schema (shapes)                 │
                    │  ComponentNode, RelationEdge, …  │
                    └───────────────┬─────────────────┘
                                    │ serialized to
                    ┌───────────────▼─────────────────┐
                    │  LanceDB (schema-light rows)     │
                    │  id, label, properties_json      │
                    └─────────────────────────────────┘
```

---

## 3. Three-layer model (recommended)

### Layer 0 — LanceDB (schema-light, domain-agnostic)

**Purpose:** Durable, embeddable, columnar storage + vector search.

**Keep the physical schema minimal and stable:**

```text
graph_nodes:
  graph_id          # ebom | routing | sourcing
  id
  label
  properties_json
  source_system     # optional ingest metadata
  as_of             # optional snapshot time (ISO string)

graph_edges:
  graph_id
  source_id, source_label
  target_id, target_label
  edge_type
  properties_json
  source_system
  as_of
```

Do **not** add per-domain Lance tables for every node attribute. Do **not** expect Lance to validate `risk_level` enums.

### Layer 1 — Application schema + constraints (authoring SSOT)

**Purpose:** Deterministic validation at the **write boundary** (ingest, seed, API).

**Already in this repo:**

| Mechanism | Example |
|-----------|---------|
| Node shape | `ComponentNode.cost > 0`, `Supplier.country` ISO-2 |
| Edge domain/range | `USED_IN`: Component → Product only |
| Endpoint existence | `add_edge` rejects missing source/target nodes |
| Single authoring file | `ontology/schema.py` |
| Published artifact | `skills/bom-ontology/assets/ontology.json` |

**Extend for three domain teams:**

```python
# Conceptual — domain views on the same SSOT
DOMAIN_GRAPHS = {
    "ebom": {
        "nodes": {"Component", "Product"},
        "edges": {"USED_IN"},
    },
    "routing": {
        "nodes": {"Component", "Process", "Product"},
        "edges": {"INPUT_OF", "PRODUCED_BY"},
    },
    "sourcing": {
        "nodes": {"Component", "Supplier"},
        "edges": {"SUPPLIED_BY"},
    },
}
```

Ingest pipelines pass `graph_id`; validators reject edges outside that domain’s bundle.

### Layer 2 — Semantics + federation (agent-facing)

**Purpose:** Humans and agents agree on **meaning** and **how to join graphs logically** without merging Lance datasets.

This layer is **not** fully expressible in JSON Schema alone. Include:

| Artifact | Contents |
|----------|----------|
| **Edge glossary** | Natural-language direction, e.g. “`SUPPLIED_BY`: the component at `source` is supplied by the supplier at `target`” |
| **Federation keys** | `Component.id` required across domains; `Product.id` for ebom ↔ routing |
| **Traversal permissions** | Per domain: which `edge_type` values tools may follow |
| **Ownership** | Which team may write which `graph_id` |
| **Playbook hooks** | `supplier_disruption` starts in `sourcing`, then joins on `component_id` |
| **Geo / lane anchors** | Hormuz news → `Supplier.country` or `shipping_lane` edge props — not raw LLM graph walk |

Ship to agents via **Agent Skills** (`bom-ontology`, `bom-graph-explorer`, future `bom-disruption-response`), not via Lance DDL.

---

## 4. Schema vs constraints vs semantics (detailed)

### 4.1 Schema (structure)

**What:** Field names, types, required vs optional.

| Node | Schema highlights |
|------|-------------------|
| `Component` | `id`, `name`, `material`, `cost` |
| `Supplier` | `company_name`, `country`, `risk_level` |
| `Process` | `work_center`, `cycle_time_min` |
| `Product` | `name`, `version` |

**Role:** Serialization, API contracts, generated `ontology.json` for LLM tool context.

**Not enough for:** cross-graph joins, disruption playbooks, or “which graph do I query?”

### 4.2 Constraints (rules)

**What:** Invariants that must hold for data to be trusted.

| Constraint class | Example | Enforced where |
|------------------|---------|----------------|
| **Value** | `cost > 0`, `country` length 2 | Pydantic |
| **Structural** | `edge_type` ∈ allowed set for domain | Pydantic + `DOMAIN_GRAPHS` |
| **Referential (intra-graph)** | Edge endpoints exist in same `graph_id` | `LanceGraphStore.add_edge` |
| **Referential (cross-graph)** | `COMP-103` in sourcing exists in ebom master | Federation / DuckDB registry |
| **Cardinality (soft)** | One primary supplier per component | Ingest policy or audit, not Lance |
| **Temporal** | `as_of` not in the future | Ingest validator |

**Role:** Keep Lance rows honest **before** they land. Fail closed on ingest; do not repair in the agent.

### 4.3 Semantics (meaning)

**What:** Business interpretation agents need for **logical integration**.

| Semantic element | Example |
|------------------|---------|
| **Type definition** | “Component: a purchasable or manufacturable item identified by enterprise part number” |
| **Edge direction** | Agents must not reverse `SUPPLIED_BY` when traversing |
| **Domain scope** | `USED_IN` is engineering truth; not updated by MES |
| **Join semantics** | “Same `Component.id` in ebom and sourcing denotes the same real-world part” |
| **Deprecated / alias** | `COMP-103-A` supersedes `COMP-103` — mapping in master, not Lance |
| **Tool mapping** | `sourcing.components_by_supplier` may only use `SUPPLIED_BY` |

**Role:** Planner selects correct domain order; summarizer uses correct vocabulary; auditors understand evidence.

**Realistic scope:** Glossary + federation contract + domain bundles. **Not** full automated reasoning (OWL inference, SHACL at ingest scale) unless you add a dedicated reasoner — usually unnecessary for this agent pattern.

---

## 5. Integrity without a graph database

Lance does not maintain referential integrity. **Policy + code** does.

### 5.1 Write path (synchronous)

```text
Source system export
    → map to node_type / edge payload
    → validate_node_payload / RelationEdge (schema + constraints)
    → check graph_id domain bundle
    → check endpoint nodes (intra-graph)
    → optional: resolve id in component master (cross-graph)
    → upsert Lance row
```

This matches [AGENTS.md](../AGENTS.md) §4: never hand-edit Lance files.

### 5.2 Component master (cross-graph anchor)

Use DuckDB (or equivalent) as **identity and scalar SSOT**:

```sql
-- conceptual
components (
  id PRIMARY KEY,
  name, material, cost,
  status,           -- active | obsolete
  canonical_id      -- alias resolution
)
```

| Graph | Uses master for |
|-------|-----------------|
| EBOM | Authoritative engineering attributes after PLM release |
| Sourcing | Verify `Component.id` exists before `SUPPLIED_BY` |
| Routing | Verify `Component.id` before `INPUT_OF` |
| Agent | Cost rollup, display names in federated reports |

Graphs may **duplicate** component properties in `properties_json` for read performance; master resolves **conflicts** and **aliases**.

### 5.3 Audit path (asynchronous)

Scheduled jobs (or `bom-validate` Skill playbook):

| Check | Action |
|-------|--------|
| Orphan edges | Edge endpoint missing in same `graph_id` |
| Cross-graph drift | `Component.id` in sourcing not in master |
| Domain leak | `USED_IN` row under `graph_id=sourcing` |
| Stale federation | ebom `as_of` ≫ sourcing `as_of` during incident |
| Agent evidence | Sample traversal produces empty join |

Report violations; **do not** auto-delete in production without owner approval.

### 5.4 Update semantics

| Operation | Pattern |
|-----------|---------|
| Node upsert | Delete-by-id + add (current `add_node`) |
| Edge upsert | Delete matching key + add (current `add_edge`) |
| Soft delete | `status: obsolete` in properties + audit flag |
| Revision | New `Product.version`; keep old nodes for `as_of` queries |

Lance’s lack of transactions across tables means **idempotent upserts** per row are preferred over multi-table ACID expectations.

---

## 6. Ontology for logical graph federation (agent)

Physical graphs stay separate. The ontology supplies **join rules** the agent and federation layer use.

### 6.1 Federation contract (minimum)

```yaml
federation:
  bridge_entities:
    - type: Component
      key: id
      graphs: [ebom, routing, sourcing]
    - type: Product
      key: id
      graphs: [ebom, routing]
  join_rules:
    - name: supplier_to_products
      steps:
        - graph: sourcing
          traverse: SUPPLIED_BY
          direction: reverse  # Supplier -> Component
          output: component_id
        - graph: ebom
          traverse: USED_IN
          from: component_id
          output: product_id
```

This can live in YAML/JSON beside Skills; execution remains **deterministic Python**, not LLM traversal.

### 6.2 What agents read from ontology

| Agent phase | Ontology use |
|-------------|--------------|
| **Plan** | Domain bundles → tool list; event type → playbook |
| **Execute** | Edge glossary → no illegal direction in custom prompts |
| **Federate** | Bridge keys → merge tool outputs on `component_id` |
| **Explain** | Type definitions → user-facing labels |
| **Audit** | `source_system`, `as_of` in evidence metadata |

The LLM should **not** parse Lance tables directly. It calls tools whose implementations honor `ALLOWED_EDGES` and `graph_id`.

### 6.3 Anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| Put all rules only in LLM system prompt | Drift from `schema.py`; untestable |
| Encode semantics only in Lance column names | Breaks schema-light flexibility |
| Merge three graphs into one Lance path on alert | Ownership blur; stale data |
| Full OWL ontology before first playbook | Slow delivery; agents need glossary + keys, not inference |
| Skip cross-graph master | Silent join failures on ID mismatch |

---

## 7. Proposed ontology package layout

Single authoring SSOT, multiple **views** for teams and agents:

```text
ontology/schema.py                 # Layer 1: schema + constraints (code)
scripts/sync_ontology.py
skills/bom-ontology/
  assets/ontology.json              # Layer 1 export (JSON Schema)
  assets/domain-bundles.json        # Layer 1: ebom | routing | sourcing subsets
  assets/federation.yaml            # Layer 2: joins, bridge keys
  assets/semantics.md               # Layer 2: edge glossary, definitions
  SKILL.md
```

| File | Layer | Consumers |
|------|-------|-----------|
| `schema.py` | 1 | Python ingest, tests, stores |
| `ontology.json` | 1 | Agents, external validators |
| `domain-bundles.json` | 1 | Per-team write policies |
| `federation.yaml` | 2 | Federation composer, playbooks |
| `semantics.md` | 2 | Humans, LLM Skills, auditors |

`domain-bundles.json` and `federation.yaml` are **proposed** extensions; only `ontology.json` exists today.

### 7.1 Example `domain-bundles.json` (illustrative)

```json
{
  "ebom": {
    "graph_id": "ebom",
    "owner": "engineering",
    "nodes": ["Component", "Product"],
    "edges": {
      "USED_IN": { "from": "Component", "to": "Product" }
    }
  },
  "sourcing": {
    "graph_id": "sourcing",
    "owner": "procurement",
    "nodes": ["Component", "Supplier"],
    "edges": {
      "SUPPLIED_BY": { "from": "Component", "to": "Supplier" }
    }
  }
}
```

### 7.2 Example semantics entry (illustrative)

```markdown
### SUPPLIED_BY
- **Domain:** sourcing
- **Direction:** Component (source) → Supplier (target)
- **Meaning:** The supplier at `target` is a qualified source for the component at `source`.
- **Traversal for impact:** Start at Supplier, walk incoming edges to Components.
- **Not:** Bill-of-material parent/child (see USED_IN in ebom).
```

---

## 8. Responsibility matrix

| Concern | LanceDB | schema.py | DuckDB master | Skills / federation |
|---------|---------|-----------|---------------|---------------------|
| Store rows | ✓ | | | |
| Property shapes | | ✓ | partial | |
| Edge typing rules | | ✓ | | |
| Endpoint exists (in-graph) | | ✓ (code) | | |
| Cross-graph ID exists | | | ✓ | ✓ |
| Business definitions | | descriptions | | ✓ |
| Agent join order | | | | ✓ |
| Vector embeddings | ✓ table | policy doc | | |

---

## 9. Summary

| Question | Answer |
|----------|--------|
| Is Lance schemaless? | **Mostly schema-light:** thin fixed columns + free-form `properties_json`. |
| Where is the real schema? | **Application layer:** `ontology/schema.py` + write validators. |
| What is a useful ontology? | **Schema + constraints + semantics + federation**, not Lance DDL. |
| Who enforces integrity? | **Ingest code** (sync), **master registry** (cross-graph), **audit jobs** (async). |
| How do agents integrate logically? | **Bridge keys** and **playbooks** from Layer 2; tools read separate Lance paths. |

Lance is the **disk format**. The ontology is the **contract** that keeps three team-owned graphs compatible enough for crisis-time federation in seconds.

---

## Related documentation

| Document | Contents |
|----------|----------|
| [enterprise-graph-design.md](enterprise-graph-design.md) | Three domains, Lance layout phases |
| [supply-chain-disruption-response.md](supply-chain-disruption-response.md) | Playbooks using federation |
| [development.md](development.md) | `schema.py` ↔ `ontology.json` workflow |
| [AGENTS.md](../AGENTS.md) | SSOT and seeding rules |
