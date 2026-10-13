# Plan B′ — Architecture-First Refactor to Promise-Graph Schema

**Date:** 2026-09-12
**Status:** Approved for execution (Phase B′-0a starting)
**Approval reviewer:** User only

## Governing Principle

Modeling is not a one-shot gate that closes at approval. It is a continuous
discipline that starts *before* code and continues through code + tests.
Approval gates the *first coding commit*, not the completion of modeling.
Existing code is preserved as a plugin behind adapter interfaces — the 3746
tests + 4 e2e benchmarks (colorama, structlog, tqdm, click) become the
plugin's regression harness.

## Philosophy Reframe (accepted 2026-09-12)

- **Primary organizing principle:** delivery-down / verify-up chain applied
  uniformly to *every attribute of every entity*. Every promise
  (`intent`, `goals`, `requirements`, `slos`, `success_criteria`,
  `failure_modes`, `assumptions`, `verification`, `open_questions`, ...)
  must have a delivery-down source (parent entity) and a verify-up evidence
  (child entity or test). If either is missing, the promise is flagged —
  same discipline as regen-score flags missing body hints.
- **Entity-as-standalone-unit:** every entity, at every decomposition level,
  must stand on its own. `slice_by_entity(entity_id)` must produce a
  self-contained package that documents *and* verifies that entity's
  promises within its own scope, or types its external gaps explicitly.
- **If we can perfectly model ourself we can use the insight to model
  everything.** The AMS refactor becomes a reference implementation of
  "model before build."

## Schema 3.0 Thesis

The 2.1 schema treats entities + relationships as primary substrate, with
promises as attributes on entities. Every problem observed — flat cap tree
(97 caps on 34 components), mechanical infer stage, static `visualize.py`,
0/97 closed chains — is downstream of that choice. Schema 3.0 inverts it:

- **Promise** is a first-class type. Every semantic field currently on
  `BaseEntity` becomes a `Promise` record referencing the owner entity.
- **Entities are containers**, not attribute owners. They group promises;
  they don't own semantic content directly.
- **Relationships are derived** from promise-source and promise-evidence
  links. Structural edges (`contains`, `exposes`, `consumes`) remain
  stored; semantic edges (`realizes`, `traces-to`, `exercised-by`) become
  views over the promise graph.

## New Pipeline Shape (7 stages, replaces 10-stage)

`scan → derive_promises → cluster → link → containerize → verify → publish`

- **cluster** groups promises by semantic similarity (embedding-based, not
  name-Jaccard). Duplicate capabilities cannot arise structurally.
- **link** builds delivered-from / verified-by edges. LLM used only in
  ambiguous middle band; exact / near-exact matches deterministic.
- **verify** runs `promise_closure` per entity; emits chain-closure report.
- Decomposition is a query over the promise graph, not a pipeline stage.

## Legacy Preservation Strategy

**Existing code is not deleted.** It becomes plugin:

- `LegacyProjectorAdapter` — every `core/visualize.py` function reachable
  through the projector interface.
- `LegacyPipelineAdapter` — the 10-stage pipeline plugs behind the new
  `scan` + `derive_promises` stages as one strategy among many.
- `LegacyDocsAdapter` — `docs/generator.py`, `docs/component_spec.py`,
  `docs/icd.py`, `docs/se/*` mapped to projector variants.
- 3746 existing tests bind to the adapter surface.
- 4 e2e benchmarks become adapter acceptance tests. Passing = adapter
  faithful. Failing = regression.

## Phases

### Phase B′-0a — Initial high-level model (1-2 weeks, no code)

Coarse anchors + delivery-down propagation. Model lives at
`.architecture-model.plan-b.yaml` — separate file, existing production
model untouched.

- **T0.1** — Actors + use-cases (Human Architect, LLM Agent, OCA Consumer,
  arch-agent Trainer × 4-6 umbrella use-cases: Extract-from-code,
  Migrate-2.1-to-3.0, Verify-standalone, Project-view, Propose-change,
  Publish-generation).
- **T0.2** — 4 umbrella capabilities (CAP-SLICE, CAP-MODEL, CAP-EXTRACT,
  CAP-DEV) with rich delivery-down attributes.
- **T0.3** — 7 sub-capabilities (CAP-PROMISE-GRAPH, CAP-PIPELINE,
  CAP-PROJECTORS, CAP-LLM, CAP-EVIDENCE, CAP-ADAPTER, CAP-VERIFY).
- **T0.4** — Behaviors for the 7-stage new pipeline + `triggers` edges +
  interface contracts.
- **T0.5** — Coarse components (~15-20).
- **T0.6** — Delivery-down propagation pass.
- **T0.7** — First closure baseline (expect 30-50% at leaves).
- **T0.8** — Regenerate viewer.html for user review.

### Phase B′-0b — Gap enumeration + typing (1 week)

- **T0.9** — Triage every `open` promise: genuinely-unclosed | typed-gap
  external-dependency | spurious | refinable-now.
- **T0.10** — Add missing entities the classification reveals.
- **T0.11** — Second closure measurement (target ≥ 70% closed OR typed-gap).

### Phase B′-0c — Approval + first-code readiness

- **T0.12** — Regenerate viewer.html.
- **T0.13** — Manual `verify_entity_standalone` on each of the 7
  sub-capabilities.
- **T0.14** — **User approval gate.** First code commit unlocked.

Approval does NOT freeze the model. Modeling continues through Phase B′-4.

