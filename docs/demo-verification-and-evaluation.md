# Demo verification and evaluation guide

How to **run each demo**, **confirm what happened**, and **evaluate pass/fail** — plus where to look in the UI versus Langfuse.

**Runbooks:** [local-demo-runbook.md](local-demo-runbook.md) (full stack) · [federation-demo-runbook.md](federation-demo-runbook.md) (graphs only, no LLM) · [observability.md](observability.md) (Langfuse setup)

---

## How to use this document

| You want to… | Start here |
|--------------|------------|
| Run the demo end-to-end | §1 Demo paths |
| Know ground truth (IDs, products, suppliers) | §2 Seed data reference |
| Walk through each UI scenario step-by-step | §3 Scenario playbooks |
| Score an agent run (good / partial / fail) | §4 Evaluation rubric |
| See which surface shows which detail | §5 Where to verify (UI vs Langfuse) |
| Automate smoke checks | §6 Automated checks |

---

## 1. Demo paths

Three entry points share the same synthetic BOM in [`pipeline/demo/sample_data.py`](../pipeline/demo/sample_data.py).

| Path | Command / URL | Proves | Langfuse |
|------|---------------|--------|----------|
| **A. Federation CLI** | `uv run python scripts/demo_federation.py --reset` | Per-domain load, join on `Component.id`, problems/mitigations | No |
| **B. Web UI (graphs)** | `uv run python -m app.agent` → **Domain query** / **Federation** tabs | Cypher + tables + federated map in browser | No |
| **C. Web UI (agent)** | Same server → **Agent (LLM)** tab (+ optional LiteLLM) | Natural-language goals → planner → tools → user summary | Yes (`bom-agent-run`) |

**Recommended first-time flow:** seed data → **B** (confirm graphs) → **C** (confirm agent) → Langfuse for **C** only.

```bash
# Shared seed for B and C
uv run python scripts/seed_complex_bom.py --reset
uv run python -m app.agent
# → http://127.0.0.1:8080/ui/
```

For path **A** without the agent server, see [federation-demo-runbook.md](federation-demo-runbook.md).

---

## 2. Seed data reference (ground truth)

Use this table when judging whether demo output is **correct**, not hallucinated.

### Suppliers

| ID | Name | Country | Risk | Demo role |
|----|------|---------|------|-----------|
| `SUP-001` | Nihon Steel | JP | High | Default federation CLI scenario; steel-heavy supply |
| `SUP-002` | Euro Brass GmbH | DE | Medium | **German brass** agent example |
| `SUP-003` | Pacific Plastics | US | Low | Mitigation / alternate sourcing stories |

### Products

| ID | Name |
|----|------|
| `PROD-900` | Industrial Pump |
| `PROD-901` | Servo Motor Drive |
| `PROD-902` | Valve Manifold |

### Components by supplier (sourcing domain)

| Supplier | Component IDs | Notes |
|----------|---------------|-------|
| `SUP-001` | COMP-100, 102, 103, 104, 105 | Includes **Drive Shaft** (`COMP-103`) |
| `SUP-002` | COMP-101, 106, 108, 110, 111 | All brass-related; **Valve** = `COMP-101` |
| `SUP-003` | COMP-107, 109 | |

### Key cross-links for agent examples

| Scenario clue | Resolves to | Tool (expected) |
|---------------|-------------|-----------------|
| Germany + brass + supplier disruption | `SUP-002` | `bom_supplier_impact` |
| Drive shaft + Servo Motor Drive | `COMP-103` → `PROD-901` | `bom_supply_path` |
| Brass valve shortage / similar parts | vector hits on brass valve-like rows | `bom_hybrid_query` |
| Explicit `SUP-001` in goal text | `SUP-001` | `bom_supplier_impact` |

Bridge key for federation: **`Component.id`** (same part number in sourcing, ebom, routing).

---

## 3. Scenario playbooks

Each playbook: **action → confirm → evaluate**.

### 3.1 Federation — `SUP-002` (Euro Brass)

**Where:** **Federation** tab (or `POST /v1/federation/analyze` with `{"supplier_id":"SUP-002"}`).

