# Agent skill assets and catalog versioning

How generated JSON catalogs relate to Agent Skills, the BOM application, and multi-agent deployment. Complements [development.md](development.md) (authoring workflow), [graph-contract.md](graph-contract.md) (Graph Contract YAML), and [graph-context.md](graph-context.md) (graph context bundle). **Terminology:** [terminology.md](terminology.md). This doc focuses on **catalog versioning** for all JSON artifacts (`ontology.json`, `graph-context.json`, …).

## Problem

Today this repository **copies** generated JSON into Skill packages:

| Artifact | Paths (today) | Generated from |
|----------|---------------|----------------|
| `ontology.json` | `ontology/assets/`, `skills/bom-ontology/assets/` | `ontology/schema.py` |
| `graph-context.json` | `skills/bom-graph-explorer/assets/` | `domains/export.py` |
| `query-catalog.json` | `skills/bom-graph-explorer/assets/` | `ontology/cypher_builder.py` |
| `cypher-engine-profile.json` | `skills/bom-graph-explorer/assets/` | `domains/export.py` |

That works for a **single repo + single deploy** demo. In production:

- Skills may be installed on **many agent hosts** (Cursor, internal runners, SDK agents).
- **Different Skill versions** may be in use at the same time.
- Each Skill version may need a **specific catalog version** (schema + query recipes must match the runtime app).

Copying JSON into every Skill bundle without a version contract causes **silent drift** (Skill v1.0 + catalog built from schema v2).

---

## Design principle: one authoring pipeline, multiple publish targets

```
┌─────────────────────────────────────────────────────────────┐
│  Authoring SSOT (human edits — Python / YAML only)            │
│  ontology/schema.py                                         │
│  ontology/cypher_builder.py                                 │
│  domains/registry.py + domains/export.py                    │
│  ontology/contract/graph_contract.yaml (Graph Contract SSOT) │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
              scripts/sync_ontology.py  (CI + local)
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   Git commit          Catalog registry     Optional
   (demo / pin)        (production)         S3/GCS artifact
         │                  │                  │
         ▼                  ▼                  ▼
   Skill packages      Agent / app resolve   CDN mirror
   (bundled copy)      by catalog version
```

**Rule:** Never hand-edit generated JSON. Never maintain a second schema table in Skill markdown.

---

## Artifact roles (what each JSON is for)

| Artifact | Consumers | Mutable by | Runtime data? |
|----------|-----------|------------|---------------|
| `ontology.json` | Agents (compose/validate), external validators | Sync only | No — schema shapes |
| `graph-context.json` | Agents (graph context: domain scope, federation bridges) | Sync only | No |
| `query-catalog.json` | Agents (named Cypher recipes) | Sync only | No |
| `cypher-engine-profile.json` | Agents (lance-graph dialect limits) | Sync only | No |
| LanceDB / DuckDB under `data/` | App tools, federation API | Seed / ingest pipelines | **Yes** — BOM instances |

Skills carry **catalog metadata**, not graph rows.

---

## Current model (this repository — P0)

| Who | What | When |
|-----|------|------|
| **Developer** | Edits `schema.py`, `cypher_builder.py`, or `domains/export.py` | Feature / schema change |
| **Developer or CI** | Runs `uv run python scripts/sync_ontology.py` | After SSOT edit |
| **Developer** | Commits regenerated JSON under `skills/*/assets/` | Same PR as SSOT |
| **CI** | `tests/test_skill_ontology_asset.py`, `tests/test_skill_agent_assets.py` | Every push — fail on drift |
| **BOM agent server** | `app/agent/skills.py` reads JSON from `repo_root/skills/...` at prompt build time | Process start / each `build_system_prompt()` |
| **External agents** | `npx skils add … --path skills/bom-ontology` (etc.) | User install — gets **bundled JSON at install time** |

