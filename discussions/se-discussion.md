# Architecture Model Standard — Systems Engineering Alignment
## Design Decisions, Requirements, Planning & Improvements

**Status:** Draft for review
**Scope:** architecture-model-standard (schema v2.0 → proposed v2.1)
**Purpose:** Formalize the model ontology to support both (a) SE-style forward development/documentation and (b) reverse-engineering of existing systems, using a single unified schema.

---

## 1. Context & Motivation

The architecture model schema (v2.0) was built primarily to support **reverse engineering**: `architect_scan` → `architect_extract` walks up from AST facts (functions, imports, test assertions) to infer Capabilities, Actors, Behaviors, and Components. This "right leg" of the classic Systems Engineering **Vee model** is mature and heavily benchmarked (see §6).

The **left leg** — forward development driven by requirements, functional decomposition, and allocation — is largely unsupported today. The schema has the *types* to support it (Constraint, Decision, Lifecycle, QualityAttribute, Resource, Environment all exist in `core/types.py`) but lacks the *relationships* and *pipeline support* to populate and use them meaningfully.

**Goal:** Close this gap without breaking the existing reverse-engineering pipeline or its benchmarked regen capability.

```
DEVELOPMENT (left leg, top-down)          REVERSE ENGINEERING (right leg, bottom-up)
─────────────────────────────             ─────────────────────────────
Mission/Need          → Actor              Actor                 ← inferred from routes/imports
Requirements          → Constraint         Constraint            ← inferred from test_contracts (implicit)
Functional Arch        → Capability         Capability            ← inferred from f_block clustering
Physical Arch          → Component          Component             ← extracted from manifest modules
Interface Design       → Interface          Interface             ← derived from cross-block imports
Detailed Design        → Behavior/steps     Behavior              ← detected via AST (service/route scan)
                          ↓ build                    ↑ verify
                       [ CODE ]         ←────────  [ CODE ]
```

---

## 2. Current Ontology (Baseline — Schema v2.0)

### 2.1 Core entity types (7, per CONTEXT.md)
Actors, Capabilities, Behaviors, Interfaces, Constraints, Layers, Components.

### 2.2 Expanded entity types (15, per `core/types.py`)
Adds: System, Data, Event, Resource, Environment, QualityAttribute, Decision, Lifecycle.

**Finding:** None of the 8 "expanded" types (Decision, Lifecycle, QualityAttribute, Resource, Environment, Event, Data, System*) appear populated in any exported model except System. This strongly suggests the schema was designed with SE parity in mind but the code-first extraction pipeline never needed to populate them — a human doing forward development and documenting rationale is the only path that would.

*System is the exception — it is machine-derived via complexity scoring (§2.4), not manually authored.

### 2.3 Relationship types (17)
`realizes`, `contains`, `depends-on`, `exposes`, `consumes`, `traces-to`, `allocated-to`, `constrained-by`, `triggers`, `mounted-on`, `connected-at`, `routed-through`, `produces`, `subscribes-to`, `transforms`, `supersedes`, `migrates-to`.

### 2.4 Entity decomposition summary

| Entity | Decomposes? | Mechanism | Terminal unit |
|---|---|---|---|
| Capability | Yes | `contains` (Cap→Cap) | realized by Component |
| Behavior | Yes | `contains` + `steps` + sub-models | per-behavior sub-model |
| Component | Yes (both directions) | files→signatures (down) / cluster→System (up) | function/symbol level |
| System | Yes | derived from Component clustering (`identify_systems`, threshold = 10.0) | own sub-model of Components |
| F-block | Yes | directory recursion (`sub_blocks`, max_depth=3) | leaf directory |
| Interface | No | — | atomic |
| Constraint | **Legal but unused** | `contains` is schema-valid; zero populated instances | atomic in practice today |
| Actor | No | — | atomic |
| Layer | No | — | atomic |

### 2.5 F-block vs. Capability vs. Component vs. System — clarified

