# Six-Pipeline Completeness Audit — 2026-09-12

**Scope**: Six operational pipelines — EXTRACT, DEV-LOOP, SLICE, SELF-IMPROVEMENT, LLM-PROVIDER, LOGGING — assessed against ISO/IEC/IEEE 42010, 15288, 29148, INCOSE Handbook v5, SysML/Arcadia stratification, and FMEA/STPA hazard framing.

**Purpose**: Establish the baseline for a schema-2.2 additive enrichment pass. This dossier is the reference gap register the subsequent commits close, one pipeline per commit.

**Model under audit**: `.architecture-model.yaml`, schema 2.1.
**Baseline test count**: 3690 passed, 104 skipped.

---

## 1. Ground-truth entity inventory

| Kind          | Count | Description present | Intent | Goals | Failure modes | Trade-offs | Any of 10 rare fields |
|---------------|------:|---:|---:|---:|---:|---:|---:|
| capabilities  |    97 | 97 | 15 |  0 |  0 |  0 | 0 |
| behaviors     |    92 | 16 |  0 |  0 |  0 |  0 | 0 |
| interfaces    |    49 | 20 |  0 |  0 |  0 |  0 | 0 |
| requirements  |    45 |  0 |  0 |  0 |  0 |  0 | 0 |
| components    |    34 | 34 | 11 | 11 | 11 | 11 | 0 |
| layers        |     7 |  7 |  0 |  0 |  0 |  0 | 0 |
| systems       |     4 |  4 |  0 |  0 |  0 |  0 | 0 |
| actors        |     3 |  3 |  3 |  3 |  0 |  0 | 0 |
| constraints   |     2 |  0 |  0 |  0 |  0 |  0 | 0 |
| environments  |     0 |  – |  – |  – |  – |  – | – |
| resources     |     0 |  – |  – |  – |  – |  – | – |

Rare-fields set (10 unused across the entire model): `stakeholders`, `success_criteria`, `assumptions`, `open_questions`, `requirements`, `verification`, `slos`, `owner`, `maturity`, `dependencies_rationale`.

**Coverage headline**: 333 entities × 14 fields = 4,662 cells. Filled: ~226. Effective coverage: **4.8%**.

Note: CONTEXT.md's `29 components | 438 relationships | 122 requirements` claim is stale. Actuals: **34 / 460 / 45 embedded** (plus 201 auto-derived + 53 human-authored in sidecars).

## 2. Ground-truth relationship inventory

Total: **460**. Types present:

| Type          | Count | Notes |
|---------------|------:|-------|
| contains      |   207 | primary hierarchy |
| realizes      |    92 | component ↔ capability |
| satisfies     |    49 | requirement ↔ component/behavior |
| exposes       |    49 | component ↔ interface |
| depends-on    |    30 | component ↔ component |
| traces-to     |    16 | mostly component ↔ behavior |
| triggers      |    13 | behavior ↔ behavior (BEH-P1 chain only) |
| allocated-to  |     4 | very thin |

Types **entirely absent**: `consumes`, `constrained-by`, `produces`, `subscribes-to`, `transforms`, `mounted-on`, `connected-at`, `routed-through`, `supersedes`, `migrates-to`.

- **`consumes` = 0** despite 3 actors × 49 interfaces (actors have no consuming edges).
- **`constrained-by` = 0** — the 2 declared Constraints float unconnected.
- **`produces` = 0** — critical for EXTRACT (BEH-P1.10 emits artifacts) and LOGGING (all four journal writers).

Additional shape drift: three coexisting relationship key conventions (`from_id/to_id/description`, `from_id/to_id`, `from/to`) — canonicalize to `from_id/to_id/description` in Commit 2.

## 3. Requirement store fragmentation

Three parallel stores with three schemas, none conforming to ISO/IEC/IEEE 29148 §5.2.5–5.2.8:

| Store | Location | Count | Priority distribution | Attributes |
|-------|----------|------:|-----------------------|-----------|
| Embedded entities | `.architecture-model.yaml:entities.requirements` | 45 | – | id, name (+ 6 unused 2.1 common fields) |
| Auto-derived      | `.architecture/derived_requirements.yaml`         | 201 | must=4, should=152, could=45 | id, name, category, priority, source_file, source_signal, component_id, evidence |
| Human authored    | `.architecture/requirements.yaml`                 | 53  | – | text, priority, status, created_at, context |

