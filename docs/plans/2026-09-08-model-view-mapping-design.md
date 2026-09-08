# Model → View Mapping: Unified Substrate Design

**Date:** 2026-09-08
**Status:** Draft — pending user review before Phase 1 begins
**Repos affected:** `architecture-model-standard` (schema, projector primitives, invalidation), `opencode-arch` (executor, MCP tools, triggers)
**Supersedes / relates to:**
- `2026-09-02-curated-se-views-design.md` (introduced ViewSpec/ModelSlice/ArtifactSpec)
- `2026-09-02-curated-se-views-implementation.md` (seeded 4 SE projectors)
- `2026-09-02-diagram-renderer-design.md` (renderer contract)
- `2026-07-30-hierarchical-model-organization.md` (per-subsystem M2 models)
- `2026-09-01-universal-entity-semantics.md` (prior semantic-field exploration; largely subsumed by Section 5 here)

---

## Section 0 — Context & Motivation

### The two-pipeline problem

The AMS + OCA stack ships **two parallel model→view pipelines**, neither complete alone.

**Pipeline A — Lifecycle spec-driven substrate.** `ModelSlice → materialize → MaterializedSlice → project → ProjectedView → render → bytes → rebuild_artifacts`. Extensible in principle, but ships with only 4 projectors (`se.conops`, `se.functional`, `se.logical`, `se.use_cases`) and 6 renderers. One shipped default view (the pipeline dashboard), and even it bypasses the projector layer via a renderer-side special-case.

**Pipeline B — Imperative docs generators.** `ArchitectureModel → generate_<name>(model, manifest?) → str → docs/architecture/<name>.md`. Rich: 17 SE doc formats, 3 Mermaid diagrams, plus `component_spec`, `icd`, `dependency_matrix`, `health`, `drift`, `index`, `behaviors`, `system_design`, `integration_flows`, `artifact_traceability`. All deterministic; **bypasses the slice/view contract entirely**.

### The five gaps

1. **Coverage matrix has empty cells.** Only top-level (M1) is fully wired. Per-subsystem (M2) needs manual invocation loops. Recursive manifests, MaterializedSlice fragments, and federated parent/child models have almost nothing.
2. **The two pipelines don't share a substrate.** A generator can't compose as a projector; a projector output can't feed the docs writer.
3. **No plugin/registry discovery.** Renderers are a literal module-level dict. Projectors have `register()` but no entry-point discovery. Extending = editing core.
4. **LLM available on the substrate but not woven.** `LLMProvider` protocol + `OpencodeRunner` + `DOC_PROMPTS` templates all exist; no doc or projector calls them.
5. **Non-substrate views bypass determinism guards.** SE docs, Mermaid, `component_spec`, `icd`, matrix, health lack byte-identical round-trip guards.

### Goal statement

Direct and complete mapping of architecture model(s) → views. Deterministic by default; LLM-permitted where valuable. The system operates as a **live development tool**: model and views stay fresh as code changes, piece-by-piece or at commit time. Full re-extraction is not required for typical edits.

### Approach at a glance

- **Approach A (canonical Pipeline A):** every generator becomes a registered projector; every doc type ships with a default `ViewSpec` + `ArtifactSpec`; `architect_docs` becomes sugar over `rebuild_artifacts`; per-subsystem loop lives in the rebuild orchestrator; LLM variants register alongside deterministic ones (`.llm` suffix).
- **Live via diffing:** reuse existing batch extractor + `stage_cache` + `package_diff`; a small invalidation module maps semantic diff → stale-set of views; pre-commit + post-commit CI triggers refresh only affected artifacts.
- **Targeted extract (Option B, per Section 7):** commit determines impacted subsystems from changed files; re-runs only those M2 pipelines + M1 aggregation.

---

## Section 1 — The View Taxonomy (First Principles)

### Guiding question

"If our architecture model were perfect and complete, what questions would stakeholders ask it — and what view answers each question?"

A view = **(audience, question, projection of the model, rendering)**. If two views answer the same question at the same fidelity, one is redundant.

### The eight view families

Every SE-relevant view reduces to one of these eight families. Each has a distinct audience, model subset, and decision it enables.