| Concept | Question answered | Entity type? | Driven by |
|---|---|---|---|
| F-block | Where does the code physically live? | No — config/grouping label | Directory scan (`architecture-model init`) |
| Capability | What can the system do? | Yes | Semantic modeling |
| Component | What concrete module implements it? | Yes | Semantic modeling + manifest |
| System | Is this cluster complex enough to warrant its own model? | Yes | Computed (`compute_complexity` ≥ threshold) |

**Key finding:** F-block is misnamed relative to SE usage. In SE, a "functional block" is purpose-defined and implementation-agnostic. In this schema, F-block is a directory/packaging artifact with no behavioral content — **Capability is the entity actually doing SE "functional block" duty.**

---

## 3. Design Decision: F-Block Rename

### 3.1 Problem
`f_block` collides conceptually with SE's "functional block" terminology while behaving like a physical/packaging construct. This creates persistent confusion when mapping this ontology onto SE methodology.

### 3.2 Decision (proposed, not yet adopted)
Rename `f_block` → **`package_block`** (or `source_block` / `module_cluster` as fallbacks), IDs `P1`, `P2`, ... replacing `F1`, `F2`, ...

**Rationale:** Matches SE's actual "physical block / package" concept — a cluster of implementation elements grouped by *location*, not *purpose*. Frees "functional block" terminology to correctly refer to Capability going forward, in any documentation that draws SE parallels.

### 3.3 Scope of change (mechanical rename, not semantic)
- `f_block` field on Capability, Component (schema + JSON Schema + `core/types.py`)
- `config.fblock_dict`, `fblock_dir_map` (config/loader.py, config/schema.py)
- `F1`/`F2`... ID convention across manifests, sub-models, CLI output
- `identify_systems()` grouping key
- CLI `--fblock` flag (`architecture-model slice --fblock`)
- Generated docs (`dependency_matrix.md`, diagrams, behavior index)

**Status:** Not started. Recommend scoping as a standalone migration PR — mechanical, low semantic risk, but wide surface area.

---

## 4. Design Decision: Requirements Decomposition & Verification Traceability (Track A)

### 4.1 Problem
Constraints today are atomic — no parent/child structure, no link back to the `test_contracts` that already implicitly verify them. SE requirements elicitation expects:
- **Derivation** — child requirements refine a parent (same intent, narrower scope)
- **Allocation** — a requirement's budget is split across implementing elements
- **Verification** — evidence (tests) that a requirement is satisfied
- **Validation** — confirmation the *right* requirement was built (traces to Actor/mission need, not just Constraint)

None of these are currently distinguishable in the schema. `constrained-by` only expresses "this entity is governed by this constraint" — a single undifferentiated edge doing multiple jobs.

### 4.2 Decision: Add two relationship types, widen one

| Type | From → To | SE meaning | Status |
|---|---|---|---|
| `derives-from` | Constraint → Constraint | Child requirement refines parent | **New** (18th → distinct from generic `contains`) |
| `verifies` | test_contract → Constraint | Evidence requirement is satisfied | **New** — the V&V closure edge |
| `allocated-to` (widened) | Constraint → Component (in addition to existing Component → Layer) | Requirement budget allocation | **Widened**, not new |

No new entity types required — this only wires up existing but unused schema surface.

### 4.3 Decision: New validator check (11th)

```
_check_requirements_verification(model, result)
```
- For every leaf Constraint (no outgoing `derives-from` children): require ≥1 `verifies` edge from a test_contract
- Mirrors `_check_capability_realization`'s existing pattern (same shape: requirement-coverage instead of functional-coverage)
- Severity: **WARNING**, not ERROR — many constraints are structural/design decisions, not test-provable claims

### 4.4 Worked example (illustrative, not yet applied to real models)