Attributes present across all 254 entries in the sidecars:
- `verification_method` — 0
- `acceptance_criteria` — 0
- `rationale` — 0
- `stakeholder` — 0
- `derived_from` — 0
- `risk` — 0

MoSCoW degeneracy: 76% of derived requirements land in `should` — no meaningful triage.

Category distribution (derived): observability=71, quality=59, technology=38, error_handling=30, interface=3. **Only 3 interface-category requirements exist despite 49 interfaces.**

`REQ-I1` cites `component_id: COMP-3-4` which is not a valid id — should be `COMP-14` (LLM Provider). Similar drift is likely across `derived_requirements.yaml`.

## 4. Standards gap register

### ISO/IEC/IEEE 42010 (Architecture description)

| Concern | Present | Gap |
|---------|:-------:|-----|
| Stakeholders identified | partial (3 actor entities) | No stakeholders on entities; `stakeholders` field 0% |
| Concerns → Viewpoints → Views | implicit via projectors | Views not modeled as first-class entities; no viewpoint→concern mapping |
| Correspondence rules | none | No rules linking model elements to view rendering |
| Architecture rationale | 0 | `trade_offs`, `assumptions` on ~12% of components only |

### ISO/IEC/IEEE 15288 §6.4.2/6.4.3 (Stakeholder needs → System reqs)

- **No stakeholder-need entities.** Requirements jump directly from category (observability/quality) to text.
- **No cascade traceability** — the derivation chain Actor → Need → Requirement → Behavior → Component → Interface → Test is broken at every join.

### ISO/IEC/IEEE 29148 (Requirements)

Required attributes vs. presence:

| Attribute | Present |
|-----------|:-------:|
| identifier | ✅ |
| statement (text/name) | ✅ |
| priority | partial (only in derived + human sidecars) |
| rationale | ❌ |
| source | partial (only in derived sidecar) |
| verification method | ❌ |
| acceptance criteria | ❌ |
| risk | ❌ |
| status | partial (only human sidecar) |
| stakeholder | ❌ |
| version / change history | ❌ |
| dependencies (derives-from / refines) | ❌ |

### INCOSE Handbook v5

- **RTM (Requirements Traceability Matrix)**: `docs/se/artifact_traceability.py` renders a prose join over 3 rel types; no matrix rendered at requirement granularity.
- **V&V matrix**: `docs/se/verification_validation.py` joins Component × test_contract but never touches `REQ-*`. V&V-per-requirement coverage: **0%**.
- **MOEs (Measures of Effectiveness)**: benchmark numbers in CONTEXT.md (`compression 26.4x`, `fidelity 100%`) are not modeled as MOEs on any entity.
- **Requirement quality (RWSEP)**: 100% of `text`/`name` fields ungraded — no INCOSE quality-attribute linting.

### SysML / Arcadia

- **Operational / System / Logical / Physical stratification**: Layers exist (7 declared) but are architectural tiers (web/data/pipeline), not Arcadia phases. No Operational-phase model.
- **`«allocate»` matrix**: `allocated-to` used 4 times only (should be dense across every behavior→component pairing).
- **Ports / flow specifications**: not modeled. Interfaces have no `protocol_spec`, no `provided`/`required` sides.

### FMEA / STPA

- `failure_modes` populated on 11 components only (the 11 top-level root components).
- No hazard entities, no control-actions modeled. STPA-lite framing (unsafe control actions, missing feedback) can be encoded via `failure_modes` + `constrained-by`, but currently isn't.

---

## 5. Per-pipeline dossiers

Each dossier follows the format: **actor → capability → behavior → components → interfaces → constraints → requirements → evidence → identified gaps**.

### 5.1 EXTRACT (Pipeline: `architect_pipeline`, BEH-P1)

**Purpose**: Turn a source-code repo into `.architecture-model.yaml` + per-system decomposition via 10 stages: observe → infer → allocate → relate → specify → contract → validate → decompose → synthesize → emit.

