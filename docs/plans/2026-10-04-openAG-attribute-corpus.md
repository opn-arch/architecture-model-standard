# openAG — Attribute Corpus & Provenance Ledger (Generation 0)

**Status:** Provenance synthesis. Companion to
`2026-10-04-openAG-entity-model.md` (the ~100-entity gen-0 ledger this doc
populates), `2026-10-04-openAG-graph-native-engine-design.md`, and
`2026-10-04-openAG-pipelines.md`.
**Date:** 2026-10-04

> **Revision 2026-10-12 (session ledger fold-in).** Two locks propagated
> into the corpus method: (1) the status model is now **four end-states**
> — verified-promise / reservoir(open) / **plain-attribute** / typed-gap
> — where *plain attribute* (non-verifiable prose, retained-but-untracked)
> is a **legitimate terminal non-gap**, only `typed-gap` is a gap (§0.2a);
> (2) **risk is intrinsic** to every promise and collapses into VoI — a
> corpus *view*, not a stored attribute (§0.6).

---

## §0. Method

This document **populates the attribute-promises of every gen-0 openAG
entity from prior work**, so that none of the ~4 years of effort embodied
in AMS (architecture-model-standard), its v3 model, its delivery history,
and its real-repo benchmark campaign is lost when openAG is seeded. It is
**provenance**, not new design: every cell points backward to a source, or
is declared an honest gap.

### §0.1 What was harvested (5 parallel sweeps)

| # | Sweep | Primary sources |
|---|---|---|
| H1 | **v3 promise index** | 4 `.architecture/model/*.v3.yaml` files — 246 PromiseSpec records, verbatim lessons L1–L22, open/gap list (39) |
| H2 | **component attributes** | `.architecture-model.yaml` self-model (COMP-1..17), `enrichment.v3.yaml`, schema `$defs` (`src/architecture_model/spec/schema.json`, `promise-graph.schema.json`) |
| H3 | **discussion rationale** | `.architecture/devlog.jsonl` (LOG-0021..0089), design docs §7/§8/§10, plan docs — ~14 decisions |
| H4 | **delivery evidence** | 835 commits; `component_test_map.json`/`test_map.json`; `metrics.json`; `validation.json`; CONTEXT.md Parts 1–17 |
| H5 | **testing & real-world** | CONTEXT.md E2E Benchmarks + Blind Regen + Token Economics + Learning Loop; `projects/django`+`projects/textual` (38 `lessons.md`); `.architecture/learning/history.json` |

### §0.2 Status model (three honest tiers)

| status | admitted when | axis-of-evidence |
|---|---|---|
| **verified** | a prior v3 promise is already `status: verified`, **OR** delivery/testing evidence (tests, benchmark, commit, journal) backs the claim | A7 runtime/observational |
| **delivered** | design-rationale / discussion backs the claim but no runtime evidence yet (design-only tier, cf. L14), **OR** it is a **reservoir** item (content exists, owner is a lower-level entity not yet in gen-0) | A7 design / A1↓ pending |
| **typed-gap** | nothing in any source — emitted as `gap:<class>` per entity-model §10, never hallucinated | — |

> **Reservoir vs gap (user-locked distinction).** A *reservoir* promise has
> real sourced content but **no gen-0 owner** — it is tagged
> `status: delivered`, `axis: A1↓`, and carries `flows-to:<lower-level area>`.
> A *typed-gap* has **no content anywhere**. Reservoir ≠ gap.

### §0.2a Four end-states (user-locked)

The three-tier *status* above (verified / delivered / typed-gap) is the
**sourcing** axis. Orthogonal to it is the **valence** axis — whether an
attribute is *verifiable at all*. Crossing them yields the **four terminal
end-states** every attribute resolves to:

| end-state | verifiable? | sourced? | is it a gap? | meaning |
|---|---|---|---|---|
| **verified promise** | yes | yes, grounded | no | discharged against A7 evidence |
| **reservoir (open)** | yes | content exists, no owner | no (yet) | promised, awaiting lower-level owner (`axis: A1↓`) |
| **plain attribute** | **no** (non-verifiable prose) | yes | **no — legitimate terminal non-gap** | retained-but-untracked descriptive text; never schedules, never a gap |
| **typed-gap** | yes | **nothing anywhere** | **yes — the only gap** | emitted as `gap:<class>` |

> **Valence floor = a declarative type-signature, not a schedule.** `grow`
> *proposes* content above the floor into the **reservoir**; `ground`
> *promotes* only what verifies to **verified**. What is inherently
> non-verifiable settles as a **plain attribute** — it is kept as prose but
> never tracked as an open promise and never counted as a gap. A reservoir
> item crosses to an owner via **θ-crosswalk by content σ**
> (`reconcile` + σ). **Only `typed-gap` is a gap.**

### §0.6 Risk is intrinsic — a corpus view, not an attribute