| # | Family | Audience | Question it answers | Primary model entities | Decision enabled |
|---|---|---|---|---|---|
| 1 | **Purpose & Stakeholders** | Sponsors, PM, new hires | Why does this system exist and for whom? | Actors, top-level Capabilities, Constraints tagged as goals/quality-attributes | Should we build/keep/kill it? |
| 2 | **Functional** | System engineers, architects | What does it do, decomposed into what functions? | Capabilities (F-blocks), Behaviors, `contains`, `triggers`, `realizes` | Is the functional decomposition sound & complete? |
| 3 | **Logical / Structural** | Software architects, tech leads | What are the parts and how do they connect? | Components, Layers, Interfaces, `depends-on`, `exposes`, `consumes` | Are boundaries right? Is coupling acceptable? |
| 4 | **Behavioral / Operational** | Ops, SREs, testers, PMs | How does it actually run — flows, scenarios, use cases? | Behaviors, Actors, Interfaces, `triggers`, `consumes` | Do the scenarios cover the mission? |
| 5 | **Physical / Deployment** | Ops, infra, security | Where does it live and how is it deployed? | Components (with deploy metadata), Interfaces (transport), `mounted-on`, `routed-through` | Is topology safe, scalable, affordable? |
| 6 | **Data & Interface Contracts** | Integrators, consumers, downstream teams | What crosses the boundaries and in what shape? | Interfaces, data models, `produces`, `subscribes-to`, `transforms` | Can I integrate without breaking? |
| 7 | **Quality & Verification** | QA, safety, compliance, auditors | How well does it meet its constraints and how do we know? | Constraints, Requirements, test_contracts, validation results, gates | Is it fit for purpose? Ready to ship? |
| 8 | **Evolution & Health** | Architects, PMs, ops | How is it changing and what's the state of the model itself? | Diffs, drift flags, SI&L rollups, learning-curve, model quality scores | Where's the risk? What needs work? |

### Design principles

1. **One family = one canonical top-level view.** Sub-views are drill-downs, not siblings.
2. **Every view has a deterministic core.** LLM authoring is a *variant* (`.llm` suffix), never the only implementation.
3. **Views compose across model kinds.** Every view family must be projectable at top-level (M1), per-subsystem (M2), per-MaterializedSlice, and (Phase 4) federated (M3).
4. **Every view carries provenance.** Which model revision, which slice, which projector, which renderer, which LLM (if any).

### Reference docs (`cli_reference`, `api_reference`, `plugin_guide`)

Per user decision: promoted through the substrate as **Family-6 (Interfaces) variants**, with CLI subcommands / HTTP routes / plugin hooks modeled as first-class `Interface` entities (see Section 2 endpoint→Interface promotion).

### LLM variant naming

Per user decision: **suffix `.llm`** (e.g., `family2.functional` vs `family2.functional.llm`). Deterministic is the default; LLM is an opt-in variant discoverable by suffix.

---

## Section 2 — Decomposition of Each Family

Per-family: canonical top-level view · standard drill-downs · model kinds it must project across · LLM variant candidacy · notable cross-cuts.

Legend for **model kinds** cell: `T`=top-level model (M1) · `S`=per-subsystem model (M2) · `M`=manifest-backed · `Sl`=MaterializedSlice · `F`=federated parent/child (M3).

### Family 1 — Purpose & Stakeholders

- **Canonical view:** *Mission & Stakeholders* — Actors, top-level Capabilities, top-level Constraints tagged as goals/quality-attributes, success criteria.
- **Drill-downs:** stakeholder register (per Actor); quality-attribute scorecard (bridges F7); goal tree (Capabilities as goals).
- **Model kinds:** T (primary), F (roll-up across federated children). Not meaningful at S/M/Sl standalone.
- **LLM variant:** `family1.mission.llm` — narrative one-pager. High value.
- **Cross-cuts:** Every goal should link to at least one Behavior (F4) and one Constraint (F7).

### Family 2 — Functional

- **Canonical view:** *Functional Decomposition* — Capability tree with `contains`, cross-block `triggers` overlaid.
- **Drill-downs:** F-block detail; behavior catalog; cross-block flow; functional coverage (capabilities with 0 realizations flagged).
- **Model kinds:** T, S, Sl.
- **LLM variant:** `family2.functional.llm` — narrative per F-block. Medium value.
- **Cross-cuts:** Capabilities anchor F1, F3 (via `realizes`), F4, F7.

### Family 3 — Logical / Structural