- **Actor(s)**: Developer (partially), no CI actor modeled.
- **Capability**: CAP-3 "Pipeline" with sub-caps CAP-3.1..3.10 (one per stage).
- **Behavior tree**: BEH-P1 root + 11 stage roots (BEH-P1.1..P1.10 + BEH-P1.R for reporter) + 69 sub-behaviors = **81 nodes**.
- **Components realizing**: COMP-2 (Pipeline) + sub-components COMP-2.1..2.5 (Coordination, Observation, Allocation/Relation, Specification/Contract, Synthesis/Emit).
- **Interfaces**: none real — all EXTRACT interfaces are auto-synthesized `IF-auto-COMP-2*` stubs. No ICD exists for the 10 stage-boundary contracts documented at length in CONTEXT.md.
- **Constraints**: 0. CONTEXT.md documents determinism (`AMS_DETERMINISTIC_NOW`), stage-latency ordering, graceful-degradation-on-parse-error — **none modeled as Constraint entities**.
- **Requirements**: several derived reqs land against COMP-2 sub-components but no `satisfies` edge into BEH-P1.* or CAP-3.*.

**Gaps (18 findings, prioritized)**:

| # | Severity | Finding | Remediation commit |
|--:|:-:|-----------------------------------------------------------|:--:|
|  1 | High | 69 sub-behaviors are pure skeletons (id + name only)      | 4  |
|  2 | High | `triggers` DAG only covers stage-to-stage (13 edges); missing sub-behavior ordering within stages | 4 |
|  3 | High | 0 `traces-to` behavior→capability edges (should be ≥81)  | 4  |
|  4 | High | 0 real ICDs; all `IF-auto-COMP-2*` need real `protocol_spec` | 4a+4 |
|  5 | High | 0 Constraint entities for EXTRACT (should have determinism, latency, graceful-degradation) | 4 |
|  6 | Med  | BEH-P1.R (Reporter) has no realizing component allocation | 4  |
|  7 | Med  | BEH-P1.10 "Emit" has no `produces` edges to model/manifest/docs artifacts | 4 |
|  8 | Med  | BEH-P1.9.6 "Collect Lessons" orphaned — no `triggers` into SELF-IMPROVEMENT (BEH-27.1) | 4+7 |
|  9 | Med  | Actor "Developer" has no `consumes` edge to BEH-P1 or `IF-*-cli` | 4 |
| 10 | Med  | CAP-3.1..3.10 have no `intent`/`goals`/`success_criteria` | 4 |
| 11 | Med  | COMP-2.1..2.5 have no `evidence` (SI&L `stage:*` events uncollected) | 10 |
| 12 | Med  | Requirements from derived_requirements.yaml (11 hits in pipeline scope) have no `satisfies` edge to BEH-P1.* | 3 |
| 13 | Low  | No `verification_results` on BEH-P1.* despite 8 stage-related test files under `tests/pipeline/` | 10 |
| 14 | Low  | 74 sub-behaviors lack `description` | 4 |
| 15 | Low  | No `dependencies_rationale` on COMP-2.* despite explicit stage dependency ordering | 4 |
| 16 | Low  | No `assumptions` on BEH-P1.* (e.g., "AST parse succeeds" is a load-bearing assumption) | 4 |
| 17 | Low  | No `open_questions` (recursion depth, cross-system federation) | 4 |
| 18 | Low  | No `owner`/`maturity`/`slos` on any pipeline entity | 4 |

### 5.2 DEV LOOP (BEH-28)

**Purpose**: Iterative developer workflow — run pipeline → view model in `viewer.html` → annotate → curate → regenerate.

- **Actor**: Developer.
- **Capability**: implicit (no dedicated CAP-* for the loop).
- **Behavior tree**: BEH-28 flat (1 node, no children).
- **Components**: allocated to COMP-8 (CLI) only. Real loop spans COMP-2 (pipeline), COMP-4 (docs), COMP-15 (drift), COMP-16 (gates), COMP-17 (test_results).
- **Interfaces**: none for `viewer.html`, none for comment persistence.
- **Constraints**: 0. No session-latency constraint, no comment-durability policy (localStorage vs. CLI-managed sidecar).
- **Requirements**: 0 scoped.