| Step | Action | Confirm |
|------|--------|---------|
| 1 | Enter `SUP-002`, click **Run federation** | Status **Ready**; no HTTP error |
| 2 | Domain steps | Three steps: **sourcing → ebom → routing** |
| 3 | Sourcing Cypher | `SUPPLIED_BY` from supplier; rows include COMP-101, 106, 108, 110, 111 |
| 4 | Joined rows | Each row ties component → product(s) → process(es) |
| 5 | Problems / mitigations | Non-empty lists; mitigations mention alternate suppliers where applicable |
| 6 | Map | Federated supply chain map shows nodes/edges (not empty) |
| 7 | Impact score | Numeric pill present |

**Evaluate**

| Result | Criteria |
|--------|----------|
| **Pass** | ≥5 SUP-002 components in sourcing; products include PROD-900 / 901 / 902; map + joined rows populated |
| **Partial** | Sourcing OK but ebom/routing empty → check seed or component ID bridge |
| **Fail** | Empty sourcing for SUP-002 → re-run `seed_complex_bom.py --reset` |

**Baseline curl**

```bash
curl -s -X POST http://127.0.0.1:8080/v1/federation/analyze \
  -H 'Content-Type: application/json' \
  -d '{"supplier_id":"SUP-002"}' | python3 -m json.tool
```

---

### 3.2 Domain query — trace one component across graphs

**Where:** **Domain query** tab.

| Step | Action | Confirm |
|------|--------|---------|
| 1 | **sourcing**, `SUP-002` | Cypher panel shows `components_by_supplier`; table lists brass components |
| 2 | Copy component IDs (e.g. `COMP-101`) | |
| 3 | **ebom**, paste IDs | `USED_IN` rows → products (e.g. Valve → PROD-900, PROD-902) |
| 4 | **routing**, same IDs | `INPUT_OF` / process linkage |

**Evaluate:** Same component IDs appear in all three domains with consistent names/materials.

---

### 3.3 Agent — German brass supplier disruption

**Where:** **Agent (LLM)** tab → example card → **Analyze**.

**Goal sent to agent (only this text):**

> Our German brass supplier might face a port strike next month. Which finished products and component parts should we worry about?

| Step | Where | Confirm |
|------|-------|---------|
| 1 | Langfuse → `planning` | Tool `bom_supplier_impact` with `supplier_id: SUP-002` (heuristic) or equivalent (LLM) |
| 2 | Langfuse → `tool:bom_supplier_impact` | `row_count` > 0; `data` mentions Euro Brass / brass components |
| 3 | Agent UI → Summary | Answers which products/parts are at risk (plain language) |
| 4 | Agent UI → Key findings | Mentions affected products (Industrial Pump, Servo Motor Drive, Valve Manifold) and/or brass parts |
| 5 | Agent UI → Evidence | Claims only — no tool names or Cypher |
| 6 | Agent UI → Map | Non-empty if graph tool returned seeds |
| 7 | Cross-check | Compare Langfuse tool JSON to **§3.1** federation baseline for SUP-002 |

**Evaluate**

| Dimension | Pass | Fail |
|-----------|------|------|
| **Planning** | `bom_supplier_impact` invoked with `SUP-002` (or LLM equivalent reasoning visible in trace) | No tools / wrong supplier / invented ID not in seed |
| **Grounding** | Findings match tool `data` (component + product names from seed) | Part numbers or products not in tool JSON |
| **User UX** | Summary readable without IDs; evidence has no operator jargon | Empty findings while tool returned rows |
| **Telemetry** | One `bom-agent-run` trace; `planning` + tool spans present | Missing trace when Langfuse configured |

**Offline planner test (no server):**

```bash
uv run pytest -q tests/test_agent.py::test_plan_tools_from_goal
```

---

### 3.4 Agent — Servo motor drive shaft trace

**Goal:**

> The servo motor drive product relies on a drive shaft part. Can you trace how that component connects through the bill of materials to the finished assembly?

