# Terminology

**SSOT for names** used across docs, code comments, and PRs.

**Audience:** all contributors, coding agents, doc authors.

**Related:** [graph-contract.md](graph-contract.md) (Graph Contract design) · [graph-context.md](graph-context.md) (`graph-context.json` usage) · [seeding.md](seeding.md) · [setup-and-demos.md](setup-and-demos.md)

---

## Quick rules

| If you are talking about… | Say | Do not say |
|---------------------------|-----|------------|
| Federation **agreement** (Bridge Keys, who owns which edge, join rules, quality gates, SLA) | **Graph Contract** | graph context, federation contract |
| Agent **prompt bundle** (domain scopes + bridges exported for Skills) | **graph context** | Graph Contract, contract file |
| **Instance data** in Neo4j (`SUP-002`, `COMP-101`, …) | **graph data** / **domain graph** | graph context |
| **UI/API subgraph** (`nodes[]`, `edges[]` for one run) | **`graph_view`** | graph context, Graph Contract |

**Contract** talk → **Graph Contract**. **Context** talk → **graph context**. Do not rename context artifacts to “contract,” and do not call the contract bundle “graph context” in prose.

---

## What each is (and is not)

| | **Graph Contract** | **graph context** | **`graph_view`** (related) |
|--|-------------------|-------------------|----------------------------|
| **Role** | Cross-team **agreement** and validation SSOT | **Runtime context** for agents composing Cypher / choosing `graph_id` | **Ephemeral subgraph** for one analysis |
| **Primary file** | `ontology/contract/graph_context.yaml` | `skills/bom-graph-explorer/assets/graph-context.json` | Built in memory; returned in API JSON |
| **Structure** | YAML manifest (identity, domains, joins, quality) | JSON bundle (`identity`, `domains`, `federation`) | `{ nodes[], edges[] }` — actual graph fragment |
| **Graph instance data?** | **No** — rules and scopes | **No** — type-level domain scopes; not Neo4j rows | **Yes** — supplier/component/product nodes and edges |
| **Typical consumers** | Ingest pipelines, audit jobs, governance | `bom-graph-explorer` Skill, agent system prompt | Web UI map, `/v1/agent/run` response |
| **Edited by** | Data governance / platform (hand-authored YAML) | Generated only (`domains/export.py` → `sync_ontology.py`) | Computed per request (`app/graph_viz.py`) |
| **Detail doc** | [graph-contract.md](graph-contract.md) | [graph-context.md](graph-context.md) | [demo-runbook.md](demo-runbook.md) |

Neither the Graph Contract nor `graph-context.json` is a graph in the database sense. Both describe **how graphs may be split, typed, and joined**. Only Neo4j rows and `graph_view` hold **instance-level** nodes and edges.

```text
  Graph Contract (YAML)          graph context (JSON)         graph data (Neo4j)
  ─ agreement & gates      ─►    ─ agent scope bundle    ─►   ─ SUP-002, COMP-101, …
        │                              │                           │
        └──────── sync / derive ───────┘                           │
                                                                   ▼
                                                            graph_view (UI slice)
```

---

## Naming map (concept vs files)

| Concept | Path |
|---------|------|
| **Terminology** (this doc) | `docs/terminology.md` |
| **Ontology** (global shapes) | `ontology/schema.py` → `ontology.json` |
| **Graph Contract** (authoring SSOT) | `ontology/contract/graph_context.yaml` |
| **graph context** (Skill export) | `skills/bom-graph-explorer/assets/graph-context.json` |
| Graph Contract design guide | `docs/graph-contract.md` |
| Graph context usage guide | `docs/graph-context.md` |
| Agent setup and seeding | `docs/seeding.md`, `docs/setup-and-demos.md` |

Historical filenames: YAML uses `graph_context`; JSON uses `graph-context`. **Concept names** follow Contract vs context above — filenames are not renamed.

---

## When to use which term

| Situation | Use | Example phrasing |
|-----------|-----|------------------|
| Changing Bridge Keys or federation join paths | **Graph Contract** | “Update the Graph Contract `federation.joins` for supplier disruption.” |
| Ingest rejecting a cross-domain edge | **Graph Contract** | “`GraphContract.validate_edge` failed — edge not in domain scope.” |
| Documenting owner team / SLA / quality gates | **Graph Contract** | “Sourcing `sla_hours` in the Graph Contract.” |
| Agent Skill loading domain allow-lists into the prompt | **graph context** | “Embed `graph-context.json` in the explorer Skill.” |
| Cypher compose: which edges exist under `sourcing` | **graph context** | “Check `graph-context.json` → `domains.sourcing.edges`.” |
| Code export function / test name | **graph context** (keep identifiers) | `export_graph_context_bundle()`, `test_graph_context_domains_match_registry` |
| Explaining federation to architects (Zenn / design) | **Graph Contract** | “Bridge Keys are part of the Graph Contract.” |
| API field with nodes and edges for the map | **`graph_view`** | “`graph_view.node_count` must be ≥ 1.” |
| Confusing contract with instance data | **Avoid** | ~~“Load the graph context into Neo4j.”~~ → “Seed Neo4j from the demo pipeline; agents read **graph context** for scope.” |

---

## Contents by layer (what lives where)

| Content | Graph Contract (YAML) | graph context (JSON) | Neo4j / `graph_view` |
|---------|:---------------------:|:--------------------:|:--------------------:|
| Bridge Keys (`Component.id`, …) | ✓ `identity.bridges` | ✓ `identity.bridges` | ✓ instance IDs |
| Allowed node/edge **types** per domain | ✓ `domains` | ✓ `domains` | ✓ typed nodes/edges |
| Federation join **definitions** | ✓ `federation.joins` (full steps) | ✓ `federation.joins` (recipe names) | — |
| Quality gates / SLA | ✓ `quality`, `sla_hours` | — | — |
| Owner team metadata | ✓ `owner_team` | — | — |
| Tool playbooks | — (see `playbooks.yaml`) | — | — |
| Supplier/product **rows** | — | — | ✓ |

---

## Related terms (do not conflate)

| Term | Meaning |
|------|---------|
| **Ontology** | Global node/edge **shapes** and validators (`ontology/schema.py`, `ontology.json`) |
| **Data contract** | Single-dataset guarantees ([datacontract.com](https://datacontract.com/) style) — analogous, not identical to Graph Contract |
| **Domain graph** | One `graph_id` slice of instance data in Neo4j (`sourcing`, `ebom`, `routing`) |
| **Bridge Key** | Shared ID field (e.g. `Component.id`) defined **in** the Graph Contract |
| **graph context** | Agent-facing **scope bundle** — [graph-context.md](graph-context.md) |
| **Graph Contract** | Cross-domain federation **agreement** — [graph-contract.md](graph-contract.md) |