**Gaps (10 findings)**:

| # | Severity | Finding | Commit |
|--:|:-:|--------|:--:|
| 1 | High | No sub-behaviors — should decompose into render-viewer / annotate / persist / regenerate / audit | 5 |
| 2 | High | No `IF-viewer-html`, `IF-comment-localStorage`, `IF-comment-cli` | 5 |
| 3 | High | Allocated to COMP-8 alone — should span COMP-2, COMP-4, COMP-15, COMP-16, COMP-17 | 5 |
| 4 | Med  | No `traces-to` any CAP-* | 5 |
| 5 | Med  | No `produces` edges to `.architecture/viewer-*.yaml`, `.architecture/comments/` | 5 |
| 6 | Med  | No `verification_results` despite 43 comment-persistence tests | 10 |
| 7 | Low  | No requirements linked | 3+5 |
| 8 | Low  | No `failure_modes` (comment loss on localStorage clear, non-deterministic viewer regen) | 5 |
| 9 | Low  | No `slos` (viewer-regeneration budget) | 5 |
| 10 | Low  | Missing description on BEH-28 | 5 |

### 5.3 SLICE (BEH-26 + `architect_slice` MCP tool + `format_model_context`)

**Purpose**: Compress an architecture model into ≤N tokens of dense context for LLM consumption. Backbone of the token-broker value proposition.

- **Actor**: LLM / MCP client.
- **Capability**: CAP-8 "Model Operations" (partial), CAP-2 "Context Formatting" (partial).
- **Behavior tree**: BEH-26 flat.
- **Components**: allocated to COMP-1 (Core) — actual code lives at COMP-1.4 (Model Operations) + `integrations/llm_context.py`.
- **Interfaces**: none for `architect_slice`, none for `format_model_context`.
- **Constraints**: 0. `max_tokens=4000` budget is a load-bearing invariant.
- **Requirements**: REQ-20 (4000-token cap) exists but is not a Constraint entity; no MOE binding compression ratios from CONTEXT.md.

**Gaps (11 findings)**:

| # | Severity | Finding | Commit |
|--:|:-:|--------|:--:|
| 1 | High | Flat behavior — should decompose into select-scope / compute-closure / shared-refs / emit-fragment / compress-to-context | 6 |
| 2 | High | Wrong allocation (COMP-1 vs. COMP-1.4 + integrations submodule) | 6 |
| 3 | High | No Constraint entity for 4000-token cap; enforceable=true, measurable=true | 6 |
| 4 | High | No MOE entity for compression ratio (currently 2.8x – 86x depending on scope) | 6 |
| 5 | Med  | No `IF-slicer-cli`, `IF-architect-slice-mcp`, `IF-format-model-context` | 6 |
| 6 | Med  | No SI&L evidence bound (compression ratio + latency histograms exist as data) | 10 |
| 7 | Med  | No `traces-to` CAP-8 or CAP-2 | 6 |
| 8 | Low  | No `failure_modes` (token overflow, closure explosion) | 6 |
| 9 | Low  | No `slos` (P95 slice latency) | 6 |
| 10 | Low  | No `requirements` scoped in embedded store; must be moved from sidecars | 3+6 |
| 11 | Low  | No `description` on BEH-26 | 6 |

### 5.4 SELF-IMPROVEMENT (BEH-27 + `pipeline/learning` + report cards)

**Purpose**: Pipeline learns from prior runs — pattern classifier, adaptive prompt optimizer, report cards, lesson accumulation, doc-drift maintainer.

- **Actor**: Pipeline (autonomous), Developer (consumes reports).
- **Capability**: CAP-14 "Pipeline Learning" with unlinked sub-caps CAP-14.1..14.5.
- **Behavior tree**: BEH-27 flat.
- **Components**: **incorrectly allocated to COMP-2** — should be COMP-11 "Pipeline Learning". Real code: `pipeline/learning/*.py`, `.architecture/learning/history.json`, `lessons.md`.
- **Interfaces**: none for `history.json`, `lessons.md`, report-card output.
- **Constraints**: 0. Monotonicity constraint (learning curve non-degrading) is documented in CONTEXT.md.
- **Requirements**: 0 scoped despite extensive prose documentation.

