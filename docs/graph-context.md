# Graph context

**Graph context** is the agent-facing **scope bundle** exported as `graph-context.json`. It tells explorers and LLM planners which `graph_id` owns which node/edge **types**, how Bridge Keys align, and which federation **recipe names** exist — without loading the full Graph Contract YAML or Neo4j instance data.

**Not instance graph data.** Rows like `SUP-002` or `COMP-101` live in Neo4j. Ephemeral subgraphs for the UI live in **`graph_view`**. Terminology: [terminology.md](terminology.md).

**Audience:** agent developers, Skill authors, anyone composing Cypher or debugging explorer prompts.

**Related:** [terminology.md](terminology.md) · [seeding.md](seeding.md) · [graph-contract.md](graph-contract.md) (Graph Contract SSOT) · [agent-skill-assets.md](agent-skill-assets.md) (catalog sync and versioning) · [skills/bom-graph-explorer/SKILL.md](../skills/bom-graph-explorer/SKILL.md) · [skills/bom-graph-explorer/references/cypher-compose.md](../skills/bom-graph-explorer/references/cypher-compose.md)

---

## 1. Role in the stack

```text
Graph Contract (YAML)     domains/registry.py + schema.py
         │                            │
         └──────── export ────────────┘
                      │
                      ▼
            graph-context.json  ──►  agent system prompt (bom-graph-explorer)
                      │
                      ▼
            Cypher compose / graph_id choice / traverse allow-list
                      │
                      ▼
            Neo4j (instance graph data)  ──►  graph_view (UI slice)
```

| Layer | Doc | File |
|-------|-----|------|
| **Graph Contract** (agreement) | [graph-contract.md](graph-contract.md) | `ontology/contract/graph_context.yaml` |
| **Graph context** (this doc) | here | `skills/bom-graph-explorer/assets/graph-context.json` |
| **Instance data** | [demo-runbook.md](demo-runbook.md), [seeding.md](seeding.md) | Neo4j + DuckDB |
| **UI subgraph** | [demo-runbook.md](demo-runbook.md#d3-ui-vs-langfuse) | `graph_view` in API responses |

---

## 2. What is in `graph-context.json`

Generated bundle format: `bom-graph-context-bundle` (see `meta.format` in the file).

| Section | Purpose | Graph instance data? |
|---------|---------|----------------------|
| `identity.bridges` | Bridge Keys (`Component.id`, `Product.id`) and which `graph_id`s share them | No — ID rules only |
| `domains.<graph_id>.nodes` | Allowed **node types** for that domain | No — type list |
| `domains.<graph_id>.edges` | Allowed **edge types** with `from` / `to` labels | No — schema-level |
| `federation.joins` | Named federation **recipes** (query step names + bridge field) | No — pipeline metadata |
| `meta` | Provenance, link to Graph Contract path | — |

Example (abbreviated):

```json
{
  "identity": { "bridges": [{ "entity": "Component", "key": "id", "graphs": ["ebom", "routing", "sourcing"] }] },
  "domains": {
    "sourcing": {
      "graph_id": "sourcing",
      "nodes": ["Component", "Supplier"],
      "edges": { "SUPPLIED_BY": { "from": "Component", "to": "Supplier" } }
    }
  },
  "federation": {
    "joins": [{ "name": "supplier_disruption_impact", "steps": ["components_by_supplier", "impact_products_by_components"], "bridge": "component_id" }]
  }
}
```

### What graph context omits (Graph Contract only)

These stay in the YAML contract or runtime code — not in the JSON bundle:

- `quality` gates, `sla_hours`, `owner_team`
- Full federation step definitions (domain, edge, direction, yields)
- Agent playbooks (`app/federation/playbooks.yaml`)

That keeps the explorer Skill prompt small while ingest/governance use the full Graph Contract.

---

## 3. Generation and sync

| Step | Command / module |
|------|------------------|
| Authoring inputs | `domains/registry.py`, `ontology/schema.py`, `FEDERATION_RECIPES` in `domains/export.py` |
| Export function | `export_graph_context_bundle()` in `domains/export.py` |
| Sync to Skill assets | `uv run python scripts/sync_ontology.py` |
| Output path | `skills/bom-graph-explorer/assets/graph-context.json` |

**Never hand-edit** `graph-context.json`. Drift is guarded by `tests/test_skill_agent_assets.py`.

After changing domain allow-lists or federation recipe names:

```bash
uv run python scripts/sync_ontology.py
uv run pytest -q tests/test_skill_agent_assets.py
```

If Bridge Keys or join **policy** change, update the **Graph Contract** YAML first ([graph-contract.md](graph-contract.md)), then extend `domains/export.py` if the JSON shape must expose new fields.

---

## 4. Runtime consumption

### BOM agent server

`app/agent/skills.py` embeds `graph-context.json` in the system prompt under a `## graph-context.json` heading when building the explorer Skill context.

### bom-graph-explorer Skill

| Consumer | Uses graph context for |
|----------|------------------------|
| [cypher-compose.md](../skills/bom-graph-explorer/references/cypher-compose.md) | Confirm edge type is allowed under target `graph_id` |
| [workflows.md](../skills/bom-graph-explorer/references/workflows.md) | Multi-hop edge allow-list per domain |
| [cypher-engine-profile.json](../skills/bom-graph-explorer/assets/cypher-engine-profile.json) | Composition rules referencing `graph-context.json` domains |

Typical compose flow:

1. Read goal → pick `graph_id` (`sourcing`, `ebom`, or `routing`).
2. Open `graph-context.json` → `domains.<graph_id>.edges`.
3. Prefer named queries from `query-catalog.json` (same sync pipeline).
4. Execute against Neo4j with `graph_id` filter — instance rows returned separately.

### Federation API / deterministic tools

Server-side federation (`app/federation/analysis.py`) reads **Neo4j** and the Graph Contract join logic in code — it does **not** parse `graph-context.json` at request time. The JSON bundle is primarily for **LLM + Skill** exploration paths.

---

## 5. When to use “graph context” in docs and code

See [terminology.md](terminology.md) for the full naming rules. Short version:

| Say **graph context** | Say **Graph Contract** instead |
|-----------------------|--------------------------------|
| `graph-context.json`, `export_graph_context_bundle()` | `graph_context.yaml`, ingest validation, quality gates |
| “Which edges exist under sourcing?” in a Skill prompt | “Who may write `USED_IN`?” or “SLA for ebom refresh” |
| Agent Cypher compose allow-list | Cross-team federation agreement changes |
| `test_graph_context_domains_match_registry` | `GraphContract.validate_edge` (planned) |

---

## 6. Related artifacts (same sync, different roles)

| File | Role |
|------|------|
| `graph-context.json` | Domain scope + bridges + federation recipe **names** |
| `query-catalog.json` | Named Cypher recipes (`components_by_supplier`, …) |
| `cypher-engine-profile.json` | Neo4j dialect and composition rules |
| `ontology.json` | Node/edge **shapes** (bom-ontology Skill) |

Catalog versioning and multi-agent deploy: [agent-skill-assets.md](agent-skill-assets.md).

---

## Related documentation

| Document | Contents |
|----------|----------|
| [terminology.md](terminology.md) | Naming SSOT |
| [graph-contract.md](graph-contract.md) | Graph Contract YAML, Bridge Keys, joins, quality, ingest |
| [agent-skill-assets.md](agent-skill-assets.md) | Sync pipeline, catalog versioning, all JSON artifacts |
| [development.md](development.md) | `domains/export.py` in authoring workflow |