| Step | Where | Confirm |
|------|-------|---------|
| 1 | Langfuse → `planning` | `bom_supply_path` with `from_component_id: COMP-103`, `to_product_id: PROD-901` (heuristic) or valid path args (LLM) |
| 2 | Langfuse → tool output | Path / edge data between Drive Shaft and Servo Motor Drive |
| 3 | Agent UI | Summary describes BOM / routing connection |
| 4 | Map | Path-related nodes visible |

**Evaluate:** Path must connect **Drive Shaft** (`COMP-103`) to **Servo Motor Drive** (`PROD-901`). Invented intermediate parts = **fail**.

---

### 3.5 Agent — Brass valve shortage (hybrid)

**Goal:**

> We're short on brass valve-related parts. Find similar components in our catalog and show which suppliers feed them.

| Step | Where | Confirm |
|------|-------|---------|
| 1 | Langfuse → `planning` | `bom_hybrid_query` with the goal text |
| 2 | Langfuse → `tool:bom_hybrid_query` | `vector_hit` rows (name/material similarity); `rdb_detail`; `graph_impacts` or supplier linkage |
| 3 | Agent UI | Summary mentions similar brass/valve parts and suppliers |
| 4 | Ground truth | **Valve** (`COMP-101`, SUP-002) should appear in hits or impacts |

**Evaluate**

| Result | Criteria |
|--------|----------|
| **Pass** | Vector step ran; at least one brass/valve-like component; supplier Euro Brass or SUP-002 referenced from tool data |
| **Partial** | Vector hits OK but graph/supplier leg empty — note in evaluation; may be known hybrid gap |
| **Fail** | No hybrid tool call; or suppliers/products not in seed |

---

### 3.6 Agent — explicit ID (regression / API)

**Purpose:** Deterministic check without LLM interpretation.

```bash
curl -s -X POST http://127.0.0.1:8080/v1/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Analyze supplier impact for SUP-002","mode":"tools"}' | python3 -m json.tool
```

**Evaluate:** `findings` non-empty; `graph_view.node_count >= 1`; Langfuse shows `SUP-002` in tool args.

---

## 4. Evaluation rubric

Use after any **Agent (LLM)** run. Federation / Domain tabs use **functional** checks only (§3.1–3.2).

### 4.1 Dimensions

| # | Dimension | Question | Primary source |
|---|-----------|----------|----------------|
| 1 | **Data readiness** | Is LanceDB seeded and health **Ready**? | UI pill; `GET /health` |
| 2 | **Tool selection** | Did the planner pick the right tool(s) for the scenario? | Langfuse `planning` |
| 3 | **Tool execution** | Did tools return non-empty `data` when seed supports it? | Langfuse `tool:*` |
| 4 | **Grounding** | Are summary/findings/evidence supported by tool JSON? | Langfuse metadata vs Agent UI |
| 5 | **User presentation** | Is the Agent UI free of Cypher, tool names, raw JSON? | Agent UI |
| 6 | **Graph fidelity** | Does the map reflect tool graph seeds? | Agent UI map vs tool output |
| 7 | **Observability** | Is there a complete `bom-agent-run` trace? | Langfuse / `verify_langfuse_telemetry.py` |

### 4.2 Overall grade

| Grade | Meaning | Typical signals |
|-------|---------|-----------------|
| **Pass** | Demo goal met | Correct tool + args; grounded findings; federation baseline aligns |
| **Partial** | Right direction, gaps | Tool ran but summarize weak; hybrid graph leg empty; map empty but findings OK |
| **Fail** | Demo broken or unsafe | No tools; empty tool data after seed; hallucinated IDs; Langfuse missing when configured |

### 4.3 Heuristic vs LLM planner

| Mode | When | Evaluation focus |
|------|------|------------------|
| **`mode=tools`** or LLM off | CI, offline | Exact match to §3 expected tools/args (`tests/test_agent.py`) |
| **`mode=auto`** with LiteLLM | Full demo | Tool choice *reasonable* for goal; grounding still mandatory |
| **Summarize LLM** | `auto` + gateway | Evidence claims must trace to tool JSON in Langfuse `summarize` generation |

Do **not** fail an LLM run solely because args differ from heuristic — fail if tools are wrong for the business question or output is ungrounded.

### 4.4 Evaluation worksheet (copy for demos)