**Gaps (12 findings)**:

| # | Severity | Finding | Commit |
|--:|:-:|--------|:--:|
| 1 | High | Wrong allocation (COMP-2 vs. COMP-11) | 7 |
| 2 | High | Flat behavior — decompose into 5: collect-lessons / pattern-classify / apply-heuristics / update-history / report-card | 7 |
| 3 | High | CAP-14.1..14.5 have zero `realizes` edges into BEH-27.* | 7 |
| 4 | High | BEH-P1.9.6 "Collect Lessons" not connected to BEH-27.1 via `triggers` | 7 |
| 5 | Med  | No `IF-learning-history-json`, `IF-lessons-md`, `IF-report-card` | 7 |
| 6 | Med  | No Constraint for monotonicity (learning curve non-degrading) | 7 |
| 7 | Med  | No MOE for compression trend or first-iteration convergence rate | 7 |
| 8 | Med  | No `requirements` derived from CONTEXT.md learning section | 3+7 |
| 9 | Low  | No `failure_modes` (learning collapse, pattern false-positives) | 7 |
| 10 | Low  | No `assumptions` on adaptive rules (thresholds hardcoded) | 7 |
| 11 | Low  | No `open_questions` (multi-repo learning, cross-project transfer) | 7 |
| 12 | Low  | Descriptions missing on CAP-14.1..14.5 | 7 |

### 5.5 LLM PROVIDER (CAP-18 + COMP-14 + `src/architecture_model/ai/`)

**Purpose**: Runtime abstraction over Anthropic / OpenAI / Relay / MCP; policy-driven routing, cost caps, WorkOrder→Proposal→Apply lifecycle, provenance stamping in `meta.provider`.

- **Actor**: MCP client, Frontier LLM (both un-modeled).
- **Capability**: CAP-18 alone — sub-caps missing.
- **Behavior tree**: **empty**. No behaviors model routing, submit, validate, apply.
- **Components**: COMP-14 alone. The entire `src/architecture_model/ai/` package (WorkOrder, Proposals, Jobs, Patch, Validators, Pack) is **invisible in the component graph**.
- **Interfaces**: IF-18 `LLMProvider` Protocol only. No IF for `policy.yaml`, WorkOrder, Proposal, Job, PatchApplication, meta.provider provenance.
- **Constraints**: 0. `max_cost_usd_per_call`, `global_budget_usd`, reproducibility gate (`AMS_DETERMINISTIC_NOW`), `.llm`-suffix contract — all documented, none modeled.
- **Requirements**: REQ-I1 exists but points at stale `COMP-3-4`.

**Gaps (16 findings)** — **highest under-modeling of any pipeline**:

| # | Severity | Finding | Commit |
|--:|:-:|--------|:--:|
| 1 | Critical | Entire `src/architecture_model/ai/` package invisible — promote to COMP-14.1..14.5 | 8 |
| 2 | Critical | Zero behaviors — add BEH-LLM-1 route-by-policy, 2 submit-work-order, 3 validate-proposal, 4 apply-proposal | 8 |
| 3 | Critical | Zero constraints — cost cap, budget, reproducibility, `.llm` suffix | 8 |
| 4 | High | REQ-I1 references nonexistent `COMP-3-4` (should be COMP-14) | 3 |
| 5 | High | No IF for `policy.yaml` (TaskClass, RoutingRule, fallback) | 8 |
| 6 | High | No IF for WorkOrder schema, Proposal schema, Job state machine | 8 |
| 7 | High | No IF for `meta.provider` provenance stamp | 8 |
| 8 | Med  | No `traces-to` from BEH-LLM-* to CAP-18 sub-caps | 8 |
| 9 | Med  | No `consumes` edge from Frontier LLM actor | 8 |
| 10 | Med  | No `produces` edges from BEH-LLM-4 to model deltas | 8 |
| 11 | Med  | No `evidence` binding SI&L `mcp_tool:*` events | 10 |
| 12 | Low  | No `failure_modes` (rate limit, fallback loop, cost breach) | 8 |
| 13 | Low  | No `slos` (P95 route latency) | 8 |
| 14 | Low  | No `open_questions` (streaming, multi-turn) | 8 |
| 15 | Low  | No `assumptions` (provider protocol stability) | 8 |
| 16 | Low  | Descriptions missing on IF-18, CAP-18, COMP-14 | 8 |

