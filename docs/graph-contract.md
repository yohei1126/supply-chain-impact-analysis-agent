# Graph Contract

A **Graph Contract** is the cross-domain agreement that lets physically separate graphs be **split for ownership**, **joined on demand**, and **federated into a logical unified view** without merging databases. It plays a role analogous to a [data contract](https://datacontract.com/) (schema, SLAs, quality rules for one dataset), but for **multi-graph federation** in manufacturing supply chains.

Within the Graph Contract, **Bridge Keys** (shared IDs such as `Component.id`) are the federation handshake. The contract as a whole is the machine-readable manifest — identity bindings, domain scopes, federation joins, and quality gates — that ingest pipelines and the agent runtime must honor.

**Audience:** data platform owners, ontology authors, pipeline engineers.

**Related:** [terminology.md](terminology.md) · [seeding.md](seeding.md) · [graph-context.md](graph-context.md) · [enterprise-graph-design.md](enterprise-graph-design.md) (three domains) · [supply-chain-disruption-response.md](supply-chain-disruption-response.md) (agent playbooks) · [development.md](development.md) (implementation phases).

> **Terminology** (Graph Contract vs graph context vs `graph_view`): [terminology.md](terminology.md).

---

## 1. Why Graph Contract and not only ontology

| Concept | Primary question | Scope |
|---------|------------------|-------|
| **Ontology** | What node/edge types exist and what do they mean? | Single knowledge domain |
| **Data contract** | What does this table/dataset guarantee? | One producer → one consumer |
| **Graph Contract** | Under what rules may separate graphs be **logically integrated**? | Many producers → federation + agent |

Ontology alone does not specify:

- Which `graph_id` a team may write
- Which entity IDs must align across graphs (Bridge Keys)
- Which join paths are valid for impact analysis
- Freshness (`as_of`) expectations when composing answers
- How an agent may traverse across domains (tool order, edge allow-list)

The Graph Contract **bundles** ontology slices, identity bindings, domain scopes, federation joins, and operational metadata into one **versioned contract** consumed by ingest pipelines and the agent runtime.

---

## 2. Definition

> **Graph Contract** — A versioned specification that defines how independent domain graphs remain compatible for dynamic logical federation.

### 2.1 Four contract elements

Aligned with the logical-federation design (Bridge Keys + cross-domain joins):

| Element | Purpose | Example |
|---------|---------|---------|
| **Identity bindings** | Bridge Keys and aliases | `Component.id` global; `canonical_id` in master |
| **Domain scopes** | Partitioning and write scope | `graph_id: sourcing`; nodes/edges allowed |
| **Federation joins** | Legal cross-graph join paths and playbooks | `supplier_disruption`: sourcing → ebom → routing |
| **Quality gates** | SLA, `as_of`, ingest and federate checks | Sourcing refreshed daily; warn if skew > 48h |

Schema shapes and edge semantics come from **`ontology/schema.py`** (referenced by the contract, not duplicated). Federation is only sound when **identity bindings + domain scopes + semantics** are satisfied. **Quality gates** warn consumers when graphs are stale relative to each other.

### 2.2 What it is not

- Not a physical merge of graph databases
- Not a replacement for PLM/MES/SRM as systems of record
- Not LLM prompt text alone (must be machine-validated where possible)
- Not a duplicate of `ontology.json` — it **references** generated schema and adds cross-graph rules

---

## 3. Relationship to existing artifacts

```text
ontology/schema.py
        │  generates
        ▼
ontology.json ──────────────┐
        │                   │
        ▼                   ▼
domain-bundles (per graph_id)     graph_contract.yaml (Graph Contract SSOT)
        │                   │
        │                   ├── sync ──► graph-context.json (graph context for agents)
        │                   │
        └─────────┬─────────┘
                  ▼
        GraphContract loader (YAML)     GraphContext bundle (JSON, read-only)
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
   Ingest      Audit       Agent + Federation
   pipelines   jobs        composer
```

| Artifact | In Graph Contract? | In graph context (`graph-context.json`)? |
|----------|-------------------|------------------------------------------|
| `ComponentNode` JSON Schema | Referenced (`schema.$ref`) | Via `ontology.json` ref, not duplicated |
| `ALLOWED_EDGES` per domain | Yes (`domains[].edges`) | Yes (`domains`) |
| `Component.id` as Bridge Key | Yes (`identity.bridges`) | Yes (`federation.bridges`) |
| Join path sourcing → ebom | Yes (`federation.joins`) | Yes (`federation.recipes`) |
| Hormuz gazetteer | No — disruption Skill | No |
| Neo4j DDL / indexes | No | No |

---

## 4. Graph Contract document (authoring format)

Single file or split bundle under `skills/bom-ontology/assets/` (proposed). Human-edited federation and ops; schema sections generated from `schema.py`.

### 4.1 Illustrative `graph_contract.yaml`

```yaml
version: "1.0.0"
meta:
  name: manufacturing-supply-chain
  owner: data-governance@example.com

identity:
  master_entity: Component
  master_key: id
  bridges:
    - entity: Component
      key: id
      graphs: [ebom, routing, sourcing]
      rule: same_id_same_real_world_part
    - entity: Product
      key: id
      graphs: [ebom, routing]
      rule: same_id_same_finished_good

domains:
  ebom:
    graph_id: ebom
    owner_team: engineering
    sla_hours: 24
    nodes: [Component, Product]
    edges:
      USED_IN: { from: Component, to: Product, traverse_out: [Product] }

  routing:
    graph_id: routing
    owner_team: manufacturing
    sla_hours: 24
    nodes: [Component, Process, Product]
    edges:
      INPUT_OF: { from: Component, to: Process }
      PRODUCED_BY: { from: Product, to: Process }

  sourcing:
    graph_id: sourcing
    owner_team: procurement
    sla_hours: 24
    nodes: [Component, Supplier]
    edges:
      SUPPLIED_BY:
        from: Component
        to: Supplier
        traverse_in_from: [Supplier]   # impact analysis starts at supplier

federation:
  joins:
    - name: supplier_to_products
      steps:
        - domain: sourcing
          edge: SUPPLIED_BY
          direction: reverse
          yields: component_id
        - domain: ebom
          edge: USED_IN
          from: component_id
          yields: product_id

quality:
  on_ingest:
    - intra_graph_endpoints_exist
    - domain_edge_allowed
    - bridge_id_present_in_master
  on_federate:
    - warn_if_as_of_skew_hours: 48
    - reject_join_if_master_missing: true
```

Agent **playbooks** (tool sequences) are runtime concerns and live in `app/federation/playbooks.yaml`, not in the Graph Contract YAML file.

```yaml
# app/federation/playbooks.yaml (excerpt)
playbooks:
  maritime_chokepoint:
    entry_domain: sourcing
    tool_sequence:
      - sourcing.suppliers_by_countries
      - sourcing.components_by_suppliers
      - ebom.products_by_components
      - routing.processes_by_components
```

The demo binds `master_entity` / `master_key` to DuckDB at `app/component_master_store.py`; that binding is not part of `ontology/`.

### 4.2 Versioning and compatibility

- **Semver** on `ontology/contract/graph_contract.yaml` (federation/join changes = minor or major).
- Ingest and agent log contract version in Langfuse / row metadata (`graph_contract_version`; legacy field name `graph_context_version`).
- Breaking Bridge Key change = major bump + migration plan for IDs.

---

## 5. Implementation in this repository

### 5.1 Authoring SSOT (no drift)

| Part | Source | Generated? |
|------|--------|------------|
| Node/edge shapes | `ontology/schema.py` | — |
| `ontology.json` | `scripts/sync_ontology.py` | Yes |
| Domain allow-lists | `domains/registry.py`, `domains/*/bundle.py` | No |
| Federation joins | `ontology/contract/graph_contract.yaml` | No (hand-authored) |
| Agent playbooks | `app/federation/playbooks.yaml` | No (runtime) |
| Semantics glossary | `skills/bom-ontology/references/semantics.md` | No |

Extend `sync_ontology.py` to emit `domain-bundles.json` and validate `graph_contract.yaml` edge names against `ALLOWED_EDGES`.

### 5.2 Runtime loaders

**Graph Contract (YAML)** — proposed loader for `ontology/contract/graph_contract.yaml`:

```python
# Responsibilities (conceptual)
class GraphContract:
    version: str
    domains: dict[str, DomainBundle]
    bridges: list[BridgeRule]
    joins: dict[str, FederationJoin]

    def validate_edge(self, graph_id: str, edge: RelationEdge) -> None: ...
    def validate_bridge(self, entity: str, entity_id: str, master) -> None: ...
    def join_plan(self, name: str) -> list[FederationStep]: ...
    def playbook_tools(self, name: str) -> list[str]: ...
```

Loaded once at agent startup and ingest job start; immutable for the duration of a run.

Agent consumption of the derived JSON bundle: [graph-context.md](graph-context.md).

### 5.3 Federation composer

`app/federation/composer.py` (planned, [development.md](development.md) P4):

1. Accept tool results + active Graph Contract version.
2. Execute join steps from `federation.joins` (deterministic ID merges).
3. Build `graph_view` for UI.
4. Attach `domain_snapshots.as_of` from each store.
5. Apply `quality.on_federate` rules (warnings in response).

**No fourth physical graph** — the “logical unified graph” is an **in-memory view** (or ephemeral JSON) for one request.

### 5.4 Neo4j storage (unchanged philosophy)

The Graph Contract does not dictate storage layout. Optional metadata on graph nodes:

- `graph_id`, `as_of`, `source_system`, `graph_contract_version`

Domains are separated by `graph_id` within Neo4j (Community edition uses one database).

---

## 6. Pipeline usage

### 6.1 Domain ingest (write path)

```text
PLM export
  → load GraphContract for graph_id=ebom
  → validate_node_payload / RelationEdge (schema)
  → GraphContract.validate_edge (domain scope)
  → resolve Component.id against master (identity binding)
  → upsert Neo4j (graph_id=ebom)
  → record as_of, graph_contract_version
```

Each team pipeline **declares** its `graph_id` and refuses writes outside its domain bundle.

### 6.2 Cross-graph precondition (procurement example)

Before `SUPPLIED_BY` for `COMP-103`:

- `COMP-103` exists in component master (identity binding).
- Optionally: `COMP-103` exists in ebom graph (stricter policy).

Failure mode: **reject row** or quarantine table — not silent agent-side fix.

### 6.3 Audit pipeline (async)

Periodic job reads `quality.on_ingest` checks:

- Orphan edges per `graph_id`
- Bridge IDs in sourcing not in master
- Domain edge leakage (e.g. `USED_IN` under sourcing)

Output: violation report for data stewards (future `bom-validate` Skill format).

---

## 7. Agent usage (Graph Contract side)

Graph context loading for Skills and Cypher compose: [graph-context.md](graph-context.md).

### 7.1 Startup (contract enforcement)

1. Load Graph Contract rules (YAML / ingest hooks) for validation and federation joins.
2. Register tools scoped by domain (tool implementation reads correct `graph_id` via `GraphStore`).

### 7.2 Unstructured disruption (news)

| Step | Graph Contract role |
|------|---------------------|
| **Interpret** | LLM uses semantics glossary; no graph walk |
| **Plan** | Match disruption class → `app/federation/playbooks.yaml` tool_sequence |
| **Execute** | Each tool respects `domains[].edges` traverse rules |
| **Re-plan** | Widen only within allowed filters (countries, risk — sourcing schema) |
| **Federate** | `federation.joins` merges tool outputs on Bridge Keys |
| **Respond** | Include `graph_contract_version`, `as_of` skew warnings |

The agent **does not** construct a unified graph by prompting “connect all nodes.” It **instantiates** a logical view from the contract’s join definitions.

### 7.3 Evidence and audit

Langfuse trace fields (proposed):

```json
{
  "graph_contract_version": "1.0.0",
  "playbook": "maritime_chokepoint",
  "joins_used": ["supplier_to_products"],
  "bridge_keys": ["Component.id"],
  "as_of_skew_warning": false
}
```

User-facing evidence stays grounded in tool JSON; operators use Langfuse for contract version and join path.

### 7.4 Skills mapping

| Skill | Uses Graph Contract for |
|-------|-------------------------|
| `bom-ontology` | Schema, domain scopes, semantics |
| `bom-graph-explorer` | Contract enforced at sync (see [graph-context.md](graph-context.md)) |
| `bom-disruption-response` | Federation playbooks |
| `bom-validate` (optional) | Quality gates |

---

## 8. “Logical unified graph” as a maintained state

The unified graph is **not** a persistent database. It is a **capability**:

| State | Meaning |
|-------|---------|
| **Split** | Three domain graphs healthy; each honors its domain scope |
| **Integrable** | Graph Contract version current; Bridge Keys aligned |
| **Federated (ephemeral)** | One agent run produced a join snapshot for analysis |
| **Degraded** | `as_of` skew or missing Bridge IDs — federation warns or stops |

Maintaining integrability is **continuous Graph Contract compliance**, not a one-time ETL merge.

```text
         ┌─────────────────────────────────────┐
         │   Graph Contract (versioned SSOT)   │
         │  identity · domains · federation    │
         └─────────────────────────────────────┘
              ▲           ▲           ▲
         ingest       audit      agent run
              │           │           │
    ┌─────────┴───┐ ┌─────┴─────┐ ┌───┴──────────────┐
    │ ebom Neo4j  │ │ routing   │ │ sourcing Neo4j   │
    └─────────────┘ └───────────┘ └──────────────────┘
              │                       │
              └───────────┬───────────┘
                          ▼
              Logical view (per request only)
```

---

## 9. Comparison summary

| | Data contract | Ontology | Graph Contract |
|--|---------------|----------|----------------|
| Unit | Dataset / table | Types & relations | Domain graph + federation |
| Producers | One | One domain | Multiple teams |
| Consumer | Downstream app | Reasoners / validators | Pipelines + agent composer |
| Joins | FK in warehouse | Same-store inference | Cross-store Bridge Key rules |
| Runtime | Batch / stream check | Validation | Dynamic per-query federation |

**Verdict:** **Graph Contract** is the federation-facing agreement that sits above per-domain ontology and below the agent. It makes explicit what must stay true so logical unification is always available.

---

## 10. Implementation roadmap

| Phase | Graph Contract deliverable | See |
|-------|------------------------------|-----|
| P0 | Implicit contract in `schema.py` + docs | Now |
| P1 | `graph_contract.yaml` draft + playbook refs in `app/federation/playbooks.yaml` | [development.md](development.md) P1 |
| P2 | `GraphContract` loader (YAML) + ingest validation hooks | P2–P3 |
| P3 | Domain bundles generated from SSOT | P3 |
| P4 | Federation composer enforces `joins` | P4 |
| P5 | Per-connector `graph_contract_version` in ingest metadata | **Done** — `pipeline/connectors/registry.py`, `ConnectorIngestContext` |

---

## Related documentation

| Document | Contents |
|----------|----------|
| [terminology.md](terminology.md) | Naming SSOT |
| [ontology-levels.md](ontology-levels.md) | L0–L5 index; [ontology-levels-project.md](ontology-levels-project.md) for this repo |
| [seeding.md](seeding.md) | Ontology SSOT, seeding, validation on write |
| [graph-context.md](graph-context.md) | `graph-context.json` bundle, sync, agent/Skill consumption |
| [enterprise-graph-design.md](enterprise-graph-design.md) | Three domains, physical layout |
| [supply-chain-disruption-response.md](supply-chain-disruption-response.md) | News-driven playbooks |
| [development.md](development.md) | Phased build plan |