- **Canonical view:** *Component & Layer Map* — Components grouped by Layer, `realizes` edges to Capabilities, `depends-on` inside.
- **Drill-downs:** component spec; layer view; dependency matrix; boundary check; sub-system atlas (link to child M2 model).
- **Model kinds:** T, S, Sl, F. M-backed for signatures/imports.
- **LLM variant:** `family3.component_spec.llm` — narrative per component. Low-medium value.
- **Cross-cuts:** Anchors F2 (`realizes`), F5 (deployment target), F6 (interfaces).

### Family 4 — Behavioral / Operational

- **Canonical view:** *Use-Case & Scenario Catalog* — Behaviors as scenarios, Actors as participants, Interfaces as messages.
- **Drill-downs:** use case detail; operational sequence; runbook (ops-tagged); maintenance procedures.
- **Model kinds:** T, S, Sl. F only for cross-repo use cases (rare).
- **LLM variant:** `family4.use_cases.llm` — narrative case studies. High value.
- **Cross-cuts:** Anchors F2 (realizing capability), F6 (interface messages), F7 (test_contract per behavior).

### Family 5 — Physical / Deployment

- **Canonical view:** *Deployment Topology* — nodes/hosts, components mounted on them, connections routed through.
- **Drill-downs:** environment tier; network diagram; resource inventory; failure domains.
- **Model kinds:** T, F. Not typically S/Sl/M.
- **LLM variant:** low value (topology is structural).
- **Cross-cuts:** Anchors F3, F7.
- **Note:** Many current models don't populate deployment metadata; view will be sparse until that's a first-class concern.

### Family 6 — Data & Interface Contracts

- **Canonical view:** *Interface Catalog* — all Interfaces with producer/consumer, direction, data schema.
- **Drill-downs:** ICD (per-interface spec); API reference (REST/RPC from manifest); CLI reference (from Click/argparse decorators); plugin guide (extension points); data model; event catalog; consumer view.
- **Model kinds:** T, S, Sl, **M (heavy — reference docs need signatures/routes/decorators from manifest)**, F.
- **LLM variant:** `family6.icd.llm`, `family6.data_model.llm`. Medium value.
- **Design implication:** ModelSlice needs manifest access. **Chosen mechanism (user decision):** `MaterializedSlice.manifest_fragment` populated by the materializer whenever a slice declares a manifest scope. Manifest fragment carries signatures, routes, decorators alongside model entities.
- **Endpoint promotion:** Per user decision, CLI subcommands / API endpoints / plugin hooks are extracted as `Interface` entities. Model becomes ground truth; manifest supplies enrichment.

### Family 7 — Quality & Verification

- **Canonical view:** *Requirements-to-Verification Matrix* — each Constraint/Requirement → verification method → status.
- **Drill-downs:** requirements analysis; V&V plan; verification results; risk register; safety analysis (profile-specific); security analysis; gate report.
- **Model kinds:** T, S, Sl, F.
- **LLM variant:** `family7.risk.llm`, `family7.security.llm`. High value.
- **Design implication:** Test results, gate outcomes, safety findings live outside the model YAML. **Chosen mechanism:** `ModelSlice.supplementary_refs` (well-known kinds: `manifest`, `sil`, `gates`, `test_results`, `drift`, `learning`). Materializer resolves each into a fragment on `MaterializedSlice`.

### Family 8 — Evolution & Health

- **Canonical view:** *Model Health Dashboard* — validation score, regen readiness, coverage %, SI&L rollups.
- **Drill-downs:** model diff; package diff; drift report; SI&L rollups; learning curve; gate history; traceability map.
- **Model kinds:** T primary. F for federated health. S rarely (per-subsystem health is a filter of T).
- **LLM variant:** low value (health data is quantitative); possibly `family8.health.llm` for executive summary.
- **Design implication:** Multi-revision / trend views need temporal data. **Chosen mechanism:** ModelSlice supports optional `revision_range: (from, to)` and `time_window` fields. Materializer resolves them to the appropriate historical fragments.

### Drill-down inventory

Family 1: 4 · Family 2: 5 · Family 3: 6 · Family 4: 5 · Family 5: 5 · Family 6: 8 · Family 7: 8 · Family 8: 8. **Total ≈ 49 top-level views** (vs 27 doc types today). Growth comes from making drill-downs first-class, adding missing purpose/health/feedback views, and per-model-kind projections.