### 5.6 LOGGING / OBSERVABILITY (CAP-17 + COMP-13 SI&L + COMP-17 Feedback)

**Purpose**: Component-scoped structural telemetry (SI&L sqlite ring buffer), gate outcomes journal, drift snapshots journal, test results journal, JUnit ingest.

- **Actor**: Pipeline (autonomous), Developer.
- **Capability**: CAP-17.
- **Behavior tree**: **empty**. No behaviors model record-event, rollup-window, append-journal, ingest-junit.
- **Components**: COMP-13 (SI&L) and COMP-17 (Feedback) — no sub-components. Real code: `sil/decorators.py`, `sil/record.py`, `sil/rollup.py`, `feedback/gates.py`, `feedback/drift.py`, `feedback/junit_ingest.py`, `feedback/test_results.py`.
- **Interfaces**: IF-17 (SI&L Store), IF-21 (Gate Journal), IF-22 (Drift Journal). **IF-23 (test_results.jsonl) missing.** No IF for sqlite ring-buffer schema (IF-24), no IF for YAML rollup snapshot (IF-25).
- **Constraints**: 0. 50-event ring-buffer bound, 7-day rollup window, fail-soft append — all invariants, none modeled.
- **Requirements**: 71 observability-category requirements exist in derived sidecar but none scoped to COMP-13/17 sub-behaviors.

**Gaps (14 findings)**:

| # | Severity | Finding | Commit |
|--:|:-:|--------|:--:|
| 1 | Critical | Zero behaviors — add BEH-LOG-1..4 | 9 |
| 2 | Critical | No sub-components — promote to COMP-13.1 (SILStore), 13.2 (SILDecorators), 13.3 (RollupWriter), 17.1 (GateJournal), 17.2 (DriftJournal), 17.3 (TestResultsJournal), 17.4 (JUnitIngester) | 9 |
| 3 | Critical | IF-23 test_results.jsonl missing; IF-24 sqlite schema missing; IF-25 rollup snapshot missing | 9 |
| 4 | High | Zero Constraints (ring-buffer bound, rollup window, fail-soft) | 9 |
| 5 | High | 71 observability-category derived requirements unlinked | 3 |
| 6 | Med  | No `produces` edges from journal writers | 9 |
| 7 | Med  | No `subscribes-to` edges from SI&L decorator consumers | 9 |
| 8 | Med  | No `evidence` — SI&L already has `.architecture/sil.sqlite` populated | 10 |
| 9 | Med  | No `traces-to` from BEH-LOG-* to CAP-17 | 9 |
| 10 | Low  | No `failure_modes` (sqlite corruption, journal truncation, ingest schema mismatch) | 9 |
| 11 | Low  | No `slos` (append latency, rollup delay) | 9 |
| 12 | Low  | No `assumptions` (sqlite WAL journal mode) | 9 |
| 13 | Low  | No `open_questions` (distributed SI&L, retention beyond 50 events) | 9 |
| 14 | Low  | Descriptions missing on CAP-17, COMP-13, COMP-17 | 9 |

---

## 6. Coverage matrix (baseline, pre-remediation)

Percentage of expected fields populated per pipeline scope:

| Pipeline           | Entities in scope | Semantic-field coverage | Requirement traceability | Constraint coverage | Evidence bound | Real interfaces |
|--------------------|------------------:|------------------------:|-------------------------:|--------------------:|---------------:|----------------:|
| EXTRACT            |               ~90 |                     ~5% |                       0% |                  0% |             0% |             0%  |
| DEV LOOP           |               ~10 |                    ~10% |                       0% |                  0% |             0% |             0%  |
| SLICE              |                ~7 |                    ~14% |                       0% |                  0% |             0% |             0%  |
| SELF-IMPROVEMENT   |                ~9 |                    ~11% |                       0% |                  0% |             0% |             0%  |
| LLM PROVIDER       |                ~4 |                    ~25% |                       0% |                  0% |             0% |            ~20% |
| LOGGING            |                ~6 |                    ~17% |                       0% |                  0% |             0% |            ~50% |
| **Global (6 pipelines)** | **~126**   |                    **~9%** |                   **0%** |              **0%** |         **0%** |           **~10%** |