**Version coupling:** App deploy and Skill install are tied to **the same Git commit** if both come from this repo. No explicit catalog semver yet (`meta.version` is a **format** version, not a release id).

---

## Target model (multi-agent, multi-version)

Separate three concerns:

| Concern | Owner | Versioned as |
|---------|-------|--------------|
| **Catalog content** | Platform / data governance | `catalog_id` + semver (e.g. `bom-graph@1.4.0`) |
| **Skill package** | Agent team | Skill semver (e.g. `bom-graph-explorer@1.1.0`) |
| **BOM application** | App team | App release + **pinned catalog_id** |

### Catalog registry (recommended production store)

A **catalog bundle** is an immutable release:

```
bom-catalog/1.4.0/
  ontology.json
  graph-context.json
  query-catalog.json
  cypher-engine-profile.json
  manifest.json          # catalog_id, built_from_git_sha, compatible_skill_ranges
```

**Storage options** (pick one; same sync output feeds all):

| Store | Use when |
|-------|----------|
| **Git tag + release asset** | Small teams, audit trail, same as today but tagged |
| **Object storage** (S3/GCS) | Many agents, CDN, no app redeploy for catalog-only fix |
| **Internal HTTP API** | `GET /v1/catalogs/{id}` — central registry with ACL |
| **OCI / artifact registry** | Already using container registry for deploy artifacts |

**Not recommended as catalog SSOT:** LanceDB/DuckDB (wrong layer), Skill markdown, prompt cache.

### Skill ↔ catalog binding

Skills should declare **compatibility**, not silently embed the latest catalog.

**Option A — Bundled copy (offline-friendly)**  
Skill tarball includes JSON **plus** manifest:

```yaml
# skills/bom-graph-explorer/SKILL.md front matter (target)
catalog:
  bundled: true
  catalog_id: bom-graph@1.4.0
  min_app_version: "0.2.0"
```

Agent uses bundled files unless `CATALOG_URL` overrides.

**Option B — Reference only (central catalog)**  
Skill markdown has no JSON; install manifest points to registry:

```yaml
catalog:
  bundled: false
  catalog_id: bom-graph@1.4.0
  url: https://catalog.example.com/bom-graph/1.4.0/
```

Agent resolves at startup; Skill semver can stay stable while catalog patch updates.

**Option C — Hybrid (recommended)**  
- Default: bundled copy for reproducibility and `npx skils add` offline use.  
- Override: env `BOM_CATALOG_URL` or `BOM_CATALOG_ID` for pinned remote fetch.  
- App and agents log `catalog_id` in Langfuse / run report.

### Application configuration

```bash
# BOM agent server (target)
BOM_CATALOG_SOURCE= bundled | registry
BOM_CATALOG_ID=bom-graph@1.4.0
BOM_CATALOG_URL=https://…   # when source=registry
BOM_REPO_ROOT=…           # when source=bundled (today)
```

Runtime tools (`bom_supplier_impact`, federation Cypher) must use **the same catalog generation** as the agent prompt, or tool execution and LLM reasoning diverge.

---

## Multi-agent scenarios

### Scenario 1 — Same repo, many Cursor users

Each user runs `npx skils add` from a **tag**. Catalog version = Git tag. No separate registry until needed.

### Scenario 2 — App in K8s, agents on SDK / CI

| Component | Catalog source |
|-----------|----------------|
| Web UI + `/v1/agent/run` | ConfigMap or init container with catalog bundle at `bom-graph@X.Y.Z` |
| SDK batch agent | Same `BOM_CATALOG_ID` in job env |
| Developer laptop Skill | Bundled JSON from Skill release built in CI from same tag |

**CI gate:** one `sync_ontology.py` job publishes bundle; downstream jobs consume artifact hash.

### Scenario 3 — Skill v1.0 and v1.1 agents coexist

| Skill version | Expects catalog | Breaking change |
|---------------|-----------------|-----------------|
| `bom-graph-explorer@1.0` | `bom-graph@1.x` | — |
| `bom-graph-explorer@1.1` | `bom-graph@1.4+` | New query name in catalog |