---

## Section 3 — Feedback Loops

### The loop pattern

A feedback loop = **model → view → observation → (correction | learning) → model**. Six loops exist or should exist. Each shapes the catalog.

| # | Loop | Signal | Surfacing view | Correction path | Loop-closed view |
|---|---|---|---|---|---|
| 1 | Extraction ↔ model quality | validation score, sub-scores | F8 Health Dashboard | `architect_correct`, next pipeline run | F8 health trend |
| 2 | Model ↔ code reality (drift) | drift flags | F8 Drift Report + F2 Functional Coverage | re-run pipeline, `architect_require`, `architect_correct` | F8 drift resolution rate |
| 3 | Requirement ↔ verification | unverified requirement, orphan verification | F7 Req→Verification Matrix | add requirement, add test contract | F7 V&V coverage; F8 gate pass rate |
| 4 | Gate outcomes ↔ model maturity | phase gate criteria | F7 Gate Report | fix identified gap; re-run gate | F8 Gate History |
| 5 | Runtime reality ↔ model (SI&L) | invocation, failure rate, latency | F8 SI&L Rollup + F3 badges | `architect_correct` remove dead comp; hotspot issue | F8 runtime coverage trend |
| 6 | Learning ↔ extraction (arch-agent) | compression ratio, iterations, patterns | F8 Learning Curve | learned heuristic → prompt optimizer | F8 learning curve trend |

### Overlay pattern (user-adopted)

Rather than shipping `family3.component_spec`, `family3.component_spec.with_sil`, `family3.component_spec.with_drift`, `family3.component_spec.with_both` (combinatorial explosion), views declare **overlay slots** in ViewSpec curation:

```yaml
curation:
  overlays: [sil, drift, gates]   # optional list, deterministic order
```

The projector renders base view + overlays it recognizes. Unknown overlays are ignored. Small addition to ViewSpec contract; eliminates variant explosion.

### Feedback persistence (user-adopted)

Three lightweight append-only journals unlock all Loop 3/4/5 trend views:

- `.architecture/gates.jsonl` — every `architect_gate` outcome appended.
- `.architecture/drift.jsonl` — drift snapshots after each extraction.
- `.architecture/test_results.jsonl` — ingested JUnit/pytest results.

Append-only, never invalidated; perfect fit for incremental updates.

### Cross-loop insights

- **Drift is a cross-cut, not its own family.** Same signal appears in F2 (unrealized capabilities), F3 (untracked components), F8 (aggregate). Factor drift computation as a shared helper: `architecture_model.core.drift`.
- **Feedback data is uniformly supplementary.** All loops (except Loop 1) require data outside the model YAML. The `supplementary_refs` contract from Section 2 covers all uniformly.
- **The eight families cover the loops without a 9th "feedback" family.** Feedback isn't its own family — it's the signal that drives updates to views in the existing families.

---

## Section 4 — Fractal Recursion

### The recursion rule

**Every entity in the model is a "system-of-interest" at its own scale.** The same eight-family lens that answers questions about the root also answers them about a Capability, Component, Behavior, Interface, or nested subsystem.

For entity `E`, the eight views become:

| Family | Applied to entity E |
|---|---|
| 1 Purpose | Who does E serve? What stakeholders depend on E? |
| 2 Functional | What does E do, decomposed into its parts (`contains`)? |
| 3 Logical | E's internal parts and their internal `depends-on` graph |
| 4 Behavioral | Scenarios E participates in |
| 5 Physical | Where E is deployed / what it's mounted on |
| 6 Interfaces | E's exposed & consumed interfaces; ICDs |
| 7 Quality | Requirements allocated to E; E's constraints; verification status; failure modes |
| 8 Evolution | E's health: validation issues touching E; SI&L rollup for E; drift; revision history |

### Registry becomes two-dimensional