Target after Commit 11: ≥95% semantic-field coverage in scope, 100% description, 100% requirement traceability, ≥90% constraint coverage on load-bearing invariants, 100% evidence-block presence (may be empty dict), 100% real interfaces (zero `IF-auto-*`).

## 7. Standards clause coverage (baseline)

| Clause | Concern | Compliance |
|--------|---------|:----------:|
| 42010 §4.4 | Stakeholders identified | partial |
| 42010 §5.3 | Concerns → Viewpoints | ❌ |
| 42010 §5.4 | Views documented | partial (via projectors, not entities) |
| 42010 §5.5 | Correspondence rules | ❌ |
| 42010 §5.6 | Rationale | ~10% |
| 15288 §6.4.2 | Stakeholder needs | ❌ |
| 15288 §6.4.3 | System requirements | fragmented |
| 29148 §5.2.5 | Requirement attributes (11 required) | 2/11 populated |
| 29148 §6 | Requirement analysis process | ❌ |
| INCOSE v5 Ch.4 | RTM | ❌ |
| INCOSE v5 Ch.9 | V&V matrix at req granularity | ❌ |
| INCOSE v5 App.C | MOE / MOP | ❌ |
| SysML Blocks/Ports | Port modeling | ❌ |
| SysML Allocate | `«allocate»` matrix | 4 edges (nominal) |
| FMEA | failure_modes | ~12% (11/92 behaviors) |
| STPA | Hazards + control actions | ❌ |

## 8. Remediation traceback

Each subsequent commit closes a subset of the findings above.

| Commit | Closes findings |
|--------|-----------------|
| 2 (schema 2.2) | enables 29148 §5.2.5 attrs, adds `description` slot, enables `sub_model_ref`, adds `PRODUCES`/`SUBSCRIBES_TO`/`CONSTRAINED_BY`/`CONSUMES` relationship types |
| 3 (requirements) | consolidates 3 stores, populates 29148 attrs, builds RTM, fixes REQ-I1 stale ref |
| 4a (interface synth) | eliminates `IF-auto-*` for endpoint-bearing modules |
| 4 (EXTRACT) | 18 findings in §5.1 |
| 5 (DEV LOOP) | 10 findings in §5.2 |
| 6 (SLICE) | 11 findings in §5.3 |
| 7 (SELF-IMPROVEMENT) | 12 findings in §5.4 |
| 8 (LLM PROVIDER) | 16 findings in §5.5 |
| 9 (LOGGING) | 14 findings in §5.6 |
| 10 (evidence binding) | all "no evidence bound" findings + all "no verification_results" findings + view descriptions |
| 11 (cleanup + CONTEXT + audit) | stale sidecar removal, artifact consumer scan, CONTEXT refresh, automated regression harness |

## 9. Success criteria (measured by `tests/test_completeness_audit.py`, added Commit 11)

For every entity in the six-pipeline scope:

1. `description` present, ≤200 chars.
2. ≥95% of 14 schema-2.2 common semantic fields populated.
3. Components carry `evidence` block (may be empty dict).
4. Behaviors carry `verification_results` list.
5. Requirements carry `verification_method`, `acceptance_criteria`, `rationale`, `stakeholder`.
6. No `IF-auto-*` interface ids remain.
7. Relationship shape uniform: `from_id` / `to_id` / `description`.
8. Zero orphans in BEH-P1 subtree.
9. Every generated page / diagram / SE doc carries a description.
10. RTM renders at requirement granularity with test-outcome linkage.

## 10. Non-goals (this pass)

- Non-six-pipeline entities remain untouched (~30% of model).
- SysML XMI export.
- STPA hazard analysis beyond `failure_modes` framing.
- Auto-derivation of stakeholder needs from git history / commit archaeology.
- Multi-repo federated learning (deferred to future phase).