Every promise carries a latent **risk = P(won't ground) × consequence**.
This is **not** a stored attribute and **not** a new entity: it collapses
into the existing VoI machinery — `consequence` is the *value* term,
`P(won't ground)` is the *confidence* term (§0.2 status/axis-of-evidence
already supplies both). The **risk register is therefore a VIEW** over the
§13 gap register sorted by consequence, surfaced at gate L2. No corpus row
gains a `risk:` cell; risk is *read* from the promise's existing
value/confidence provenance.

### §0.3 Typed provenance tags (on every citation)

`[model]` v3 `.v3.yaml` promise · `[schema]` JSON-Schema `$defs` ·
`[report]` `docs/reports/*` · `[plan]` `docs/plans/*` · `[context]`
CONTEXT.md · `[discussion]` devlog / design rationale · `[delivery]`
commit / test-map / metrics · `[testing]` benchmark / real-repo lessons.

### §0.4 Promise row shape

Each row: **`attribute · content · status · axis · valence · verified_by · provenance`**.
`axis ∈ {A1 Abstraction, A2 Realization, A3 Boundary, A4 Governance,
A5 Flow, A6 Lifecycle, A7 Evidence}`. `valence` = the per-kind rule
(entity-model §0 / design §4.1) that *demanded* the promise.

### §0.5 The locked correction (CAP-mdd is not zero-source)

`CAP-mdd` / `COMP-CodeGenerator` / `COMP-ParityChecker` are **evidence-backed**
by the blind-regeneration, test-oracle, and parity benchmark campaign
(CONTEXT.md). They are *not* zero-source. The **genuinely net-new residue**
(no prior source anywhere) is the fixpoint-kernel internals —
`ExpanderRegistry`, `Grounder`, `Reconciler`, `IdentityStore`,
`SeedStrategy`, the `axis`/`valence` promise fields — plus the `CON-N2`
NN-compilability constraint.

---

## §1. Source index

| source | path | what it grounds |
|---|---|---|
| v3 capabilities | `.architecture/model/capabilities.v3.yaml` | 120 promises — CAP-PB, CAP-DF, CAP-WK, behaviors, interfaces |
| v3 pipelines | `.architecture/model/pipelines.v3.yaml` | 84 promises — BEH-P1 (10-stage), BEH-26/27/28, BEH-LLM/SIL/FBK |
| v3 enrichment | `.architecture/model/enrichment.v3.yaml` | 26 promises — COMP-c5a72728, COMP-VIEWER, actors, constraints, layers |
| v3 viewer | `.architecture/model/viewer.v3.yaml` | 16 promises — COMP-VIEWER delivers/provides |
| self-model | `.architecture-model.yaml` | COMP-1..17 component boundaries, 438 relationships, 90/100 validator |
| schema | `src/architecture_model/spec/{schema.json, promise-graph.schema.json}` | attribute `$defs`, PromiseStatus enum, open-schema `attribute` |
| scratch index | `.architecture/scratch/v3-promise-index.md` | full H1 per-entity tables (958 lines) |
| benchmarks | CONTEXT.md §E2E / §Blind Regen / §Token Economics | extraction 98/100, blind 35/35 @100%, compression 85.8× |
| learning curve | `.architecture/learning/history.json` | per-stage score trend (infer 69, validate 0→90, allocate 100→78) |
| real-repo lessons | `projects/{django,textual}/**/lessons.md` (38 files) | 1030 ambiguous-module + 308 complex-behavior, all on infer |
| devlog | `.architecture/devlog.jsonl` | LOG-0021..0089 design decisions |
| lessons L1–L22 | `capabilities.v3.yaml` CAP-DF `lessons_learned` | design rationale (L6→L18, L11→L19, L16 RESOLVED) |

---

## §2. System — SYS-openAG

| attribute | content | status | axis | valence | verified_by | provenance |
|---|---|---|---|---|---|---|
| intent | Sustain a verified architecture graph of a target system by promise-discharge (F0). | delivered | A1 | system node-local | design §1 mission statement | `[plan]` entity-model §1 |
| success_criteria | Least-fixpoint reached: every node either grounded (A7 evidence) or carrying an explicit typed-gap; zero silent omissions. | delivered | A7 | system node-local | design invariant #5 gap-honesty | `[plan]` design §invariants `[discussion]` L13 loop pattern |
| top-constraints | Governed by CON-existence, CON-prohibition, CON-parametric, CON-pure-state, CON-N2. | delivered | A4 | `→CON-*` governance | entity-model §7.3 | `[plan]` entity-model §7.3 |
| health | Σ capability health rolled up A1↑ from the 5 L1 capabilities. | delivered | A1↑ | roll-up | rollup is CAP-WK contract-composition (L18) | `[model]` CAP-WK requirements `[plan]` entity-model §1 |

---

## §3. Capabilities (5)

### CAP-extract — extract
Crosswalk ← AMS **CAP-PB** (`extract_architecture_from_code`) + 10-stage **BEH-P1**.

| attribute | content | status | axis | valence | verified_by | provenance |
|---|---|---|---|---|---|---|
| intent | Produce seed nodes + grounded facts from a target's source via pure AST analysis, deterministically, no LLM. | **verified** | A1 | cap node-local | `pipeline_v3.orchestrator.run_pipeline` emits model end-to-end (25 comp / 664 promises / 50 edges) | `[model]` CAP-PB intent `[context]` self-run |
| success_criteria | Byte-identical output across reruns (pinned clock); ≥1 component per non-empty root; schema-valid; decompose reaches fixed point. | **verified** | A7 | cap success-criteria | Phase 8 byte-determinism gate; `tests/pipeline_v3/` | `[model]` CAP-PB success_criteria `[delivery]` 4351 tests passed |
| requirements | Deterministic AST-only; stage-composable; resumable via disk cache; emit schema-compatible YAML. | **verified** | A2 | cap requirements | `tests/pipeline_v3/`; `promise-graph.schema.json` validates output | `[model]` CAP-PB requirements |
| owner | Substrate+Kernel layer; forks `pipeline_v3`. | **verified** | A4 | cap owner | self-model COMP-2 (Pipeline) + pipeline_v3 package | `[model]` `[delivery]` pipeline 203 tests |
| realizes | SourceScanner, PatternDetector, Seeder. | **verified** | A2 | ≥1 realizes | entity-model §4.1 | `[plan]` entity-model §2 |
| realization-coverage | Rolled up from scan/detect/seed children. | delivered | A1↑ | roll-up | CAP-WK.unrealized-cap rollup | `[model]` CAP-WK.unrealized-cap |
| slos | byte-determinism=100% (gated); module coverage ≥95%; <10s typical. | **verified** | A7 | cap slo | CI byte-determinism gate | `[model]` CAP-PB slos |
| failure_modes | import cycles hide edge direction; name-prefix mis-clusters siblings; publish overwrites wholesale; dynamic imports invisible to AST. | **verified** | A7 | cap failure-mode | PR-BEH-publish-failure_modes; real-repo 1030 ambiguous-module on infer | `[model]` CAP-PB failure_modes `[testing]` django/textual lessons |
| open_questions | Should the 8 pipeline_v3 modules split from single COMP into 8 per-stage components (per-stage SI&L/validation)? | delivered | A1↓ | open-question | — (Part-3 candidate) | `[model]` CAP-PB open_questions (gap:deferred-split) |

### CAP-model — model
Crosswalk ← AMS **CAP-DF** (evolve loop) + **CAP-WK** (walk substrate) + **BEH-P1** stages. **Fixpoint semantics are net-new.**

| attribute | content | status | axis | valence | verified_by | provenance |
|---|---|---|---|---|---|---|
| intent | Grow the graph to least-fixpoint by discharging open promises along their axes. | delivered | A1 | cap node-local | design §operator; CAP-DF intent (view→note→walk→validate→re-extract) is the closest prior loop | `[plan]` design §3 `[model]` CAP-DF intent |
| success_criteria | Fixpoint reached modulo budget; confluent reconcile; every discharge grounded or typed-gap. | delivered | A7 | cap success-criteria | design confluence-modulo-budget | `[plan]` design §operator |
| requirements | Substrate exposes Stage/Pipeline/ContentCache/silent-skip; kind+predicate selection; attribute-category-aware rollup (A=union,B=conjunction,C=contract). | **verified** | A2 | cap requirements | `src/architecture_model/walks/`, `pipeline_v3/substrate/` | `[model]` CAP-WK requirements |
| owner | Kernel layer (13 model components). | **verified** | A4 | cap owner | self-model COMP-2; walks/ package | `[model]` `[delivery]` |
| realizes | ExpansionKernel + 12 model-layer components. | delivered | A2 | ≥1 realizes | entity-model §4.2 | `[plan]` entity-model §2 |
| SLO | Rolls down A1↓ to sub-cap SLOs (grow/ground/gate/reconcile/govern/remember/traverse). | delivered | A1↓ | SLO decomposition | — | `[plan]` entity-model §2 |
| goals | Reduce a new walk from ~60 LOC Python to ~20 lines YAML; declarative rollup; meta-auditable walks. | delivered | A1 | cap goal | CAP-WK goals (status: proposed) | `[model]` CAP-WK goals |

### CAP-represent — represent
Crosswalk ← AMS **CAP-SL** (slice) + lifecycle substrate (BEH-26, Phases 1–5) + **COMP-VIEWER**.

| attribute | content | status | axis | valence | verified_by | provenance |
|---|---|---|---|---|---|---|
| intent | Materialize, project, and render any owned view/artifact from the graph. | **verified** | A1 | cap node-local | CAP-SL intent; lifecycle `ModelSlice→materialize→project→render→rebuild` substrate | `[model]` CAP-SL intent `[context]` Phase 1 substrate |
| success_criteria | Fragment digest stable across identical slice calls; zero broken cross-refs; byte-identical render. | **verified** | A7 | cap success-criteria | `tests/test_slicer.py`, `tests/lifecycle/test_overlay_determinism.py` | `[model]` BEH-26 success_criteria `[delivery]` lifecycle 227 tests |
| requirements | Respect token budget without silent truncation; no dangling refs after closure; deterministic bytes. | **verified** | A2 | cap requirements | `tests/test_slicer.py` | `[model]` BEH-26 requirements |
| owner | Projection layer (Slicer, ProjectorRegistry, Renderers, Viewer). | **verified** | A4 | cap owner | self-model COMP-4 (Documentation) + lifecycle | `[model]` `[delivery]` |
| realizes | Slicer, ProjectorRegistry, Renderers, Viewer. | **verified** | A2 | ≥1 realizes | entity-model §4.3 | `[plan]` entity-model §2 |

### CAP-learn — learn
Crosswalk ← AMS **BEH-27** (learn-across-runs) + **BEH-FBK** (feedback journals) + Learning Loop (CONTEXT.md).

| attribute | content | status | axis | valence | verified_by | provenance |
|---|---|---|---|---|---|---|
| intent | Observe outcomes, distill lessons, tune the rules that drive discharge. | **verified** | A1 | cap node-local | BEH-27 intent; `pipeline/lessons.py`, `learning.py`, `global_learning.py` | `[model]` BEH-27 intent |
| success_criteria | Pattern hit-rate trending up; regen-readiness grade improving/stable; zero learning-curve oscillation. | delivered | A7 | cap success-criteria | BEH-27 success_criteria (status: open) | `[model]` BEH-27 (gap:unverified) `[testing]` learning-curve 2.8→26.4× |
| requirements | Persist lessons to `learning/history.json`; dedup by content-hash; apply at stage entry not emit. | **verified** | A2 | cap requirements | `pipeline/history.py` | `[model]` BEH-27 requirements |
| owner | Adaptation layer (FeedbackJournals, LessonStore, RuleTuner). | **verified** | A4 | cap owner | self-model COMP-3-12 (feedback), BEH-FBK | `[model]` `[delivery]` |
| realizes | FeedbackJournals, LessonStore, RuleTuner. | **verified** | A2 | ≥1 realizes | entity-model §4.4 | `[plan]` entity-model §2 |
| failure_modes | infer stage is chronically weak (score 69); allocate regressed 100→78; 1030 ambiguous-module instances unlearned. | **verified** | A7 | cap failure-mode | `.architecture/learning/history.json`; 38 real-repo lessons.md | `[testing]` learning curve + django/textual |

### CAP-mdd — mdd
Crosswalk ← **blind-regen / test-oracle / parity benchmark campaign** (CONTEXT.md). **NOT zero-source** (locked correction §0.5).

| attribute | content | status | axis | valence | verified_by | provenance |
|---|---|---|---|---|---|---|
| intent | Model-driven code generation + behavioral parity verification against an oracle. | **verified** | A1 | cap node-local | blind regen: enriched model alone regenerates passing code for 35/35 subsystems | `[context]` Blind Regen §; `[testing]` |
| success_criteria | Blind (model-only) regen converges 100% fidelity, 1.0 avg iterations, zero source/test reads. | **verified** | A7 | cap success-criteria | colorama 4/4, structlog 13/13, tqdm 10/10, click 8/8 = 35/35 @100% | `[context]` Blind Regen FINAL RESULTS `[testing]` |
| requirements | body_hints + constants + test_contracts suffice as lossless behavioral representation; oracle-in-loop. | **verified** | A2 | cap requirements | 34/35 converge first attempt; structlog.processors 91%→100% blind-beats-normal | `[context]` “What made it work” |
| owner | mdd layer (CodeGenerator, ParityChecker). | **verified** | A4 | cap owner | `quality/code_improver.py`; arch-agent benchmark harness | `[delivery]` `[context]` |
| realizes | CodeGenerator, ParityChecker. | **verified** | A2 | ≥1 realizes | entity-model §4.5 | `[plan]` entity-model §2 |
| trade_offs | Abstract model alone = 0% regen; enrichment (AST-level body_hints/constants) required for fidelity. | **verified** | A7 | cap trade-off | CONTEXT.md “Regeneration” (0% pass) vs “Blind Regeneration” (100%) | `[context]` `[testing]` |

---

## §4. Sub-capabilities (18)

### 4.1 CAP-extract sub-caps (3)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| CAP-extract.scan | intent | AST-walk tree; emit observable facts (modules/sigs/imports/routes/constants). | **verified** | A1 | `pipeline_v3/scan.py` (BEH-scan); `manifest/scanner.py` | `[model]` BEH-scan `[delivery]` manifest 74 tests |
| CAP-extract.scan | provides | ScanResult — ModuleRecord list (sigs, docstrings, imports, public surface). | **verified** | A5 | `tests/pipeline_v3/test_scan.py` | `[model]` BEH-scan provides |
| CAP-extract.detect | intent | Discover architecturally-significant patterns (http/cli/message/rpc) + affinity clusters. | **verified** | A1 | `pipeline_v3/cluster.py` (BEH-cluster); `manifest/endpoint_extractor` | `[model]` BEH-cluster `[context]` Phase 4 endpoint extractors |
| CAP-extract.detect | failure_modes | name-prefix mis-groups sibling modules; single dir hosting unrelated modules. | **verified** | A7 | BEH-cluster failure_modes; real-repo 1030 ambiguous-module | `[model]` `[testing]` |
| CAP-extract.seed | intent | Emit seed nodes (one per module/endpoint) with open promises. | **verified** | A1 | `pipeline_v3/derive_promises.py` (BEH-derive-promises) emits intent/delivers/provides | `[model]` BEH-derive-promises |
| CAP-extract.seed | provides | PromiseSet — Promise records per module (intent/delivers/provides only, AST-era). | **verified** | A5 | `tests/pipeline_v3/test_derive_promises.py` | `[model]` BEH-derive-promises |

### 4.2 CAP-model sub-caps (7 — the operator)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| CAP-model.grow | intent | Pick an open promise, expand into candidate edges/nodes (select-promise · propose-candidates). | delivered | A5 | design §3.2 operator stage; closest prior = BEH-P1.2 infer | `[plan]` design `[model]` BEH-P1.2 |
| CAP-model.grow | failure_modes | infer/propose is the chronic-weak stage (score 69; 308 complex-behavior unresolved). | **verified** | A7 | `learning/history.json`; 38 lessons.md | `[testing]` |
| CAP-model.ground | intent | Verify candidates against typed evidence (gather · check-grounding · score-confidence). | delivered | A7 | design §operator; partial prior = SIL `evidence.py` verified_by chain | `[plan]` design `[model]` BEH-SIL.5 |
| CAP-model.gate | intent | Admit only schema+constraint-valid candidates; emit gaps (admit-schema · admit-constraints). | **verified** | A4 | `pipeline/validate.py` (BEH-P1.7); `core/validator.py`; `authoring/gate.py` | `[model]` BEH-P1.7 `[delivery]` |
| CAP-model.gate | success_criteria | Score ≥80/100; zero false-positive orphan verdicts on well-formed models. | **verified** | A7 | `tests/test_validator.py` | `[model]` BEH-P1.7 success_criteria |
| CAP-model.reconcile | intent | Normalize to canonical form: dedup · identity-bind(θ) · roll-up · canonicalize. | delivered | A2 | design closure operator; dedup prior = LessonStore content-hash; rollup prior = CAP-WK | `[plan]` design `[model]` BEH-27.3, CAP-WK |
| CAP-model.govern | intent | Schedule discharge under budget (critical-path · slack · tier-schedule · widen · batch). | delivered | A4 | design §govern; partial prior = OCA `llm/bundle.py` BundleScheduler (tier caps T1/T2/T3) | `[plan]` design `[context]` Part 14 bundle |
| CAP-model.remember | intent | Persist decisions, identities, generations (cache-decision · record-generation). | **verified** | A6 | lifecycle `generation_dir`, `ArchitecturePackage`; `pipeline/cache.py` | `[context]` Lifecycle Phase 1 `[model]` CONS-resumable |
| CAP-model.traverse | intent | Run declarative walks (select→hop→classify→rollup→evidence→emit-cards). | **verified** | A5 | `src/architecture_model/walks/`; 24 walk tests; CAP-WK 14 covered walks | `[model]` CAP-WK intent `[context]` Walk Parts 1–15 |

### 4.3 CAP-represent sub-caps (3)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| CAP-represent.slice | intent | Materialize a named curated subset (select · close-relationships · curate/redact). | **verified** | A5 | `lifecycle/model_slice_materializer`; `core/slicer.py` (slice_by_fblock/layer/entity/component) | `[model]` CAP-SL, BEH-26.3 `[context]` |
| CAP-represent.slice | requirements | Sub-model itself validates; preserve all promises on retained entities (no truncation). | delivered | A2 | CAP-SL requirements (status: open) | `[model]` CAP-SL (gap:open) `[model]` L16 RESOLVED |
| CAP-represent.project | intent | Turn materialized slice + ViewSpec into DiagramSpec (resolve-projector · stamp-freshness/provenance). | **verified** | A5 | `lifecycle/view_projection.projectors`; freshness stamp `view_projection.py:189-194` | `[context]` Phase 1 projector registry |
| CAP-represent.render | intent | Deterministically render ProjectedView to bytes (md/html/svg/zip/ai-context/pipeline-html). | **verified** | A7 | lifecycle renderers; dashboard byte-identical round-trip `test_dashboard_rebuild.py` | `[context]` Pipeline Dashboard `[delivery]` |

### 4.4 CAP-learn sub-caps (3)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| CAP-learn.observe | intent | Capture outcomes into append-only journals (gate/drift/test/llm-call · read). | **verified** | A5 | `feedback/{gates,drift,junit_ingest,llm_calls}.py` (BEH-27.1, BEH-FBK) | `[model]` BEH-FBK `[context]` Part 15 |
| CAP-learn.lesson | intent | Distill deduplicated lessons from journals (content-hashed IDs). | **verified** | A2 | `orchestration/compaction.py` (BEH-27.3); `pipeline/lessons.py` (BEH-27.4) | `[model]` BEH-27.3/.4 |
| CAP-learn.tune | intent | Adjust expander/scheduler rules from lessons (closes design B6 loop). | delivered | A4 | `pipeline/auto_correct.py` (BEH-27.5); adaptive optimizer 4 rules | `[model]` BEH-27.5 `[context]` Learning Loop optimizer |

### 4.5 CAP-mdd sub-caps (2)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| CAP-mdd.generate | intent | Generate code from model; converge against oracle (scaffold · fill-bodies · oracle-loop). | **verified** | A1 | blind-regen 35/35; test-oracle normal-mode grades A/B | `[context]` Regen w/ Test-Oracle `[testing]` |
| CAP-mdd.verify-parity | intent | Run oracle, diff, score behavioral parity (run-oracle · diff · score-parity). | **verified** | A7 | parity/fidelity scoring per subsystem (colorama 80% → click 89% normal; 100% blind) | `[context]` fidelity tables `[testing]` |

---

## §5. Components (26)

### 5.1 Substrate layer (3)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| COMP-SourceScanner | intent | AST-walk a target tree; emit observable-fact inventory. | **verified** | A1 | forked `pipeline_v3/scan.py` + `manifest/scanner.py` (COMP-3) | `[model]` BEH-scan `[delivery]` manifest 74 tests |
| COMP-SourceScanner | layer | Substrate (A4). kind=library. | **verified** | A4 | self-model COMP-3 Manifest | `[model]` `[schema]` layer field |
| COMP-SourceScanner | produces | Manifest/ScanReport (observable-fact inventory). | **verified** | A5 | `manifest/generator.py` generate_manifest | `[context]` Manifest APIs |
| COMP-PatternDetector | intent | Detect endpoints/handlers/clusters (http/cli/message/rpc). | **verified** | A1 | `manifest/endpoint_extractor`; `pipeline_v3/cluster.py` | `[context]` Phase 4 `[model]` BEH-cluster |
| COMP-PatternDetector | dependencies_rationale | Depends on SourceScanner output (scan→detect ordering). | **verified** | A3 | BEH-cluster traces from scan; relate stage | `[model]` `[schema]` |
| COMP-PatternDetector | failure_modes | AST-only misses dynamic/decorator patterns; 1030 ambiguous-module on infer. | **verified** | A7 | real-repo lessons.md | `[testing]` |
| COMP-Seeder | intent | Emit seed nodes with kind-valence open promises. | **verified** | A1 | `pipeline_v3/derive_promises.py` | `[model]` BEH-derive-promises |
| COMP-Seeder | dependencies_rationale | Depends on PatternDetector (detect→seed ordering). | delivered | A3 | entity-model §4.1 | `[plan]` |

### 5.2 Kernel layer (13)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| COMP-ExpansionKernel | intent | Coordinator of the fixpoint; runs B-ROUND to least-fixpoint. | delivered | A1 | design §operator; closest prior = `pipeline_v3/orchestrator.py` (BEH-run-pipeline) + `pipeline/coordinator.py` (BEH-P1) | `[plan]` design `[model]` BEH-run-pipeline |
| COMP-ExpansionKernel | failure_modes | budget-exhausted mid-round; infer/grow chronic-weak (69). | **verified** | A7 | `learning/history.json` | `[testing]` |
| COMP-PromiseEngine | intent | Compute open promises per node from kind-valence; track lifecycle. | **verified** | A2 | `core/promise.py` (accepts any non-empty attribute); v3 PromiseSpec + CONS-open-schema | `[model]` CONS-open-schema `[schema]` promise-graph.schema.json |
| COMP-PromiseEngine | produces | Promise nodes (`{owner}#p{index}`, has-promise edge). | delivered | A5 | entity-model §9; graph export promotes promises to sub-nodes (L21: 802 promises) | `[plan]` `[model]` L21 |
| COMP-ExpanderRegistry | intent | Total registry of `(kind, axis)` → expander (symbolic/neural). | typed-gap | A2 | — **genuinely net-new (§0.5)**; nearest prior = ProjectorRegistry pattern (register/resolve) | `[plan]` design only — `gap:missing` content beyond registry shape |
| COMP-ExpanderRegistry | total-registry-invariant | Every `(kind,axis)` pair resolves to exactly one expander. | typed-gap | A2 | — net-new | `[plan]` design invariant only |
| COMP-Grounder | intent | Check candidate edges/nodes against typed evidence. | typed-gap | A7 | — **net-new**; partial analog = SIL `evidence.py` + verified_by chains | `[plan]` design; `[model]` BEH-SIL.5 (analog only) |
| COMP-Grounder | evidence-taxonomy | static / observational / executable. | delivered | A7 | design §evidence; cf. L14 tiers (runtime/inherited/design/asserted) | `[plan]` design `[model]` L14 |
| COMP-GateEvaluator | intent | Admit only schema+constraint-valid candidates; emit gaps. | **verified** | A4 | `pipeline/validate.py`, `core/validator.py`, `authoring/gate.py` | `[model]` BEH-P1.7 `[delivery]` validator 90/100 |
| COMP-GateEvaluator | verification-classes | existence / prohibition / parametric (3 classes). | delivered | A4 | design §verification classes; entity-model §7.3 | `[plan]` design |
| COMP-Reconciler | intent | Closure operator: dedup, identity-bind, roll-up, canonicalize (confluence-modulo-budget). | delivered | A2 | design; dedup prior = LessonStore content-hash; rollup prior = CAP-WK rollup stage | `[plan]` design `[model]` BEH-27.3, CAP-WK |
| COMP-BudgetGovernor | intent | Critical-path, tier-exhausting, cost-aware scheduler (widening). Internal-only (no interface). | delivered | A4 | design; partial prior = OCA BundleScheduler (tier caps T1=1/T2=10/T3=3, cost-split) | `[plan]` design `[context]` Part 14 |
| COMP-ModelGraph | intent | Pure state — mutable graph (nodes/edges/promises). Anti-god-object: no logic. | delivered | A4 | design; `CON-pure-state`; graph export `to_networkx` proves NN-compilable round-trip | `[plan]` design `[context]` Graph export L21 |
| COMP-ModelGraph | NN-compilable | Lossless axis-typed MultiDiGraph round-trips (C-N2). | delivered | A7 | `graph/to_networkx` (18/18 export tests + graphml round-trip); 1011 nodes/1086 edges | `[context]` L21 `[delivery]` |
| COMP-DecisionCache | intent | Memoize expander decisions for incremental re-runs. Internal-only. | delivered | A6 | `pipeline/cache.py` (per-stage disk cache) is the partial analog | `[model]` CONS-resumable `[context]` |
| COMP-IdentityStore | intent | Sticky θ-crosswalk; stable IDs across generations (θ_high=0.85/θ_low=0.60). Internal-only. | typed-gap | A6 | — **net-new**; θ thresholds are design-only; lifecycle has generation lineage but no θ-crosswalk | `[plan]` design `[discussion]` IdentityStore rationale |
| COMP-GenerationStore | intent | Publish + version model generations; own generation lineage. | **verified** | A6 | lifecycle `generation_dir`, `current_root_digest`, `ArchitecturePackage`, package_publish/load/diff | `[context]` Lifecycle Phase 1 `[delivery]` |
| COMP-GenerationStore | produces | Generation (`GEN-*`, published revisions). | **verified** | A5 | `architect_package_publish` returns {package_id, revision, digest} | `[context]` lifecycle tools |
| COMP-WalkEngine | intent | Run declarative WalkSpecs (select→…→emit cards). | **verified** | A5 | forked AMS `walks/`; `walks/spec/loader.py`, `walks/runner.py`; 14 covered walks | `[model]` CAP-WK `[context]` Walk Parts 1–15 |
| COMP-SeedStrategy | intent | Choose seeding policy (forward-author vs code-extract). Internal-only (support). | typed-gap | A2 | — **net-new**; partial prior = `architect_author` forward-author path | `[plan]` design `[context]` author tool (analog) |

### 5.3 Projection layer (4)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| COMP-Slicer | intent | Materialize ModelSlice contracts into closed fragments. | **verified** | A5 | forked `lifecycle/model_slice_materializer`; `core/slicer.py` | `[model]` CAP-SL `[context]` Phase 1 |
| COMP-Slicer | consumes | SliceSpec (ModelSlice contract). | **verified** | A3 | `architect_slice_materialize` | `[context]` lifecycle tools |
| COMP-ProjectorRegistry | intent | Named registry of pure projectors → DiagramSpec. | **verified** | A5 | `lifecycle/view_projection.projectors` register/resolve; families 1–8 | `[context]` Phase 1–3 projectors |
| COMP-ProjectorRegistry | exposes | ProjectorRegistry-API (register/resolve). | **verified** | A3 | `view_projection.projectors.register` | `[context]` |
| COMP-Renderers | intent | Deterministic md/html/svg/zip/ai-context/pipeline-html renderers. | **verified** | A7 | lifecycle renderers; `architect_view_render`, `artifact_rebuild` | `[context]` `[delivery]` |
| COMP-Renderers | produces | Artifact (`ART-*`) + provenance sidecar. | **verified** | A5 | Phase 5 `<id>.provenance.json` sidecars | `[context]` Phase 5 Task 28 |
| COMP-Viewer | intent | Self-contained HTML lenses (v3 promise-graph, legacy box-arrow, dashboard). | **verified** | A1 | COMP-VIEWER D1..D10; `scripts/build_v3_viewer.py`; 326KB single file | `[model]` viewer.v3.yaml `[discussion]` |
| COMP-Viewer | slos | HTML <500KB (measured 326KB @ef632b9); rebuild <5s; open <2s; zero runtime deps. (!) **drift:** current file = 1.73MB — SLO violated since ef632b9. | **verified** (as-of-commit) | A7 | `stat v3_viewer.html = 326034 bytes` (ef632b9); current `stat` = 1,731,509 bytes | `[model]` COMP-VIEWER slos `[delivery]` |
| COMP-Viewer | failure_modes | fragment kind-collision → exit 3; conflicting promise content → exit 3; unrealized false-positive if new realizing edges. | **verified** | A7 | `_merge_sources()` error paths | `[model]` COMP-VIEWER failure_modes |

### 5.4 Adaptation layer (3)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| COMP-FeedbackJournals | intent | Append-only JSONL streams (gates, drift, test_results, llm_calls). Fail-soft. | **verified** | A5 | `feedback/*.py` (BEH-FBK); O_APPEND+fsync; missing→[] | `[model]` BEH-FBK `[context]` Phase 2/Part 15 |
| COMP-FeedbackJournals | produces | Journal (`JRN-gates/drift/test/llm`). | **verified** | A5 | 4 journal writers + tests | `[model]` BEH-FBK.1-4 `[delivery]` |
| COMP-FeedbackJournals | goals | Zero data loss on append (fsync); fail-soft read; byte-stable under AMS_DETERMINISTIC_NOW. | **verified** | A7 | `tests/feedback/test_*_journal.py` | `[model]` BEH-FBK goals |
| COMP-LessonStore | intent | Deduplicated lesson store (fixes AMS "lessons overwritten"). Internal-only. append+dedup. | **verified** | A5 | `pipeline/lessons.py`; content-hashed IDs (BEH-27.3); CONTEXT Lessons | `[model]` BEH-27.3 `[context]` Learning Loop |
| COMP-LessonStore | produces | Lesson (`LSN-*`, deduplicated insights). | **verified** | A5 | lessons.md append-only; L1–L22 corpus | `[model]` CAP-DF lessons_learned |
| COMP-RuleTuner | intent | Tune expander/scheduler rules from lessons; re-enter B-ROUND (closes B6). | delivered | A4 | `pipeline/auto_correct.py` (BEH-27.5); adaptive optimizer 4 heuristics | `[model]` BEH-27.5 `[context]` optimizer |
| COMP-RuleTuner | affects | ExpanderRegistry, BudgetGovernor (A4). | delivered | A4 | entity-model §4.4 | `[plan]` |

### 5.5 mdd layer (2)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| COMP-CodeGenerator | intent | Generate code from model; oracle-in-loop convergence. | **verified** | A1 | blind-regen 35/35; `quality/code_improver.py`, `code_prompts.py` | `[context]` Blind Regen `[delivery]` quality module |
| COMP-CodeGenerator | precondition | oracle-obtainable (test suite available as behavioral oracle). | **verified** | A3 | test-oracle loop; test_contracts drive regen | `[context]` “What made it work” |
| COMP-ParityChecker | intent | Run oracle, diff, score behavioral parity. | **verified** | A7 | fidelity/parity scoring (per-subsystem 80–100%) | `[context]` fidelity tables `[testing]` |
| COMP-ParityChecker | verifies | behaviors (A7 parity metric). | **verified** | A7 | blind score = normal score for 33/35; structlog beats normal | `[context]` |

### 5.6 Cross-cutting support (1)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| COMP-LLMProviderRouter | intent | Provider-agnostic routing (policy, budget, fallback, bundling). | **verified** | A3 | `llm/provider.py` Protocol; BEH-LLM; OCA policy.yaml + BundleScheduler | `[model]` BEH-LLM `[context]` LLM Provider Layer |
| COMP-LLMProviderRouter | exposes | LLMProvider-Protocol (complete/stream/structured/tokenize). | **verified** | A3 | `llm/provider.py` (BEH-LLM.1-5) | `[model]` BEH-LLM.1 |
| COMP-LLMProviderRouter | requirements | TaskClass→(provider,model,tier,cost-cap,fallback); every call → LLMCallRecord. | **verified** | A4 | `.architecture/llm/policy.yaml`; `feedback/llm_calls.py` | `[model]` BEH-LLM requirements `[context]` Part 14/15 |
| COMP-LLMProviderRouter | failure_modes (cost/fallback) | per-call cost-cap + fallback-on-error are design-declared, not yet verified. | delivered | A7 | BEH-LLM.6/.7 intent (status: open) | `[model]` BEH-LLM.6/.7 (gap:unverified) |

---

## §6. Behaviors (~33)

### 6.1 B-ROUND (7)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| BEH-ROUND | intent | govern → grow → ground → reconcile → bind → gate, to least-fixpoint. | delivered | A5 | design §operator; closest prior = BEH-run-pipeline ordered stages | `[plan]` design `[model]` BEH-run-pipeline |
| BEH-ROUND.govern | intent | build-DAG · schedule · widen. | delivered | A4 | design; BundleScheduler analog | `[plan]` `[context]` Part 14 |
| BEH-ROUND.grow | intent | select · propose. | delivered | A5 | design; BEH-P1.2 infer analog (chronic-weak) | `[plan]` `[testing]` |
| BEH-ROUND.ground | intent | gather · check · score. | delivered | A7 | design; SIL evidence analog | `[plan]` `[model]` BEH-SIL.5 |
| BEH-ROUND.reconcile | intent | dedup · identity-bind · roll-up · canonicalize. | delivered | A2 | design; CAP-WK rollup + LessonStore dedup | `[plan]` `[model]` |
| BEH-ROUND.bind | intent | record-generation. | **verified** | A6 | lifecycle generation publish | `[context]` lifecycle |
| BEH-ROUND.gate | intent | admit-schema · admit-constraints · emit-gaps. | **verified** | A4 | `pipeline/validate.py`; `architect_gate` | `[model]` BEH-P1.7 `[context]` |

### 6.2 Top-level behaviors (7) ← crosswalk to AMS pipelines

| id | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|
| BEH-B1 Extract | scan→derive→cluster→link→containerize→verify→publish (forks pipeline_v3) → B-ROUND. | **verified** | A5 | BEH-run-pipeline + BEH-P1 (10-stage); 203 pipeline tests | `[model]` BEH-run-pipeline/BEH-P1 `[delivery]` |
| BEH-B2 Author | note→save→author→apply (CAP-DF ceremony) → B-ROUND. | **verified** | A5 | BEH-28.1-4; `walks/meta/{promise_note,save_promise_note,author_promise_note}.py` | `[model]` BEH-28 `[context]` CAP-DF Parts 10–12 |
| BEH-B3 Re-extract | re-scan→diff→identity-bind→B-ROUND. | delivered | A6 | `architect_diff`, `package_diff`; identity-bind is net-new | `[context]` diff tools `[plan]` design |
| BEH-B4 Represent | slice→materialize→project→render→rebuild. | **verified** | A5 | BEH-26; lifecycle substrate Phases 1–5 | `[model]` BEH-26 `[context]` |
| BEH-B5 Generate | scaffold→fill-bodies→oracle-loop→verify-parity. | **verified** | A1 | blind-regen 35/35 | `[context]` Blind Regen `[testing]` |
| BEH-B6 Learn | observe→lesson→tune→re-enter B-ROUND. | **verified** | A5 | BEH-27; learning loop | `[model]` BEH-27 `[context]` |
| BEH-B7 Gate | run gate checks (= B-ROUND.gate standalone). | **verified** | A4 | `architect_gate` + gates.jsonl (BEH-FBK.1) | `[model]` BEH-FBK.1 `[context]` |

### 6.3 Fan-out sub-behaviors (~19) — representative rows

| id | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|
| B1: scan/derive/cluster/link/containerize/verify/publish | per-stage pipeline_v3 behaviors. | **verified** | A5 | BEH-scan..BEH-publish; `tests/pipeline_v3/test_<stage>.py` | `[model]` `[delivery]` |
| B1: 10-stage BEH-P1.1–.10 | observe→infer→allocate→relate→specify→contract→validate→decompose→synthesize→emit. | **verified** | A5 | `pipeline/*.py`; per-stage | `[model]` BEH-P1.* |
| B2: note/save/author/apply | CAP-DF ceremony steps. | **verified** | A5 | BEH-28.1-4 | `[model]` BEH-28 `[context]` Parts 10–12 |
| B4: BEH-26.1–.6 | parse-focus→load→slice→format→enforce-budget→emit. | **verified** | A5 | BEH-26.1-6 | `[model]` |
| B6: BEH-27.1–.6 | read-journals→classify→extract-lessons→write→update-rules→propose-patches. | partial | A5 | BEH-27.1/.3/.4/.5 verified; .2/.6 open | `[model]` BEH-27.* |
| SIL: BEH-SIL.1–.8 | instrument→append→rollup→query→attach-evidence→no-op→audit→async. | **verified** | A7 | `sil/*.py`; `tests/sil/*` | `[model]` BEH-SIL.* `[context]` |
| infer sub-behavior | infer semantic entities — the weak link. | **verified** (as weak) | A7 | score 69 chronic; 308 complex-behavior | `[testing]` learning curve |

---

## §7. Interfaces (13)

| id | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| IF-ExpanderRegistry | intent | `register(kind,axis,expander)` / `resolve`. | typed-gap | A3 | — net-new; shape mirrors ProjectorRegistry | `[plan]` design |
| IF-ProjectorRegistry | intent | `register(name)` / `resolve` → DiagramSpec. | **verified** | A3 | `view_projection.projectors` | `[context]` Phase 1 |
| IF-LLMProvider | intent | `complete/stream/structured/tokenize` Protocol. | **verified** | A3 | `llm/provider.py` (IF-llm-provider) | `[model]` IF-llm-provider |
| IF-LLMProvider | requirements | runtime-checkable; deterministic seed/temp; per-call cost accounting. | delivered | A4 | IF-llm-provider requirements (status: open) | `[model]` (gap:open) |
| IF-Patch | intent | ModelPatch (add/remove/replace); move→ParseError. | **verified** | A3 | `ai/patch.py apply_model_patch`; Proposal/Provenance | `[context]` AI APIs `[model]` BEH-28.4 |
| IF-ScanReport | intent | observable-fact inventory (ModuleRecord). | **verified** | A5 | `manifest/generator.py`; IF-model | `[model]` IF-model `[context]` |
| IF-EvidenceRef | intent | static/observational/executable typed evidence. | typed-gap | A7 | — net-new; SIL evidence is partial analog | `[plan]` design `[model]` BEH-SIL.5 |
| IF-PromiseSpec | intent | v3 PromiseSpec + **axis/valence** (net-new fields). | **verified** (base) / typed-gap (axis/valence) | A3 | `promise-graph.schema.json`; axis/valence net-new | `[schema]` `[plan]` design |
| IF-WalkSpec | intent | select/traverse/classify/rollup/evidence/emit. | **verified** | A3 | `walks/spec/loader.py`; 13 WalkSpec YAMLs | `[model]` CAP-WK `[context]` |
| IF-SliceSpec | intent | ModelSlice contract. | **verified** | A3 | lifecycle ModelSlice; `architect_slice_materialize` | `[context]` Phase 1 |
| IF-ViewSpec | intent | projector + output kind. | **verified** | A3 | lifecycle ViewSpec; `architect_view_project` | `[context]` |
| IF-Journal | intent | append-only JSONL. | **verified** | A5 | `feedback/*.py` | `[model]` BEH-FBK |
| IF-GraphExport | intent | lossless MultiDiGraph (C-N2). | **verified** (export) / delivered (C-N2) | A7 | `graph/to_networkx` (18/18 tests, 1011/1086) — but C-N2 compilability net-new | `[context]` L21 `[plan]` design |
| IF-CLI | intent | commands + MCP tools. | **verified** | A3 | `cli/main.py`; OCA MCP tools (19 handlers) | `[context]` `[delivery]` |

---

## §8. Actors (5) · Layers (5) · Constraints (5)

### 8.1 Actors

| id | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|
| ACT-Modeler | Runs pipeline, opens viewer, authors fragments, takes notes. Primary daily user. | **verified** | A3 | ACT-developer intent | `[model]` ACT-developer `[report]` 2026-09-15 dev-workflow |
| ACT-Target | Target system — source of all A7 evidence; triggers B3. | **verified** | A7 | ACT-se / pipeline input | `[model]` `[plan]` |
| ACT-LLM | External LLM service; consumes LLMProvider-Protocol. (Part 3 deferred.) | delivered | A3 | ACT-llm intent (status: open) | `[model]` ACT-llm (gap:open) |
| ACT-Auditor | Triggers B6/B7; consumes artifacts. | **verified** | A3 | ACT-ci intent (byte-determinism gate enforcer) | `[model]` ACT-ci |
| ACT-Downstream | arch-agent / N1-N2; consumes GraphExport. | delivered | A3 | graph export consumers; arch-agent repo | `[context]` L21 `[plan]` design N1/N2 |

### 8.2 Layers

| id | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|
| LAY-Substrate | SourceScanner, PatternDetector, Seeder, FeedbackJournals; upward-only deps. | **verified** | A4 | L-standard/L-tooling intents; self-model | `[model]` L-standard, L-tooling |
| LAY-Kernel | 13 model components; → Substrate. | **verified** | A4 | L-tooling (pipeline_v3) | `[model]` L-tooling |
| LAY-Projection | Slicer, ProjectorRegistry, Renderers, Viewer; → Kernel. | **verified** | A4 | L-view intent | `[model]` L-view |
| LAY-Adaptation | LessonStore, RuleTuner; → Kernel via journals. | **verified** | A4 | L-authoring/feedback | `[model]` `[context]` |
| LAY-CrossCutting | LLMProvider/Router; any (policy-bounded). | delivered | A4 | L-llm intent (status: open, Part 3) | `[model]` L-llm (gap:open) |

### 8.3 Constraints

| id | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|
| CON-existence | required promise present, else `gap:missing`. | **verified** | A4 | validator referential-integrity; GateEvaluator | `[model]` BEH-P1.7 `[delivery]` |
| CON-prohibition | forbidden edge/state absent, else `gap:violation`. | delivered | A4 | design §verification classes; layer dep-direction rules | `[plan]` design `[model]` CONS-* |
| CON-parametric | fitness ≤ bound (budgets/SLOs), aggregate-verified. | delivered | A4 | design; slos promises across model | `[plan]` `[model]` slos (7 promises) |
| CON-pure-state | ModelGraph has no logic (anti-god-object). | delivered | A4 | design; `to_networkx` state/logic separation | `[plan]` design `[context]` L21 |
| CON-N2 | lossless axis-typed graph round-trips (machine-evaluable). | delivered | A7 | `graph/to_networkx` round-trip proves graph half; axis-typing net-new | `[context]` L21 `[plan]` design |
| CONS-determinism (inherited) | all artifact outputs byte-identical across runs (pinned clock). | **verified** | A7 | Phase 8 gate; rerun-diff (ef632b9) | `[model]` CONS-determinism |
| CONS-open-schema (inherited) | Promise.attribute = open string, no enum. | **verified** | A3 | `promise-graph.schema.json` (no enum); `promise.py:101` | `[model]` CONS-open-schema `[schema]` |
| CONS-ast-only (inherited) | no LLM in extract path. | **verified** | A2 | pipeline_v3 imports no LLM adapter | `[model]` CONS-ast-only |

---

## §9. I/O-entity family (12)

| id | content | status | axis | owner | verified_by | provenance |
|---|---|---|---|---|---|---|
| ART-* Artifact | Rendered docs/diagrams/viewers/dashboards/code/graph-exports. | **verified** | A5 | Renderers/Viewer/CodeGenerator | `architect_artifact_rebuild`; provenance sidecars | `[context]` Phase 5 |
| JRN-gates | gate outcomes (GateEvent). | **verified** | A5 | FeedbackJournals | `feedback/gates.py`; `architect_gate` auto-append | `[model]` BEH-FBK.1 |
| JRN-drift | drift snapshots. | **verified** | A5 | FeedbackJournals | `feedback/drift.py`; post-pipeline auto-append | `[model]` BEH-FBK.2 |
| JRN-test | test_results batches. | **verified** | A5 | FeedbackJournals | `feedback/junit_ingest.py` | `[model]` BEH-FBK.3 |
| JRN-llm | llm_calls records. | **verified** | A5 | FeedbackJournals | `feedback/llm_calls.py` (Part 15) | `[model]` BEH-FBK.4 `[context]` |
| WO-* WorkOrder | `fill_promise:<entity>:<attr>` intents. | **verified** | A5 | B2 save step | `ai/work_order.py`; `architect_promise_save` | `[context]` Part 11 `[model]` BEH-28.2 |
| JOB-* Job | queued→running→…→completed tracking. | **verified** | A6 | BudgetGovernor/Kernel | `ai/jobs.py` JobStore | `[context]` AI APIs |
| PROP-* Proposal | ModelPatch + Provenance. | **verified** | A5 | authoring expander | `ai/proposals.py`; `architect_promise_author` | `[context]` Part 12 `[model]` BEH-28.3 |
| NOTE-* Note/CommentStub | promise-slot comments. | **verified** | A5 | Modeler note step | `comments/models.py` PromiseTarget; `architect_promise_note` | `[context]` Part 10 `[model]` BEH-28.1 |
| LSN-* Lesson | distilled deduplicated insights. | **verified** | A5 | LessonStore | lessons.md; L1–L22 | `[model]` CAP-DF lessons_learned |
| GEN-* Generation | published model revisions. | **verified** | A6 | GenerationStore | lifecycle package_publish/list_generations | `[context]` lifecycle |
| DEC-* Decision (ADR) | design decisions with rationale. | delivered | A4 | ExpansionKernel/Modeler | devlog LOG-0021..0089; ~14 decisions | `[discussion]` devlog |

---

## §10. Promise & Evidence nodes

| kind | attribute | content | status | axis | verified_by | provenance |
|---|---|---|---|---|---|---|
| Promise | shape | v3 PromiseSpec (attribute·content·owner·delivered_from·verified_by·status·gap_type·provenance) + **axis** + **valence**; `has-promise` edge. | **verified** (base) / typed-gap (axis+valence) | A7 | base promoted to sub-node in graph export (L21: 802 promises); axis/valence net-new | `[schema]` `[context]` L21 `[plan]` design |
| Evidence | shape | uri · type(static/observational/executable) · digest · verifies-target; `verified-by` edge; deduped+promoted. | **verified** (promotion) / delivered (typed-taxonomy) | A7 | graph export promotes 132 unique evidence URIs (L21); typed taxonomy is net-new | `[context]` L21 `[plan]` design |

---

## §11. Coverage scorecard (by provenance cluster)

Status rollup across the ~100 gen-0 entities' primary promises:

| entity cluster | count | verified | delivered | typed-gap | dominant provenance |
|---|---:|---:|---:|---:|---|
| System (L0) | 1 | 0 | 1 | 0 | `[plan]` |
| Capabilities (L1) | 5 | 4 | 1 | 0 | `[model]`+`[context]`+`[testing]` |
| Sub-caps (L2) | 18 | 12 | 6 | 0 | `[model]`+`[context]` |
| Components | 26 | 14 | 7 | 5 | `[model]`+`[delivery]` |
| Behaviors (~33) | 33 | 24 | 9 | 0 | `[model]` |
| Interfaces | 13 | 9 | 2 | 2 | `[model]`+`[schema]` |
| Actors | 5 | 3 | 2 | 0 | `[model]` |
| Layers | 5 | 4 | 1 | 0 | `[model]` |
| Constraints | 5 (+3 inherited) | 1+3 | 4 | 0 | `[plan]`+`[model]` |
| I/O family | 12 | 11 | 1 | 0 | `[context]`+`[model]` |
| Promise/Evidence nodes | 2 | 0 (base verified, ext gap) | 0 | 2 (axis/valence/taxonomy) | `[schema]`+`[plan]` |
| **TOTAL** | **~125** | **~86** | **~34** | **~9** | — |

**Provenance-cluster contribution:**
- `[model]` (v3) — backs the largest share: every CAP-extract, CAP-model.traverse, CAP-represent, CAP-learn, BEH-*, IF-*, actor, layer, constraint.
- `[context]`/`[delivery]` — backs lifecycle (GenerationStore, Slicer, ProjectorRegistry, Renderers), SIL, LLM router, I/O family.
- `[testing]` — backs CAP-mdd (35/35 @100%), CAP-learn failure_modes (infer 69), CAP-extract.detect failure_modes (1030 ambiguous-module).
- `[discussion]` — backs DEC-* decisions, IdentityStore/BudgetGovernor rationale.
- **net-new residue** (typed-gap, no prior source): ExpanderRegistry, Grounder, IdentityStore, SeedStrategy internals; axis+valence promise fields; EvidenceRef typed taxonomy; CON-N2 axis-typing. **9 primary promises** — the genuine openAG invention surface.

---

## §12. Pending-ownership reservoir (`flows-to`)

Content that **exists and is sourced** but whose owner is a lower-level
entity **not yet in gen-0** (will be discovered in L3+ fan-out / gen-1).
Parked here per the user-locked distinction (reservoir ≠ gap). All tagged
`status: delivered · axis: A1↓`.

| reserved content | sourced from | flows-to (lower-level area) | provenance |
|---|---|---|---|
| per-stage SI&L badges + per-stage validation scores | CAP-PB open_questions (split 8 modules → 8 components) | 8 per-stage Expander components under ExpansionKernel | `[model]` CAP-PB open_questions |
| infer-stage fix heuristics for 1030 ambiguous-module + 308 complex-behavior | 38 real-repo lessons.md (django/textual) | per-stage `grow`/`infer` Expander (CAP-model.grow children) | `[testing]` |
| pattern classifier 7 types (CROSS_DEP, MISSING_IMPL, WRONG_CONSTANT, API_MISMATCH, COMPLEX_BEHAVIOR, TEST_INFRA, UNKNOWN) | BEH-27.2 (status: open); Learning Loop | RuleTuner sub-components / classify-DSL atoms | `[model]` BEH-27.2 `[context]` |
| adaptive optimizer 4 heuristic rules (dep-count, contract-cap, body-hint, historical) | Learning Loop (CONTEXT) | RuleTuner tune-expander sub-functions | `[context]` |
| report-card grading A–F + trend detection | Learning Loop report cards | LessonStore / RuleTuner reporting sub-entity | `[context]` |
| curated-view / hierarchy-era rationale (families 1–8, entity pages, drill-down) | H3 discussion; Phases 1–5 | ProjectorRegistry family projectors + Renderers | `[discussion]` `[context]` |
| θ-crosswalk tuning (θ_high=0.85/θ_low=0.60) sensitivity | H3 IdentityStore rationale | IdentityStore internal params (gen-1) | `[discussion]` `[plan]` |
| per-call cost-cap + fallback enforcement mechanics | BEH-LLM.6/.7 (status: open) | LLMProviderRouter budget sub-component | `[model]` BEH-LLM.6/.7 |
| critical-path / slack / tier-schedule / widening mechanics | OCA BundleScheduler (tier caps); design §govern | BudgetGovernor internal scheduler sub-functions | `[context]` Part 14 `[plan]` |
| compression economics (2.8×→85.8×, dependency-driven scaling law) | Token Economics (CONTEXT) | Slicer / CAP-represent.slice metrics sub-entity | `[context]` `[testing]` |
| CAP-DF ceremony bundling (T1/T2/T3 batch, demux keys) | Part 14 bundle | BudgetGovernor + LLMProviderRouter bundling | `[context]` Part 14 |
| domain profiles (controls/mechanical/electrical enum+property extensions) | CONTEXT Domain Profiles; `profiles/schema.py` | PromiseEngine valence-table per-domain extensions | `[context]` `[delivery]` |

---

## §13. Gap register (typed-gaps — nothing anywhere)

Genuinely sourceless primary promises → emitted as `gap:<class>` per
entity-model §10. These are the **openAG invention surface**.

| entity | attribute | gap class | why no source | provenance |
|---|---|---|---|---|
| COMP-ExpanderRegistry | intent / total-registry-invariant | `gap:missing` | `(kind,axis)`→expander total registry has no AMS analog beyond register/resolve shape | `[plan]` design only |
| COMP-Grounder | intent | `gap:missing` | candidate-grounding-against-typed-evidence is net-new (SIL evidence is observability, not admission control) | `[plan]` design only |
| COMP-IdentityStore | intent | `gap:missing` | sticky θ-crosswalk for stable IDs across generations — net-new (lifecycle has lineage, no θ) | `[plan]`+`[discussion]` |
| COMP-SeedStrategy | intent | `gap:missing` | forward-author-vs-code-extract policy selector — net-new (author tool is partial) | `[plan]` design only |
| IF-ExpanderRegistry | intent | `gap:dangling` | interface for net-new ExpanderRegistry | `[plan]` |
| IF-EvidenceRef | intent | `gap:dangling` | typed evidence interface (static/observational/executable) net-new | `[plan]` |
| IF-PromiseSpec | axis + valence | `gap:missing` | the two net-new promise fields — the core openAG extension | `[plan]`+`[schema]` |
| Promise node | axis + valence | `gap:missing` | same two fields at node level | `[plan]` |
| Evidence node | typed taxonomy | `gap:missing` | typed evidence taxonomy net-new (export promotion exists, typing does not) | `[context]` L21 (promotion only) |

> **9 typed-gaps.** Every one is a deliberate net-new design element, not an
> oversight. This is where openAG is genuinely inventing rather than
> inheriting.

---

## §14. Delivery + Testing evidence index

### 14.1 Delivery (H4)

| metric | value | source |
|---|---|---|
| commits | 835 | git log |
| tests passing | 4351 passed / 104 skipped | `pytest tests/` |
| validator score (self-model) | 90/100 | `validation.json` / CONTEXT |
| representativeness | 87.35 | metrics |
| per-component test backing | core 342 · lifecycle 227 · pipeline 203 · manifest 74 | `component_test_map.json` |
| delivered subsystems | pipeline_v3 (8 stages) · Walk Parts 1–15 · CAP-DF Parts 10–12 · lifecycle Phases 1–5 · SI&L · LLM Provider · Dashboard · Graph export | CONTEXT.md |
| caveat | `evaluation.yaml` model_coverage 0.0 is a stale sync artifact (not real) | H4 |

### 14.2 Testing & real-world (H5)

| result | value | source |
|---|---|---|
| extraction quality | 98/100 avg, 100% success (python-dotenv/colorama/tqdm/structlog) | CONTEXT §E2E |
| blind regeneration | **35/35 subsystems, 100% fidelity, 1.0 avg iterations** | CONTEXT Blind Regen FINAL |
| first-attempt convergence | 34/35 (97%) | CONTEXT |
| max compression | 85.8× (click.arguments); scaling law 2.8×→26.4× by repo size | CONTEXT Token Economics |
| learning curve (per-stage) | infer **69 chronic-weak** · specify 50→100 · validate 0→90 · allocate **regression 100→78** | `learning/history.json` |
| real-repo stage lessons | **1030 ambiguous-module + 308 complex-behavior**, all on infer | 38 `lessons.md` (django/textual) |
| pattern classifier / optimizer | 7 pattern types · 4 adaptive rules · A–F report cards | CONTEXT Learning Loop |

**Testing → attribute flow (user emphasis):** benchmark results ground
CAP-mdd (success_criteria, trade_offs), CAP-extract (success_criteria,
slos), and CAP-learn/CAP-extract.detect **failure_modes**; real-repo
lessons populate the §12 reservoir for per-stage grow/infer Expanders.

---

## §15. Provenance ledger (summary)

| provenance tag | entities/promises grounded | strength |
|---|---|---|
| `[model]` | ~86 promises across all kinds (v3 is the spine) | strongest — 246 PromiseSpec corpus |
| `[context]` | lifecycle, SIL, LLM router, I/O family, graph export | strong — delivered + documented |
| `[delivery]` | test-backing, validator 90/100, 835 commits | strong — runtime |
| `[testing]` | CAP-mdd, failure_modes, reservoir fuel | strong — benchmark |
| `[schema]` | PromiseEngine, PromiseSpec, open-schema constraint | definitional |
| `[discussion]` | DEC-*, IdentityStore/BudgetGovernor rationale | design-only (L14 tier) |
| `[plan]`/`[report]` | design rationale, axis/valence, net-new residue | design-only |

**Bottom line:** of ~125 primary gen-0 promises, **~86 are verified**
(prior model + delivery + testing evidence), **~34 are delivered**
(design-rationale or reservoir content awaiting lower-level owners), and
**only ~9 are true typed-gaps** — and those 9 ARE openAG's genuine
invention (fixpoint-kernel internals + axis/valence + CON-N2). **Zero
prior AMS effort is lost**; it is all re-anchored here with a backward
citation.

---

### Appendix — verbatim lessons & full per-entity tables

The complete H1 per-entity promise tables (all 246 PromiseSpecs) and the
verbatim L1–L22 lessons (with supersession notes L6→L18, L11→L19, L16
RESOLVED) are preserved at `.architecture/scratch/v3-promise-index.md`
(958 lines) and in `capabilities.v3.yaml` CAP-DF `lessons_learned`.