```yaml
- id: CON-ROUND-TRIP
  name: Round-Trip Fidelity
  # existing parent constraint, unchanged

- id: CON-ROUND-TRIP-META
  name: Meta Fields Round-Trip
  description: All ModelMeta fields survive serialize/deserialize

- id: CON-ROUND-TRIP-RELS
  name: Relationships Round-Trip
  description: Relationship set is order-independent-equal after round-trip

relationships:
- {from: CON-ROUND-TRIP, to: CON-ROUND-TRIP-META, type: derives-from}
- {from: CON-ROUND-TRIP, to: CON-ROUND-TRIP-RELS, type: derives-from}
```

This maps almost 1:1 onto existing `test_parser.py` test_contracts (`test_round_trip_preserves_meta`, `test_round_trip_preserves_relationship_count`, `test_round_trip_preserves_actor_ids`, ...) — strong evidence the granularity is real and already implicit in test naming, just currently uncaptured in the model.

### 4.5 V&V loop, formalized

Splits the currently-conflated "test_contracts on Component" into two independently checkable SE claims:

```
Actor (need)
  └─ triggers → Behavior          [VALIDATION: does behavior serve the actor's need?]
                  └─ traces-to → Component
                                    └─ has → test_contracts
                                                └─ verifies → Constraint  [VERIFICATION: does it meet the requirement?]
```

### 4.6 Important caveat
`test_contracts` currently live on `Component`, populated via `enrich_from_manifest` → `_enrich_test_contracts` → `analyze_test_file`. This pipeline has **no existing connection to Constraint** — Constraints and test_contracts are unconnected subgraphs today. The `verifies` edge is genuinely new wiring, not a relabeling of something that already flows.

---

## 5. Design Decision: Forward-Authoring Path (Track B — larger effort, deferred)

### 5.1 Problem
`architect_extract` is currently the *only* path to a populated model. There is no way to author Constraints/Capabilities first and have Components validated against them as they're built — i.e., no genuine SE "develop top-down" workflow.

