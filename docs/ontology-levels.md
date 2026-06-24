# Ontology utilization levels

Index for **ontology** in knowledge graphs: classical/modern definitions (L0–L5), external references, GraphRAG grounding, and **this repository’s** implementation status.

**Audience:** architects, data platform owners, ontology authors, coding agents.

---

## Documents

| Doc | Contents |
|-----|----------|
| **[ontology-levels-general.md](ontology-levels-general.md)** | Part I — two roles (validation + reasoning), classical vs modern, L0–L5, external links, **GraphRAG grounding (§6)** |
| **[ontology-levels-project.md](ontology-levels-project.md)** | Part II — narrow ontology in this repo, what is implemented, agent grounding vs GraphRAG |

**Related:** [terminology.md](terminology.md) · [graph-contract.md](graph-contract.md) · [graph-context.md](graph-context.md) · [seeding.md](seeding.md) · [ontology/README.md](../ontology/README.md)

---

## Quick reference — two classical roles

| Role | Question |
|------|----------|
| **Semantic validation** | Does the graph conform to the ontology? (L0–L3) |
| **Reasoning** | What can be inferred from ontology semantics? (L5) |

Modern stacks often add **grounding (G\*)**: are **answers** faithful to graph/retrieval? — adjacent to ontology, not a substitute for L3. See [general §6](ontology-levels-general.md#6-graphrag-grounding--verification-and-ontology-levels).

---

## Quick reference — L0–L5 in this repo

| Level | Status |
|-------|--------|
| **L0** Vocabulary | **Done** |
| **L1** Payload schema | **Done** |
| **L2** Structural + domain scope | **Done** (write paths) |
| **L3** Post-load conformance | **Not started** |
| **L4** Graph Contract | **Partial** |
| **L5** Reasoning (OWL) | **Out of scope** |
| **G\*** Agent/tool grounding | **Partial** ([project §7](ontology-levels-project.md#7-agent-grounding-vs-graphrag)) |

Details: [ontology-levels-project.md](ontology-levels-project.md).

---

## Where to start

| You want to… | Read |
|--------------|------|
| Understand ontology in general KG practice | [ontology-levels-general.md §1–§4](ontology-levels-general.md) |
| See W3C / Neo4j / GraphRAG citations | [ontology-levels-general.md §5](ontology-levels-general.md#5-external-references-classical-and-modern) |
| Verify GraphRAG answer grounding | [ontology-levels-general.md §6](ontology-levels-general.md#6-graphrag-grounding--verification-and-ontology-levels) |
| Know what this repo implements | [ontology-levels-project.md](ontology-levels-project.md) |
| Verify BOM agent demo output | [demo-runbook.md §D](demo-runbook.md#part-d--verification--evaluation) |