Publish `manifest.json`:

```json
{
  "catalog_id": "bom-graph@1.4.0",
  "skill_compatibility": {
    "bom-graph-explorer": ">=1.1.0,<2.0.0",
    "bom-ontology": ">=1.0.0,<2.0.0"
  }
}
```

Agents with Skill 1.0 + catalog 1.4 either work (backward compatible) or **fail fast** at startup with a clear mismatch error — never partial drift.

---

## CI/CD workflow (target)

```yaml
# Conceptual pipeline
1. lint + test (pytest including skill asset drift tests)
2. sync_ontology.py  →  staging/catalog/
3. attach manifest (git sha, catalog semver bump policy)
4. publish:
     - git commit (if repo-embedded)
     - upload to s3://catalogs/bom-graph/1.4.0/
     - build skill tarballs with bundled copy + catalog_id metadata
5. deploy app with BOM_CATALOG_ID=1.4.0
6. smoke: agent run + federation API against pinned catalog
```

**Who bumps catalog semver?**

| Change | Bump |
|--------|------|
| New optional field on `Component` | Patch (1.4.0 → 1.4.1) if backward compatible |
| New `ALLOWED_EDGES` pair | Minor (1.4 → 1.5) — breaking for old agents |
| Rename query in `QUERY_SPECS` | Minor or major + Skill major |

---

## Decision matrix

| Requirement | Stay with Git + Skill bundle | Add catalog registry |
|---------------|------------------------------|----------------------|
| Single deploy demo | ✅ | Overkill |
| Multiple agent hosts | ⚠️ pin Git tag | ✅ |
| Catalog hotfix without app redeploy | ❌ | ✅ |
| Air-gapped agents | ✅ bundled | Mirror registry |
| Tenant-specific ontology | ❌ | ✅ per-tenant catalog_id |
| Audit / compliance | Git tags | Registry + signed artifacts |

---

## Migration from today

| Phase | Action |
|-------|--------|
| **Now** | Keep JSON in `skills/*/assets/`; document in this file; drift tests in CI |
| **Next** | Add `manifest.json` to sync output with `catalog_id`, `git_sha`, `built_at` |
| **Then** | Skill front matter declares `catalog_id`; run report logs it |
| **Later** | CI publishes bundle to registry; app/agents use `BOM_CATALOG_ID` with bundled fallback |

Do **not** move catalog SSOT to DB tables editable by agents. DB holds **instance graph data**; catalog remains generated from Python SSOT.

---

## Related docs

| Topic | Doc |
|-------|-----|
| Authoring & sync commands | [development.md](development.md), [seeding.md](seeding.md) |
| Terminology SSOT | [terminology.md](terminology.md) |
| Graph Contract (YAML SSOT) | [graph-contract.md](graph-contract.md) |
| Graph context (`graph-context.json`) | [graph-context.md](graph-context.md) |
| Skill install | [skills/README.md](../skills/README.md) |
| Drift tests | [testing-and-quality.md](testing-and-quality.md) |
| Compose protocol (prose) | [skills/bom-graph-explorer/references/cypher-compose.md](../skills/bom-graph-explorer/references/cypher-compose.md) |

---

## Summary

| Question | Answer |
|----------|--------|
| Is copying JSON into Skills wrong? | **No** for demo and offline distribution — it is a **publish target**, not a second SSOT |
| What is wrong? | Hand-editing JSON or Skills without version pins when **multiple agent versions** coexist |
| Production pattern | **One sync pipeline** → immutable **catalog releases** → Skills and app **pin `catalog_id`** |
| Object storage / DB? | **Object storage or registry** for catalog bundles; **LanceDB/DuckDB** for BOM data only |
| Multi-version Skills | Skill semver + `manifest.json` compatibility range + fail-fast on mismatch |