### 5.2 Proposed direction (not scoped in detail yet)
- New CLI path (`architecture-model author` or similar) that scaffolds Capability→Component allocation starting from author-provided Constraints/Actors
- Reuse `architect_check`'s existing `file_coverage` / `relationship_accuracy` scoring, but as a **live development gate** rather than a **post-hoc drift detector**
- Wire up `Decision` (trade studies: `proposed`/`accepted`/`superseded`, needs a `resolves → Constraint` and `affects → Component` relationship) and `Lifecycle` (phase-gated validation — e.g., a Component in `concept` phase shouldn't fail `_check_regen_readiness` for missing signatures, but one in `production` should)

**Status:** Deferred pending Track A validation. Track A is schema-only and lower-risk; Track B requires new pipeline/CLI surface.

---

## 6. Regeneration Capability — Current State (Benchmark Baseline)

Regen is the most mature, most rigorously tested capability in the system and is the proposed proving ground for Track A.

### 6.1 Blind regeneration results (model-only, agent never reads source/test files)

| Repo | Testable subsystems | Converged | Fidelity | Avg iterations | Time |
|---|:---:|:---:|:---:|:---:|:---:|
| colorama | 4 | 4/4 | **100%** | 1.0 | ~5m |
| structlog | 13 | 13/13 | **100%** | 1.0 | ~25m |
| tqdm | 10 | 10/10 | **100%** | 1.0 | ~20m |
| click | 8 | 8/8 | **100%** | 1.0 | ~30m |
| **Total** | **35** | **35/35** | **100%** | **1.0** | **~80m** |

34/35 subsystems converged on first attempt (97% first-iteration success).

### 6.2 What drives fidelity
- **Plain (non-enriched) models score 0% test pass rate** — architecture alone is insufficient
- What matters: `body_hint` (exact source for trivial functions), module-level constants, `test_contracts` with exact expected outputs
- **Regen is fundamentally test_contracts-driven, not architecture-driven**

### 6.3 Token economics
Compression scales with repo size: 2.8x (colorama, 10K tokens) → 26.4x average / up to 85.8x per-subsystem (click, 105K tokens). Compression benefit is dependency-driven — subsystems with many upstream dependencies benefit most.

### 6.4 Implication for Track A
Since regen is already at ceiling (100% fidelity, 1.0 avg iterations) on all four benchmarks, **there is no headroom to demonstrate improvement** via added Constraint/verifies structure — any test must be framed as a **regression check** (does fidelity hold, does prompt size change) rather than an improvement demo.

---

## 7. Formalized Plan — Phased Rollout

| Phase | Deliverable | Success criterion |
|---|---|---|
| **1 — Schema** | Add `derives-from`, `verifies`; widen `allocated-to` in JSON Schema + `core/types.py` `RelationType` enum | `architect_validate` still passes on all existing models unmodified (additive, backward-compatible) |
| **2 — Retrofit colorama** | Manually decompose 3–5 Constraints into child Constraints; wire `verifies` from colorama's existing `test_contracts` | Confirms mapping is mechanical (test names already imply the constraint tree) |
| **3 — Validator check** | Ship `_check_requirements_verification`; run against colorama's enriched model | Establish baseline requirement-coverage % |
| **4 — Regen regression** | Re-run blind regen on colorama with Constraint tree included in agent context | Fidelity holds at 100%/1.0 iterations (a drop = added context is noise; holding steady at smaller prompt = win) |
| **5 — Scale out** | Repeat phases 2–4 on structlog, tqdm, click if colorama validates | Full 4-repo parity with existing E2E benchmark table |

**Why colorama first:** Smallest benchmark (4 subsystems, 10K source tokens), already at 100%/1.0 with no adaptive-prompt/retry machinery engaged (unlike tqdm/click, which needed dependency-context expansion and contract-cap increases). Any signal from added structure will be cleanly attributable.

---

## 8. Open Questions / Not Yet Decided

1. **F-block rename** — which name wins (`package_block` vs. `source_block` vs. `module_cluster`)? Needs a decision before scoping the migration.
2. **`verifies` cardinality** — can one test_contract verify multiple Constraints? Can one Constraint have zero verifying tests and still be valid (e.g., purely structural constraints)? Current proposal treats missing verification as WARNING, not ERROR — confirm this is the right severity.
3. **Track B scope** — is `architecture-model author` a CLI addition, a new MCP tool, or both? Needs a separate scoping pass once Track A lands.
4. **Decision/Lifecycle wiring** — do we need `Decision --resolves--> Constraint` and `Decision --affects--> Component` as two new relationship types, or can existing `constrained-by`/`traces-to` be reused with a documented convention? Leaning toward new types for clarity but not yet decided.
5. **Validation vs. Verification split enforcement** — should `_check_requirements_verification` also check the Actor→Behavior "validation" leg, or is that a separate 12th check? Currently scoped as verification-only.

---

## 9. Summary Table — All Proposed Changes

| Change | Type | Effort | Risk | Status |
|---|---|---|---|---|
| Rename `f_block` → `package_block` | Rename (mechanical) | Medium (wide surface) | Low (no semantic change) | Proposed, not started |
| Add `derives-from` relationship type | Schema addition | Small | Low (additive) | Proposed |
| Add `verifies` relationship type | Schema addition | Small | Low (additive) | Proposed |
| Widen `allocated-to` (Constraint→Component) | Schema widening | Small | Low (additive) | Proposed |
| `_check_requirements_verification` validator | New validator check | Small | Low (WARNING-only) | Proposed |
| Colorama Constraint retrofit | Data/content work | Small | None (test repo) | Proposed (Phase 2) |
| Regen regression test w/ Constraint context | Evaluation | Small | None (read-only test) | Proposed (Phase 4) |
| Forward-authoring CLI path (Track B) | New pipeline/CLI | Large | Medium (new surface) | Deferred |
| Decision/Lifecycle wiring | Schema + pipeline | Medium | Medium | Deferred (part of Track B) |

---

*Document reflects design discussion as of this session. Nothing described here has been implemented in the codebase yet — all items in §3, §4, §5, and §7 are proposals pending review and prioritization.*
