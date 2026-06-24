# Ontology utilization — general knowledge graphs

Classical and modern definitions of ontology, the L0–L5 ladder, external references, and **GraphRAG grounding** (how it relates — and does not fully replace — ontology).

**Audience:** architects, data platform owners, ontology authors.

**See also:** [ontology-levels.md](ontology-levels.md) (index) · [ontology-levels-project.md](ontology-levels-project.md) (this repository) · [terminology.md](terminology.md)

---

## 1. The two roles of ontology (classical view)

In the **classical** knowledge-graph formulation, ontology serves two related purposes on top of a **knowledge representation** (triples, property graph, etc.):

| Role | Question | What “success” looks like |
|------|----------|---------------------------|
| **1. Semantic validation** | Does the graph **conform** to what the ontology allows? | Every instance respects types, properties, and relation patterns |
| **2. Reasoning** | What can be **inferred** from that representation using ontology semantics? | Implicit types, edges, or constraints are derived without being stored explicitly |

```text
  Ontology (rules)              Knowledge representation          Consumers
  ───────────────              ────────────────────────          ─────────
  L0–L2: what may exist   →    nodes & edges in Neo4j/RDF  →    queries, apps, agents
  L3: does it conform?    ────────────┬──────────────────
  L5: what is entailed?   ────────────┘
```

**Semantic validation** splits into:

- **Definition** (L0–L2): what patterns are allowed when authoring or ingesting
- **Conformance** (L3): whether the **loaded** graph still matches those rules