Projector namespace: **(family × entity-scope)**. Family-scoped operates on a slice representing a whole system-of-interest; entity-scoped operates on a single entity. Not every (kind, family) pair is meaningful (e.g., Interfaces don't have their own deployment view). Pragmatic count: **≈ 40 entity-page projectors** across common intersections.

### Drill-down IS re-projection at smaller scope

Today "drill-down" means "click into a component." In the recursive model, drill-down is re-projection:

- Click Capability CAP-F1 in F2 root → project F2 at scope CAP-F1 → sub-capabilities and their triggers.
- Click Component COMP-3 in F3 root → project F3 at scope COMP-3 → internal modules.
- Click Behavior BEH-7 in F4 root → project F4 at scope BEH-7 → sub-behaviors and participating interfaces.

**Every projector needs `scope: EntityRef`.** ModelSlice already supports scoping by fblock/layer. Generalize: `slice_by_entity(model, entity_id)` returns the sub-model rooted at that entity's transitive closure.

### Cross-scale traceability

Every `ProjectedView` carries:

- `scope_chain: list[EntityRef]` — breadcrumb: root → subsystem → capability → component
- `parent: EntityRef?` — the entity's parent by `contains`
- `peers: list[EntityRef]` — sibling entities at the same scope
- `roll_up: bool` — data local to E, or aggregated from E's children?

### Depth control

Every ViewSpec declares:

- `depth: int` — how many `contains` levels to descend before rendering children as opaque links (default 1).
- `expand_kinds: list[EntityKind]` — which kinds recurse.

Deterministic and safe.

### Consequence for family count

Taxonomy stays at 8. What grows is the **projector matrix** (family × entity-kind × scope) and the **slice contract** (must support entity-scoped slicing).

---

## Section 5 — Entity-Level Semantic Content

### The problem

Today an entity looks approximately like:

```yaml
- id: COMP-3
  name: Parser
  kind: module
  status: ACTIVE
  files: [src/architecture_model/core/parser.py]
```

That answers "what is this called and where does it live" but not "**why does it exist, what could go wrong, what did we choose, and what did we choose against.**" Per-entity F1/F7 views (Section 4) require semantic content.

### Proposed enrichment schema

Optional fields on every entity kind:

| Field | Purpose | Consumed by |
|---|---|---|
| `intent` (str) | One-sentence "why this exists." | F1 per-entity, F2 |
| `goals` (list[str]) | Measurable outcomes expected. | F1, F7 |
| `stakeholders` (list[EntityRef]) | Actors/peers depending on E. | F1 |
| `success_criteria` (list[str]) | Objective checks that intent is fulfilled. | F1, F7 |
| `failure_modes` (list[FailureMode]) | FMEA-lite. | F7 safety/risk, F8 |
| `trade_offs` (list[TradeOff]) | Living ADR fragments per entity. | F1, F3, F7 |
| `assumptions` (list[str]) | Assumed truths; if violated, guarantees may fail. | F7 risk |
| `open_questions` (list[str]) | Known unknowns. | F7, F8 (maturity) |
| `requirements` (list[RequirementRef]) | Requirements allocated to E. | F7 |
| `verification` (list[VerificationRef]) | Test contracts / methods verifying E. | F7 |
| `slos` (list[SLO]) | Latency, availability, throughput targets. | F5, F7, F8 |
| `owner` (str \| EntityRef) | Human/team accountable. | F1, F8 |
| `maturity` (enum) | proposal / draft / active / stable / deprecated | F1, F8 |
| `dependencies_rationale` (dict[EntityRef, str]) | Per `depends-on`, WHY we depend. | F3 |

### Nested types

```
FailureMode:
  id: str
  cause: str
  effect: str
  likelihood: enum(rare, unlikely, possible, likely, certain)
  severity: enum(negligible, minor, moderate, major, catastrophic)
  detection: str
  mitigation: str
  mitigated_by: list[EntityRef]

TradeOff:
  id: str
  decision: str
  alternatives: list[str]
  rationale: str
  consequences: list[str]
  revisit_when: str
  status: enum(active, superseded, revisited)

SLO:
  metric: str
  target: str
  window: str
  current: str?              # populated by SI&L overlay
```

### Kind-specific applicability

| Field | Actor | Capability | Behavior | Component | Interface | Constraint | Layer |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| intent | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| goals |  | ✓ | ✓ | ✓ |  |  | ✓ |
| stakeholders |  | ✓ | ✓ | ✓ | ✓ |  |  |
| success_criteria |  | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| failure_modes |  |  | ✓ | ✓ | ✓ |  |  |
| trade_offs |  | ✓ |  | ✓ | ✓ |  | ✓ |
| assumptions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| open_questions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| requirements |  | ✓ | ✓ | ✓ | ✓ |  |  |
| verification |  | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| slos |  |  |  | ✓ | ✓ |  |  |
| owner |  | ✓ |  | ✓ |  |  | ✓ |
| maturity |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| dependencies_rationale |  |  |  | ✓ |  |  |  |

### Population paths

1. **Extraction pipeline.** `specify`/`contract` stages can seed `intent` from docstrings, `slos` from constraints, `failure_modes` from exception-handling patterns.
2. **LLM enrichment via write-back projectors.** F1 `intent`, F3 `dependencies_rationale`, `trade_offs` are prime LLM-authored. `.llm` variants emit **AI Proposals** (existing `architecture_model.ai` infra) rather than rendering only. Once accepted, the field lives in the model and deterministic projectors render it thereafter. **Key insight:** enrichment moves LLM output from view time to authoring time.
3. **Human authoring.** Reviewers annotate during design reviews via extended `architect_require` or a new `architect_annotate` MCP tool.

### Schema versioning

**schema_version bumps to 2.1** (additive; existing models pass through untouched; enriched fields render as skeleton when absent). Migration: `0.3.0` models remain valid `2.1`; new fields optional.

---

## Section 6 (revised) — Live/Incremental via Diff

### Simplification insight

Rather than build a bespoke incremental extractor, reuse three primitives already in the codebase:

- `stage_cache` — pipeline stages can skip work when inputs unchanged.
- `package_diff` — semantic diff between published generations.
- `rebuild_artifacts` with `expected_digest` — skip rebuilds when inputs unchanged.

The flow becomes:

```
Changed files  →  invalidate stage_cache entries for those files
              →  run full pipeline (cache absorbs bulk of work)
              →  new .architecture-model.yaml produced
              →  package_diff(current_gen, new_model)  = semantic delta
              →  invalidation module: diff → stale-set of views
              →  rebuild_artifacts on stale-set only
              →  publish new generation
```

### Stage_cache granularity (verified)

`pipeline/cache.py:190` writes one JSON per stage holding the whole `StageResult`. Cache is **per-stage, not per-file**. Any changed file invalidates the whole `observe` stage; observe re-scans the repo. For AMS (189 modules), a cache-cold observe + downstream deterministic stages run in a few seconds each. Fits <30s pre-commit target **provided LLM stages don't fire on every commit**. Per-file caching is deferred; can be added if needed.

### What this eliminates from prior designs

- ❌ Bespoke incremental extractor as proposer plugin
- ❌ File→entities ownership map
- ❌ Threshold fallback logic (only one extraction path exists)
- ❌ Full/incremental equivalence invariant (single-path)

### What stays

- ✅ **Invalidation module** at `architecture_model/lifecycle/invalidation.py`. Maps `SemanticDiff` → stale-set of view IDs. Deterministic rule table.
- ✅ **Pre-commit + post-commit triggers.** Pre-commit runs targeted extract, validates, blocks commit on failure. Post-commit CI is authoritative.
- ✅ **Freshness metadata** on artifacts: `provenance.freshness ∈ {fresh, stale, pending}` + `provenance.revision`.

### Latency target

Pre-commit hook: **<30s** for typical single-file change. Optimize per-file caching only if this target is missed in practice.

### Invalidation rule table (data, not code)

Entity/relationship-level rules mapping diff kinds → affected view families:

- Component add/remove → F3 root, F3 per-entity (added/removed comp + peers), F2 root, F8 diff
- Capability change → F1 root, F2 root + sub-tree, F7
- Constraint add → F7 root, F1 quality-scorecard
- Semantic field change (intent/failure_modes/trade_offs/…) → per-entity F1/F7 view only (surgical)
- Interface change → F6 root + per-entity, F3 pages that expose/consume it

Rules live as data in `invalidation.py` so they can be unit-tested exhaustively.

### Full/incremental equivalence

Only one extraction path exists (`stage_cache`-accelerated full run). Views rebuilt on a partial commit are byte-identical to views rebuilt on a full re-extraction of the same tree — guaranteed by determinism of every projector + renderer.

---

## Section 7 — Which Models Does the Pipeline Operate On?

### Three models in play

| # | Model | Path | Scope |
|---|---|---|---|
| M1 | Top-level (root) | `.architecture-model.yaml` | Repo-wide: subsystem-level components, cross-subsystem relationships, root-level capabilities/actors/constraints |
| M2 | Per-subsystem | `.architecture-models/<sys>/.architecture-model.yaml` × 25 today | Subsystem-internal architecture (complete, self-contained) |
| M3 | Federated / SoS | Composed via `package.yaml` `children:` refs, `federated_ref: bool` | Multiple repos federated |

M1 + M2 fully populated in AMS today. M3 scaffolded (`iter_descendants`, federated slice scope, `_diff_children`) but not exercised at repo scope.

**Actual AMS layout (as of 2026-09-08):** 25 sub-models exist under `.architecture-models/`: S1–S15 (numeric) plus named (utilities, pipeline-learning, export, cli, configuration, authoring, extract, orchestration, documentation, manifest, pipeline, core). CONTEXT.md's "6 subsystems" claim is stale — Phase 1 fixes.

### Code-change → models table

| Code change | Which models must update |
|---|---|
| Edit inside a single subsystem file (no public-interface change) | Only that subsystem's M2 |
| Add new subsystem (new directory + module cluster) | M1 adds component + M2 created |
| Rename / delete a subsystem | M1 + one M2 |
| Change an interface between two subsystems | Both subsystems' M2 (both `expose`/`consume`), possibly M1 |
| Cross-repo API change (M3 in use) | Exposing M2 + exposing M1 + federating repos' M3 |

### Option B — Targeted extract (chosen)

1. Determine impacted subsystems: `changed_files → subsystems that own any of them` via each M2's `component.files`.
2. Re-run only those M2 pipelines.
3. Re-run M1 aggregation (fast: reuses M2 stage_cache).
4. `package_diff` on M1 and each impacted M2 → semantic deltas.
5. Invalidation module maps deltas → stale-set of views.
6. `rebuild_artifacts` on stale-set only.

### M2 → M1 propagation rules

Encoded as data in `invalidation.py`:

- M2 adds/removes a component with an `exposes` relationship surviving to M1 → **invalidate M1**.
- M2 adds/removes a `depends-on` edge crossing subsystem boundary → **invalidate M1**.
- M2 changes only internal component, interface, capability, or relationship → **M1 unchanged**.
- M2 semantic-field change on entities appearing in M1 → **surgical M1 update** (semantic fields only).
- File added/removed that maps to no existing subsystem → **M1 investigates** for new subsystem or top-level component.

### Views declare their model explicitly

Registry key: **(family, entity_kind_or_none, scope)** where `scope ∈ {M1, M2, Sl, F}`. Cross-subsystem views target M1; per-subsystem views target the relevant M2; slice-of-interest views target Sl.

`ModelSlice.scope` already supports `local | descendants | federated` — aligns with M1(`descendants`), M2(`local`), M3(`federated`).

### Federated (M3) deferred to Phase 4

Cross-repo trigger design (child publish → parent invalidation), federated materialization completion, cross-repo diff/rebuild all land together in Phase 4.

---

## Consolidated Substrate Additions (17 items across 4 phases)

| # | Addition | Phase | Owner repo |
|---|---|:-:|:-:|
| 1 | Overlay slots in ViewSpec curation | 2 | ams |
| 2 | `ModelSlice.supplementary_refs` | 2 | ams |
| 3 | Temporal slicing (`revision_range`, `time_window`) | 2 | ams |
| 4 | Feedback persistence (gates.jsonl, drift.jsonl, test_results.jsonl) | 2 | ams (writers) + oca (hook wiring) |
| 5 | Endpoint→Interface promotion (extractor) | 4 | ams |
| 6 | Entity-scoped slicing (`slice_by_entity`) | 3 | ams |
| 7 | Scope-chain in ProjectedView | 3 | ams |
| 8 | Entity semantic schema (§5 fields) | 2 | ams |
| 9 | `schema_version` bump to 2.1 + migration | 2 | ams |
| 10 | Write-back projector class (AI Proposal emitters) | 4 | ams |
| 11 | Projector registry canonicalization + `.llm` naming | 1 | ams |
| 12 | `architect_docs` as `rebuild_artifacts` sugar | 1 | oca |
| 13 | Per-subsystem rebuild loop in executor | 1 | oca |
| 14 | Determinism guards for all projectors + generators | 1 | ams |
| 15 | `MaterializedSlice.manifest_fragment` | 2 | ams |
| 16 | Invalidation module (diff → stale-set) | 1 | ams |
| 17 | Pre-commit + post-commit templates + freshness metadata | 1 | ams (schema) + oca (evaluate) |

---

## Phasing

**Phase 1 — Substrate + liveness foundation.**
Registry canonicalization, `architect_docs` sugar, per-subsystem rebuild loop, invalidation module, targeted-extract dispatch (Option B), pre-commit + post-commit templates, freshness metadata, determinism guards for all existing projectors + generators, CONTEXT.md refresh. **No schema changes. No new UX. No LLM writes.**

**Phase 2 — Schema + semantic content.**
Entity semantic schema (§5), `schema_version` 2.1 + migration, `supplementary_refs`, `manifest_fragment`, temporal slicing, feedback persistence journals, overlay slots.

**Phase 3 — Recursion + entity views.**
Entity-scoped slicing, scope-chain on ProjectedView, entity-page projectors × (family, entity_kind), fractal drill-down.

**Phase 4 — LLM write-back + endpoint promotion + federated (M3).**
Write-back projector class emitting AI Proposals; endpoint→Interface extractor; federated materialization completion + cross-repo trigger.

Each phase ships independently and passes full ams + oca test suites at baseline.

---

## Determinism & Migration Invariants

- **Byte-identical determinism** required for every deterministic projector and every renderer. Round-trip tests guard every projector; new tests added in Phase 1 for the 4 seeded projectors + all 17 SE generators + 3 Mermaid generators + non-SE generators.
- **Schema backward-compat.** `schema_version: 2.0` models continue to parse and validate after 2.1 lands. New fields are optional.
- **`.architecture*` untouched by tooling.** Never staged, never modified, never committed by the plan's own changes.
- **Base-branch discipline.** Feature branches created off `main`; no rebasing over shared history.
- **PYTHONPATH pattern** retained: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q`. No `pip install -e`.
- **One commit per task.** Conventional Commit format. Verification skill invoked before claiming complete.
- **Test baselines locked:** ams `2918 passed + 6 pre-existing`; oca `917 passed + 2 pre-existing`.

---

## Open Questions (deferred)

- **Federated (M3) trigger.** When a child repo publishes, how does the parent repo learn? Options: webhook, filesystem watch (monorepo case), pull-based CI. Decision punted to Phase 4.
- **IDE watcher process.** On-save low-latency refresh. Not required for correctness (pre-commit hook is the enforceable boundary). Phase 2+ if user demand.
- **Per-file `stage_cache` keys.** Only add if the <30s pre-commit target proves consistently violated. Phase 2+ if needed.
- **LLM prompt caching / budget policy.** `.llm` variants can be expensive; policy layer already exists (`opencode_arch/llm/policy.py`) — Phase 4 adds per-projector budget rules.
- **Migration of existing `.architecture-model.yaml` files** across all downstream projects. Phase 2 ships a migration CLI; project owners run it once.

---

## CONTEXT.md Drift (Phase 1 fixes)

Both CONTEXT.md files carry stale claims. Phase 1 refreshes:

**`architecture-model-standard/CONTEXT.md`:**
- Claims "6 subsystems" — actual is **25** (M2 count per `.architecture-models/`).
- Claims "4 Mermaid diagrams per model" (`context.mmd`, `components.mmd`, `behaviors.mmd`, `dependencies.mmd`) — actual output is **3 markdown files** (`component-diagram.md`, `use-case-diagrams.md`, `system-boundary-diagram.md`).
- SE workflow section predates the projector/view substrate; refresh to describe Approach A.

**`opencode-arch/CONTEXT.md`:**
- Refresh `architect_docs` description to note it becomes sugar over `rebuild_artifacts` in Phase 1.
- Note freshness metadata is emitted on rebuilds.

---

## References

- Prior plans: `2026-09-02-curated-se-views-{design,implementation}.md`, `2026-09-02-diagram-renderer-design.md`, `2026-07-30-hierarchical-model-organization.md`, `2026-09-01-universal-entity-semantics.md`
- Session report: `docs/reports/2026-09-05-phase1-escalations-and-ams-adoption.md`
- Companion Phase 1 plan: `docs/plans/2026-09-08-phase-1-substrate-and-liveness.md`
