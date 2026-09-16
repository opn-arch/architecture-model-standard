# AMS v3 — CAP-PB Walk (extract_architecture_from_code)

*Extends [2026-09-14 v3 SE walk](2026-09-14-v3-se-walk.md) and [2026-09-15 dev workflow walk](2026-09-15-dev-workflow-se-walk.md). Applies graph-walk-as-capability (CAP-DF.1) to the mature capability CAP-PB. Delivers semantic-attribute enrichment, a missing orchestrator behavior, the primary output interface, and two cross-cutting constraints — as an authored fragment, no pipeline change.*

**Date:** 2026-09-16
**Branch:** `feat/phase-5-fanout-provenance-family5`
**Artifacts:** [`.architecture/model/capabilities.v3.yaml`](../../.architecture/model/capabilities.v3.yaml) · [`.architecture/model/enrichment.v3.yaml`](../../.architecture/model/enrichment.v3.yaml) · [v3 viewer](../../.architecture/viewers/v3_viewer.html)

---

## Level 0 — Why walk CAP-PB now

Prior walks framed the standard (2026-09-14) and the dev loop (2026-09-15). Both identified the same gap: **pipeline_v3 emits 1 of 7 entity kinds** (components only). The mainline remediation is *not* to rewrite `emit.py` — it is to demonstrate that **graph-walk-as-capability (CAP-DF.1)** can close the gap through authored fragments merged at view time. This walk is that demonstration, applied to the most mature capability in the model.

The success criterion is narrow and testable: after the walk, the merged model contains all 7 entity kinds, CAP-PB carries the full semantic-attribute set (stakeholders, success criteria, failure modes, SLOs, assumptions, trade-offs), and every claim is either `verified` against source or explicitly `typed-gap` with a follow-up.

## Level 1 — Concept: what does CAP-PB actually promise?

**Definition (pre-walk):** `extract_architecture_from_code` — AST-scan a Python repo and emit an architecture model.

**Gap analysis before walk:**

| Semantic attribute | Present? |
|---|:---:|
| intent | ✓ |
| requirements | ✓ |
| stakeholders | ✗ |
| success_criteria | ✗ |
| failure_modes | ✗ |
| slos | ✗ |
| assumptions | ✗ |
| trade_offs | ✗ |

7 delivers-promises (one per stage behavior) were present but the capability itself was thinly modeled. The user-facing entry point — `architecture-model pipeline .` — was **not** modeled as a behavior; the 7 stages appeared as if they ran themselves.

**Result:** 6 new verified promises on CAP-PB (stakeholders, success_criteria, failure_modes, slos, assumptions, trade_offs) + 1 delivers-promise for the orchestrator + 2 typed-gap open questions (per-stage split, LLM enrichment seam) = **9 new promises on CAP-PB**.

## Level 2 — Sub-capability split? Adaptive-stop decision

Considered: split CAP-PB into CAP-PB.1 (observe) / CAP-PB.2 (structure) / CAP-PB.3 (emit) mirroring the 3-phase pipeline.

**Rejected.** Adaptive-depth rule applied: further decomposition here would be organizational, not behavioral. Each of the 8 stage behaviors is already 1:1 with a `pipeline_v3/*.py` module, independently testable, and independently traced. Sub-caps would add nodes without adding promises. Kept a flat 8-behavior structure (7 stages + 1 orchestrator).

Recorded as design rationale on CAP-PB via the trade_offs promise: *"flat behavior structure over sub-capabilities: stages are behaviorally independent; sub-caps would be organizational-only."*

## Level 3 — Behavior enrichment (per stage + orchestrator)

Before the walk, each of BEH-scan, BEH-derive-promises, BEH-cluster, BEH-link, BEH-containerize, BEH-verify, BEH-publish carried only `intent`. Enrichment added `verified_by` (test module path) and `provides` (typed output artifact) to all 7, plus `failure_modes` where the stage has known misgrouping/cycle/drift risks.

| Behavior | +verified_by | +provides | +failure_modes |
|---|:---:|:---:|:---:|
| BEH-scan | ✓ `tests/pipeline_v3/test_scan.py` | ✓ `Module[]` | — |
| BEH-derive-promises | ✓ | ✓ `Promise[]` | — |
| BEH-cluster | ✓ | ✓ `Cluster[]` | ✓ name-prefix misgroup |
| BEH-link | ✓ | ✓ `Edge[]` | ✓ import cycles, dynamic imports |
| BEH-containerize | ✓ | ✓ `Component[]` | — |
| BEH-verify | ✓ | ✓ `ValidationReport` | ✓ schema drift |
| BEH-publish | ✓ | ✓ `.architecture-model.v3.yaml` | — |
| **BEH-run-pipeline (new)** | ✓ `tests/pipeline_v3/test_orchestrator.py` | ✓ resumable execution | — |

**BEH-run-pipeline** is the actual user-triggered entry point (`architecture-model pipeline .`). It orchestrates the 7 stages, handles resumption from the cache, and is what actors trigger. Modeling it as a first-class behavior lets `ACT-developer` and `ACT-ci` roll up cleanly through a single edge instead of triggering 7 stage-behaviors individually.

## Level 4 — Component + Interface

**Component (unchanged):** All 8 behaviors currently `traces-to COMP-c5a72728` (`architecture_model.pipeline_v3`). The stages are physically one Python subpackage.

**Deferred question — per-stage component split.** Splitting COMP-c5a72728 into COMP-scan / COMP-derive-promises / ... would enable per-stage SI&L badges, per-stage validation scores, and per-stage failure isolation. It requires `pipeline_v3/emit.py` code changes (write one component per stage instead of one component per package) — out of walk scope. Captured as:

- Promise `PR-CAP-PB-open-per-stage-split` (status: `open`, gap_type: `deferred-split`)

**Interface (new):** `IF-model` — `architecture_model_yaml`. The pipeline's primary output was previously unmodeled. Added with 2 promises (intent, requirements) and two relationships:

- `CAP-PB exposes IF-model`
- `BEH-publish produces IF-model`

This is the second entity kind delivered by the walk (after `interface` — with actors, constraints, and layers coming from `enrichment.v3.yaml`).

## Level 5 — Constraints + actor retargeting

**Two new constraints on CAP-PB:**

| ID | Intent |
|---|---|
| `CONS-ast-only` | Extraction uses AST parsing only — no runtime execution of target code. Safe on untrusted repos. |
| `CONS-resumable` | Pipeline is resumable from cache: rerunning after failure resumes at the failed stage. |

Both added via `enrichment.v3.yaml` with `CAP-PB constrained-by CONS-*` edges.

**Actor triggers retargeted.** Before: `ACT-developer` and `ACT-ci` triggered `BEH-scan` (three edges, one dangling for `BEH-publish`). After: both actors trigger `BEH-run-pipeline` (two edges). This corrects the model — no real actor triggers `BEH-scan` in isolation — and cleans up the ConOps view.

**Layer allocation:** `L-tooling contains CAP-PB` and `L-tooling contains CAP-SL` — CAP-PB and CAP-SL are tooling capabilities delivered by the CLI + pipeline, distinct from CAP-DF which is a developer-workflow capability.

## Adaptive-stop — why we did not go to Level 6

Level 6 would be individual stage-internal decomposition (e.g., BEH-scan → BEH-scan.parse + BEH-scan.walk-imports). Skipped because:

1. Each stage is already 1:1 with a test module — verification is per-stage.
2. Sub-behaviors would not add new promises; they would add navigation depth without insight.
3. The failure modes we care about (name-prefix misgroup, import cycles, schema drift) are already promised at Level 3.

Rule: stop when further decomposition would not change what a downstream consumer (SE reviewer, LLM regenerator) can *verify* or *act on*.

## Fragment delta

**`.architecture/model/capabilities.v3.yaml`** — +~275 lines
- CAP-PB: +9 promises (delivers, stakeholders, success_criteria, failure_modes, slos, assumptions, trade_offs, 2 open typed-gaps)
- BEH-run-pipeline: new behavior, 3 promises
- BEH-scan…BEH-publish: +verified_by, +provides on each; +failure_modes on 3
- IF-model: new interface, 2 promises
- +5 relationships (contains, exposes, traces-to, triggers, produces)

**`.architecture/model/enrichment.v3.yaml`** — +~55 lines
- CONS-ast-only, CONS-resumable: 2 new constraints, 1 intent promise each
- Retargeted 3 actor triggers → 2 (developer+ci → BEH-run-pipeline)
- +2 constraint edges, +2 layer→cap edges

**Build results:**

| | Before | After | Δ |
|---|---:|---:|---:|
| Entities | 63 | **67** | +4 |
| Promises | 739 | **772** | +33 |
| Relationships | 113 | **121** | +8 |
| Kinds present | 6 | **7** | +1 |

`gap_type_hist` now includes `deferred-split: 1` and `llm-seam: 1`. Both are follow-ups, not deficiencies — they are explicitly modeled open questions.

## ConOps impact preview

Before: `ACT-developer → CAP-DF`, `ACT-developer → BEH-scan`, `ACT-ci → BEH-scan`, `ACT-ci → BEH-publish`, `ACT-llm → CAP-DF`, `ACT-se → CAP-DF` — a messy mix of capability-level and behavior-level edges.

After (regenerated Mermaid, verified):

```
ACT-ci        → CAP-PB   (rolled up via BEH-run-pipeline)
ACT-developer → CAP-DF
ACT-developer → CAP-PB   (rolled up via BEH-run-pipeline)
ACT-llm       → CAP-DF
ACT-se        → CAP-DF
```

All 4 actors now roll up cleanly to top-level capabilities. Functional view unchanged (still 7 capability nodes, 4 edges) — the enrichment did not touch the capability tree.

## Verification

- ✅ `python scripts/build_v3_viewer.py` — clean build
- ✅ Byte-determinism rerun-diff — deterministic
- ✅ `node --check` on extracted logic JS — `JS_OK`
- ✅ ConOps + Functional Mermaid regenerated; ConOps edges as expected, Functional unchanged
- ✅ `kinds_present` now spans all 7 entity kinds

## Follow-ups

1. **Per-stage component split** (`PR-CAP-PB-open-per-stage-split`, gap_type: `deferred-split`) — requires `pipeline_v3/emit.py` change to emit one component per stage. Enables per-stage SI&L badges and validation scores. Estimated: 1 CAP-DF loop.
2. **LLM enrichment seam** (`PR-CAP-PB-open-llm-derive-enrichment`, gap_type: `llm-seam`) — Part 3 work. Wire an LLM provider to synthesize verified_by/failure_modes/slos promises from source when a walk starts from an empty template. Deferred to LLM part of roadmap.
3. **CAP-SL enrichment walk** — CAP-SL currently has zero contained behaviors and zero actor triggers. Same walk pattern applies. Estimated: 1 CAP-DF loop of similar size.

---

**This is the third CAP-DF loop in the branch history.** Commit `1a721a5` was viewer+notes, `ef632b9` was the capability tree, and this commit is the CAP-PB semantic enrichment. Each loop is one context window, one commit, one authored fragment.