Authoring an ontology does **not** imply conformance — validation must run at ingest and/or after load. See [SHACL](https://www.w3.org/TR/shacl/) and [Neosemantics SHACL validation](https://neo4j.com/labs/neosemantics/5.14/validation/).

**Reasoning** (L5): OWL knowledge can **verify consistency** and **make implicit knowledge explicit** — [OWL — W3C](https://www.w3.org/OWL/), [OWL 2 Overview](https://www.w3.org/TR/owl-overview/).

This two-role model remains a valid **architecture vocabulary** for modern systems; implementation differs (§2).

---

## 2. Classical vs modern knowledge graphs

| Dimension | Classical formulation | Modern operational KGs (typical) |
|-----------|----------------------|----------------------------------|
| **Representation** | RDF triples, URIs | Property graphs (Neo4j), sometimes RDF alongside |
| **Ontology language** | RDFS, OWL, SHACL | JSON Schema, Pydantic; optional SHACL on LPG |
| **Semantic validation** | SHACL + SPARQL | Application validators on write; partial post-load audits |
| **Reasoning** | OWL DL reasoners | Traversal, joins, **LLM + tools**, heuristics |
| **Open vs closed world** | Open-world common | Closed-world at ingest common |
| **Scope** | Single logical graph | Federated graphs, vector + graph (GraphRAG) |
| **Who consumes ontology** | Reasoner, SPARQL | Pipelines, APIs, **agents**, BI |

**Modern “inference”** often means deterministic graph algorithms and federated joins, not OWL materialization.

A **third concern** in agent stacks: **operational context** (which graph, which tools, which Cypher) — consumption layer, not classical ontology. LLM-extracted graphs use **prompt-defined** types — [GraphRAG dataflow](https://microsoft.github.io/graphrag/index/default_dataflow/).

Further reading: [§5 External references](#5-external-references-classical-and-modern).

---

## 3. Neighboring concerns

| Concern | Primary question | Typical stack |
|---------|------------------|---------------|
| **Ontology / schema** | What types and relation patterns are allowed? | RDFS/OWL, SHACL, Pydantic |
| **Taxonomy** | Named categories and synonyms? | SKOS |
| **Instance data** | What entities and edges exist? | Neo4j, triple stores |
| **Data contract** | What does one producer guarantee? | [datacontract.com](https://datacontract.com/) |
| **Federation contract** | How may separate graphs be joined? | Bridge keys, joins (**L4**) |
| **Grounding / faithfulness** | Are **answers** supported by retrieved graph/text? | RAG eval, citations — **§6** |

Linked Data mapping:

| Layer | Standard | Two-role model |
|-------|----------|----------------|
| Vocabulary | [RDF Schema](https://www.w3.org/TR/rdf-schema/) | L0 |
| Constraints | [OWL 2](https://www.w3.org/TR/owl-overview/) | L2–L5 |
| Instance shapes | [SHACL](https://www.w3.org/TR/shacl/) | L3 validation |
| Reasoning | [OWL](https://www.w3.org/OWL/) / [RDF Semantics](https://www.w3.org/TR/rdf11-semantics/) | L5 |

OWL = inference (open-world); SHACL = integrity on a concrete graph (often closed-world). See [Reconciling SHACL and Ontologies (PDF)](https://noukoudshoorn.github.io/files/Reconciling_SHACL_and_Ontologies_Semantics_and_Val.pdf).

Property graphs: [GRAPH TYPE](https://neo4j.com/docs/cypher-manual/25/schema/graph-types/set-graph-types/), [Neosemantics SHACL](https://neo4j.com/labs/neosemantics/5.14/validation/), or app validators — often without full OWL.

---

## 4. Utilization levels (L0–L5)

| Levels | Classical role |
|--------|------------------|
| L0–L2 | **Semantic validation** — define what may be represented |
| L3 | **Semantic validation** — prove loaded data conforms |
| L4 | **Federation agreement** (modern; outside narrow ontology) |
| L5 | **Reasoning** — infer implicit facts |

```text
  L0  Vocabulary                    ─┐
  L1  Record / payload schema        ├─ semantic validation (define)
  L2  Structural graph constraints  ─┘
       │
  L3  Instance conformance (post-load)
       │
  L4  Multi-graph agreement
       │
  L5  Reasoning / rich semantics
```

### L0 — Vocabulary

Entity and relation **names** (`Component`, `SUPPLIED_BY`). Artifacts: glossaries, SKOS, enums.

### L1 — Record / payload schema

Well-typed properties, required fields. Artifacts: JSON Schema, Pydantic. Validates on **write**.

### L2 — Structural graph constraints

Legal **(source, relationship, target)** patterns and per-domain scope. Type-level, not full-instance cardinality.

### L3 — Instance conformance

Does the **stored graph** match ontology/shapes? Orphan edges, endpoints, cardinality, `graph_id`. SHACL, Cypher audits, **after load**.

### L4 — Multi-graph agreement

Bridge keys, join paths, SLA. Data/graph contracts when graphs stay separate.

### L5 — Reasoning

Subclass inheritance, entailment, materialization. OWL reasoners.

### Validation timing

| When | Levels |
|------|--------|
| Schema authoring | L0–L2 |
| Ingest / API write | L1–L2 |
| Post-load audit | L3 |
| Federated join | L4 (+ L3 per graph) |
| Reasoner | L5 |

---

## 5. External references (classical and modern)

### 5.1 Classical — semantic validation and reasoning

| Topic | Source |
|-------|--------|
| OWL + reasoning | [W3C OWL](https://www.w3.org/OWL/) |
| OWL 2 overview | [OWL 2 Overview](https://www.w3.org/TR/owl-overview/) |
| RDF semantics | [RDF 1.1 Semantics](https://www.w3.org/TR/rdf11-semantics/) |
| RDFS vocabulary | [RDF Schema](https://www.w3.org/TR/rdf-schema/) |
| SHACL validation | [SHACL](https://www.w3.org/TR/shacl/) |
| SHACL vs OWL | [Reconciling SHACL and Ontologies (PDF)](https://noukoudshoorn.github.io/files/Reconciling_SHACL_and_Ontologies_Semantics_and_Val.pdf) |
| SKOS | [SKOS Reference](https://www.w3.org/TR/skos-reference/) |

### 5.2 Modern — property graphs, contracts, agents

| Topic | Source |
|-------|--------|
| Neo4j + SHACL | [Neosemantics validation](https://neo4j.com/labs/neosemantics/5.14/validation/) |
| GRAPH TYPE | [Cypher Manual — GRAPH TYPE](https://neo4j.com/docs/cypher-manual/25/schema/graph-types/set-graph-types/) |
| GRAPH TYPE vs SHACL | [Neo4j Blog — GRAPH TYPE](https://neo4j.com/blog/developer/graph-type-schema-enforcement-made-easy-preview/) |
| LPG vs RDF | [Property Graphs vs RDF](https://bryon.io/property-graphs-vs-rdf-whats-the-real-difference-37a81a9f98a3) |
| JSON Schema | [json-schema.org](https://json-schema.org/) |
| Data Contract | [datacontract.com](https://datacontract.com/) |
| GraphRAG indexing | [GraphRAG dataflow](https://microsoft.github.io/graphrag/index/default_dataflow/) |
| GraphRAG prompts | [GraphRAG custom prompts](https://microsoft.github.io/graphrag/prompt_tuning/custom_prompts/) |

### 5.3 L0–L5 vs references

| Level | Classical | Modern |
|-------|-----------|--------|
| L0 | SKOS, RDFS | Glossaries, GraphRAG `entity_types` |
| L1 | RDFS datatypes | JSON Schema, Pydantic, GRAPH TYPE |
| L2 | domain/range, OWL | Allowed-edge tables, GRAPH TYPE endpoints |
| L3 | SHACL | Neosemantics, Cypher audits |
| L4 | (often external) | Data Contract, graph federation |
| L5 | OWL reasoners | Often traversal + tools + LLM search |

---

## 6. GraphRAG grounding — verification and ontology levels

### 6.1 What “grounding” means in GraphRAG

[GraphRAG](https://microsoft.github.io/graphrag/index/default_dataflow/) builds a graph from text (entities, relationships, communities), then **retrieves** subgraph summaries for LLM answers. **Grounding** asks: is the **generated answer** supported by the **retrieved graph and source text**?

This is **not** the same question as classical ontology **reasoning** (L5). It is closer to **RAG faithfulness** or **epistemic validation**: claims ↔ evidence.

### 6.2 Is grounding part of ontology utilization?

**Partially — map to different layers:**

| Concern | Ontology level? | Notes |
|---------|-----------------|-------|
| `entity_types` in extraction config | **L0–L1 (soft)** | Prompt-defined vocabulary, not OWL SSOT |
| Extracted entities/edges match a target schema | **L1–L3** | If you validate the **indexed graph** against Pydantic/SHACL |
| Community reports / retrieval match source docs | **Not L0–L5** | **Provenance / extraction quality** |
| LLM answer supported by retrieved context | **Not L0–L5** | **Grounding / faithfulness** (consumption layer) |

**Recommendation:** treat **GraphRAG grounding verification** as **adjacent to ontology**, not a replacement for L3:

```text
  L0–L2  ontology defines allowed knowledge representation
  L3     graph instance conforms to ontology
  G*     answers / summaries are faithful to retrieved graph + sources  ← GraphRAG grounding
```

Use **G\*** (grounding) in prose when you need a label; it is **not** added to L0–L5 as L6 in this repo unless you standardize it team-wide.

**Contrast with this project:** the BOM agent uses **deterministic tools** over a validated Neo4j graph (`bom_supplier_impact`, etc.) and returns `evidence` pointers — grounding is **tool-output faithfulness**, not GraphRAG community retrieval. See [ontology-levels-project.md §7](ontology-levels-project.md#7-agent-grounding-vs-graphrag).

### 6.3 How to verify GraphRAG grounding (practical)

| Method | What it checks | Ontology link |
|--------|----------------|---------------|
| **Citation / pointer audit** | Each claim links to entity IDs, community report IDs, or source `text_unit` | G*; optional L3 if IDs must exist in graph |
| **Human rubric** | Experts score supported / unsupported / contradicted per claim | G* |
| **LLM-as-judge** | Judge model compares answer to retrieved context only (closed book) | G* |
| **Extraction precision/recall** | Sample documents; compare extracted entities/edges to gold or manual labels | **L0–L2** on extraction output |
| **Schema validation on indexed graph** | Run SHACL or Pydantic on `entities.parquet` / Neo4j projection | **L3** on GraphRAG index artifacts |
| **Retrieval hit rate** | For benchmark questions, correct community/entities retrieved? | G* (retrieval), not ontology |
| **Entailment / NLI metrics** | NLI model: answer entailed by context? | G* |
| **Regression suite** | Fixed prompts + frozen index; diff answers and citations over time | G* + optional L3 |

**Minimum viable pipeline:**

1. **Index time:** validate extracted graph against domain schema (**L1–L3** if you have a SSOT).
2. **Query time:** require structured output with `citations[]` → `entity_id` / `text_unit_id`.
3. **Eval time:** automated judge + periodic human audit on a **golden question set**.

GraphRAG does not ship a single “grounding score”; you compose metrics from RAG evaluation practice (faithfulness, context precision) plus optional **L3** audits on the indexed graph.

### 6.4 When ontology investment pays off for GraphRAG

| If you need… | Invest in… |
|--------------|------------|
| Consistent entity types across index runs | **L0–L1** SSOT (+ sync to extraction prompts) |
| No illegal relationship patterns in the index | **L2–L3** on extracted graph |
| Answers that match enterprise BOM/supplier IDs | **L4** bridge keys + validated graph (prefer curated graph over pure LLM extraction) |
| “Did the model hallucinate?” | **G\*** faithfulness eval, not OWL reasoning |

For **manufacturing BOM** scenarios, a **curated ontology-validated graph** (this repo) plus **tool-grounded agents** often beats pure GraphRAG extraction for **factual supply-chain impact** — GraphRAG is stronger for **unstructured corpus** exploration.

---

## Related

| Topic | Doc |
|-------|-----|
| Index | [ontology-levels.md](ontology-levels.md) |
| This repository | [ontology-levels-project.md](ontology-levels-project.md) |
| Naming | [terminology.md](terminology.md) |