```text
Scenario: ______________________  Date: __________  Evaluator: __________

[ ] Seed OK (seed_complex_bom.py --reset)
[ ] Federation baseline SUP-___ pass (§3.1)
[ ] Agent run completed without HTTP error

Langfuse trace id: ______________________
Planner: heuristic / LLM
Tools called: ______________________
Tool row_count > 0: Y / N

Grounding (claims ⊆ tool JSON): Pass / Partial / Fail
User UI clean (no Cypher/tools in evidence): Y / N
Map populated: Y / N / N/A

Overall: Pass / Partial / Fail
Notes:
```

---

## 5. Where to verify (UI vs Langfuse)

### Principle

| Surface | Audience | Question it answers |
|---------|----------|---------------------|
| **Agent (LLM) tab** | Business user | *What is the impact in plain language?* |
| **Domain / Federation tabs** | Demo / architecture reviewer | *Do graphs and federation join behave correctly?* |
| **Langfuse** (`bom-agent-run`) | Developer / evaluator | *Why these tools, with what args, and what raw data backed the answer?* |

**Rule:** Langfuse-only details (planner, args, Cypher, raw JSON, evidence pointers) stay out of the Agent UI. Cypher belongs on Domain/Federation tabs.

### At a glance

| Content | Agent UI | Domain | Federation | Langfuse |
|---------|:--------:|:------:|:------------:|:--------:|
| Summary / findings / evidence (claims) | ✓ | — | — | ✓ |
| Supply chain map | ✓ | — | ✓ | counts |
| Cypher + domain tables | — | ✓ | ✓ | ✓ |
| Problems / mitigations | — | — | ✓ | — |
| Planner, tool args, raw JSON | — | — | — | ✓ |

### Agent UI — user-facing checks

| Section | What to check |
|---------|----------------|
| **Summary** | Answers the goal; no invented IDs if tools returned empty |
| **Key findings** | Component → product impacts grounded in the run |
| **Evidence** | Short claims only — no tool names, JSON paths, or Cypher |
| **Supply chain map** | Non-empty when graph tools returned seeds |

### Langfuse — operator checks

Filter **Traces** → **`bom-agent-run`**. One trace per agent run.

| Observation | Verify |
|-------------|--------|
| **Span `planning`** | `planner`; `tool_calls[]` name + arguments |
| **`tool:*`** | Input args; output `data`, `row_count`, `cypher_queries` |
| **Generation `summarize`** | Claims derivable from tool JSON |
| **Metadata** | Full `run_report`, `tool_results` |

**Indirect example cards** (Intent / Expected exploration) are **evaluator hints only** — not sent to the agent beyond the goal text.

---

## 6. Automated checks

Run after code changes or before a demo.

| Check | Command | Proves |
|-------|---------|--------|
| Unit + integration | `uv run pytest -q` | Planner, federation API, user response, skills assets |
| German brass planner | `uv run pytest -q tests/test_agent.py::test_plan_tools_from_goal` | SUP-002 routing for indirect goal |
| Federation API | `uv run pytest -q tests/test_federation_api.py` | Domain query Cypher + analyze join |
| Langfuse smoke | `uv run --extra observability python scripts/verify_langfuse_telemetry.py` | Keys + recent `bom-agent-run` traces |

---

## 7. Implementation map

| Topic | Code |
|-------|------|
| Seed / ground truth | `pipeline/demo/sample_data.py` |
| UI example cards | `app/agent/static/app.js` → `AGENT_EXAMPLES` |
| Heuristic planner | `app/agent/runner.py` → `plan_tools_from_goal` |
| User-facing response | `app/agent/user_response.py` |
| Langfuse emission | `app/agent/telemetry.py` |
| Federation analyze | `app/federation/analysis.py` |

---

## Quick links

| Task | Doc |
|------|-----|
| Start Docker + agent + Langfuse | [local-demo-runbook.md](local-demo-runbook.md) |
| Federation without LLM | [federation-demo-runbook.md](federation-demo-runbook.md) |
| Generated JSON catalogs | [agent-skill-assets.md](agent-skill-assets.md) |
| Langfuse env vars | [observability.md](observability.md) |