### Phase B′-1 — Legacy-adapter design (parallel with B′-0b)

Modeled, not coded. Mapping tables declared as data.

- **T1.1-T1.5** — LegacyProjectorAdapter, LegacyPipelineAdapter,
  LegacyDocsAdapter, test binding strategy, benchmark declaration.

### Phase B′-2 — Schema 3.0 formalization (1 week)

- **T2.1** — `spec/architecture-model-3.0.schema.json` derived from
  modeled entities.
- **T2.2** — `spec/migration-2.1-to-3.0.md` — deterministic rules per
  field.
- **T2.3** — Round-trip contracts for 4 e2e benchmark models.
- **T2.4** — Backwards-compatibility declaration.

### Phase B′-3 — Approval + published architecture

- **T3.1** — Publish `.architecture-model.plan-b.yaml` v1 via
  `architect_package_publish`.
- **T3.2** — Regenerate viewer HTML, user sign-off.
- **T3.3** — Write
  `.opencode/skills/superpowers/architecture-first-refactor/SKILL.md`.
- **T3.4** — Freeze approval; first code commit unblocked.

### Phase B′-4 — Code with continuous modeling (7-10 weeks)

42 Plan-B tasks land here. Every code commit references its architecture
entity via commit-msg convention:
`feat(promise-graph): Promise parser round-trip [refs: CAP-PROMISE-GRAPH BEH-PROMISE-PARSE]`

Continuous modeling discipline:
- Every code task begins by verifying its architecture entity's closure.
- Every code task ends by re-running `chain_closure` on the affected slice.
- New promises discovered during coding → added to model → validators
  enforce closure before merge.

Ordering:
- **B′-4a (2w):** Promise type + parser + migration primitive.
- **B′-4b (2w):** Legacy adapters — safety net (all 3746 + 4 benchmarks
  pass under adapter).
- **B′-4c (2w):** New pipeline stages.
- **B′-4d (2w):** Projector matrix (deterministic base).
- **B′-4e (1-2w):** LLM layer required at construction.
- **B′-4f (1w):** SI&L-as-evidence.
- **B′-4g (1w):** `verify_entity_standalone` universal harness + CI gate.

### Phase B′-5 — Post-code hardening

- **T5.1** — 4 e2e benchmarks re-verified on native 3.0 path.
- **T5.2** — Coordination release: OCA + arch-agent migration guide.
- **T5.3** — Publish architecture-first-refactor skill as OpenCode
  superpower.

## Baseline Metrics (2026-09-12, pre-refactor)

Captured from `.architecture-model.yaml` after enrichment + intent-seeding
+ observability seeding + pipeline-completeness validator fix:

| Metric | Value |
|--------|------:|
| Actors | 4 |
| Capabilities | 97 |
| Behaviors | 154 |
| Components | 34 |
| Interfaces | 77 |
| Constraints | 2 |
| Layers | 7 |
| Relationships | 787 |
| Cap tree roots | 4 |
| Cap leaves (79%) | 77 |
| Cap→cap contains | 93 |
| Comp→cap realizes | 92 |
| Beh→cap traces-to | 6 |
| Beh→cap exercised-by | 0 |
| Caps with closed delivery chain | 0 / 97 |
| Pipeline anchor gaps (validator) | 0 |
| Exact-duplicate capability names | 3 pairs |
| Requirements (first-class attr) | 0 |
| Regen readiness | 65 / 100 (C) |
| Validator score | 38 |
| Test suite | 3746 passed, 104 skipped |
| Session commits | d0caf81 · d1acf64 · 32b288a · 9a713be · 4b5ccd0 · 36b87b1 |

## Guardrails (unchanged)

- Conventional Commits
- Never `git add -A`
- Never touch `.architecture-models/**`, `.DS_Store`, `sil.sqlite*`,
  auto-regen `.architecture/*` (context.md, structure.yaml, functional.yaml,
  relationships.yaml, inventory.json, validation.json,
  derived_requirements.yaml, learning/, component_test_map.json,
  test_map.json)
- `viewer.html` allowed on user's explicit exception
- Full test suite green after every commit; no batching
- No push
- No `pip install -e`
- Every entity + generated view gets ≤200-char `description`

## Risks

1. **A3 consolidation destructive to entity IDs** — mitigated by
   `superseded_by` + snapshot test.
2. **Deliver/verify inference heuristic** — WARNING severity + fix-proposal
   loop.
3. **Cap target ≤30 heuristic** — accept deterministic consolidator output.
4. **S0..S15 removal needs test audit first.**
5. **Schema 3.0 migration lossy on prose fields** — LLM re-derivation with
   digest-locked prompts; adapter path preserves 2.1 as fallback.
6. **Cost explosion under LLM-required pipeline** — budget cap per pipeline
   run in `policy.yaml`; clean entities skip LLM entirely.
7. **Prompt drift** — snapshot-locked at `tests/llm/test_prompt_fragments.py`.
8. **Non-determinism polluting artifacts** — LLM outputs cached by
   `(prompt_digest, model, temperature=0)`.

## Comparison Anchor

Full A / B / B′ tradeoff matrix preserved in the conversation transcript
that produced this plan (session 2026-09-12). Key axis: **Plan B′ preserves
all existing tests + benchmarks via legacy-adapter path**, unlike Plan B
which deleted `core/visualize.py` outright. Plan B′ trades slower initial
delivery for full reversibility until Phase B′-4g merges native 3.0.
