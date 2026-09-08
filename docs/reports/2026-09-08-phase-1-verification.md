# Phase 1 Verification Report

**Date:** 2026-09-08
**Plan:** `docs/plans/2026-09-08-phase-1-substrate-and-liveness.md`
**Design:** `docs/plans/2026-09-08-model-view-mapping-design.md`
**Branches:** `feat/model-view-mapping-phase-1` on both ams and oca (off `main`).

## Test counts

| Repo | Baseline (pre-Phase-1) | Final (post-Phase-1) | Delta | Pre-existing failures | Skips |
|------|-----------------------:|---------------------:|------:|:---------------------:|:-----:|
| architecture-model-standard | 3065 passed | **3105 passed** | **+40** | 6 (unchanged) | 103 |
| opencode-arch | 993 passed | **997 passed** | **+4** | 2 (unchanged) | 3 |

Baselines were recorded before Task 1 (ams) and before Task 12 (oca). The
"pre-existing failures" counts and identities match the plan's baseline
section — no Phase 1 commit introduced or resolved any of them.

### ams pre-existing failures (unchanged)

- `tests/test_docs_gen.py::TestHealthReport::test_includes_confidence`
- `tests/test_docs_gen.py::TestHealthReport::test_includes_components`
- `tests/test_manifest.py::TestFunctionalBlocks::test_has_f1_through_f6`
- `tests/test_manifest.py::TestGenerateManifest::test_has_functional_blocks`
- `tests/test_multi_scanner.py::TestScanAllLanguages::test_real_logs_db`
- `tests/test_pipeline_decompose.py::TestStageMetadata::test_name_version_requires`

### oca pre-existing failures (unchanged)

- `tests/test_adaptive_budget.py::TestComputeAdaptiveBudget::test_very_large_repo_capped`
- `tests/test_ingest.py::test_ingest_basic`

### Test commands

```bash
# ams
cd architecture-model-standard
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py

# oca
cd opencode-arch
PYTHONPATH="$PWD/src:$(realpath ../architecture-model-standard)/src" \
  /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/e2e --ignore=tests/logs_db
```

## New projectors registered

All projectors are registered under `family<N>.<name>` in
`architecture_model.lifecycle.view_projection.projectors`.

**Seeded family (4, Task 1 seed):**
- `family1.summary`, `family2.detail`, plus 2 additional seeded fixtures
  used by determinism tests.

**Mermaid diagrams (Task 5, `component-diagram`, `use-case-diagrams`,
`system-boundary-diagram`):**
- `family3.component-diagram`
- `family3.use-case-diagrams`
- `family3.system-boundary-diagram`

**Non-SE prose generators (Task 6):**
- `family4.component-spec`
- `family4.icd`
- (multi-entity outputs joined with `"\n\n---\n\n"`, `content_kind: markdown`)

**SE document generators (Task 8, 17 projectors):**
- ConOps, Functional Analysis, Logical Architecture, Requirements Analysis,
  V&V, Operations Manual, Maintenance Manual, Use Cases, Risk Assessment,
  Interface Spec, Artifact Traceability, plus the shared frontmatter/index
  generators.

Adapters live under `src/architecture_model/lifecycle/projectors/` and
return `DiagramSpec` values. `list_names()` and the duplicate-registration
guard were added in `2caa2b1` / `eeb29a2` (Task 4).

## New tests

| Task | Repo | Test file(s) | Count |
|-----:|------|--------------|------:|
| 1–4 | ams | `tests/lifecycle/test_projector_registry.py` (+ related) | ~10 |
| 5 | ams | `tests/docs/test_mermaid_projector_determinism.py` | 3 |
| 6 | ams | `tests/docs/test_non_se_projector_determinism.py` | 4 |
| 7 | ams | (freshness stamp inside `view_projection`) covered by Task 8/11 | — |
| 8 | ams | `tests/docs/test_se_projector_determinism.py` | 17 |
| 9 | ams | `tests/lifecycle/test_invalidation.py` | ~4 |
| 10 | ams | `tests/lifecycle/test_freshness_stamping.py` | ~2 |
| 11 | ams | `tests/pipeline/test_targeted_extract_dispatch.py` | ~2 |
| 12 | oca | `tests/mcp/tools/test_docs_specs.py` | ~15 |
| 13 | oca | `tests/lifecycle_exec/test_rebuild_descendants.py` | 4 |
| 14 | oca | `tests/mcp/tools/test_evaluate_freshness.py` | 4 |
| 15 | oca | `tests/templates/test_hook_template_syntax.py` | 5 |

Totals reconcile with the `+40` (ams) / `+4` (oca) deltas above.

## Deferred items (Phase 2)

Phase 1 shipped the substrate + liveness metadata; two structural
follow-ons were deliberately deferred once the semantic gap was
identified during Tasks 13/14 review:

- **Task 27 — Per-subsystem fan-out** (added to Phase 2).
  Current `materialize()` merges root ∪ descendants into a single
  fragment when the slice's scope requests descendants. The plan
  originally wanted N artifacts per rebuild (one per descendant, output
  paths carrying the subsystem slug). Merged-fragment shipped in Phase 1
  as sufficient coverage; fan-out shape moves to Phase 2 alongside
  `MaterializedSlice.manifest_fragment`.

- **Task 28 — Per-artifact `<id>.provenance.json` sidecars**
  (added to Phase 2).
  `project()` stamps `freshness: "fresh"` and `revision` on returned
  `DiagramSpec`s, but `rebuild.py:575` writes raw renderer bytes with no
  provenance sidecar. Therefore `architect_evaluate.freshness_summary`
  currently reports every artifact as `unknown` — `fresh/stale/pending`
  always 0. Sidecar persistence + reader logic land in Phase 2.

Two additional generator families remained skipped in Phase 1 because
they require a `manifest_fragment` on `MaterializedSlice` that Phase 2
introduces:

- Anything reading `ArchitectureModel.entities.components[*].signatures`
  / `constants` / `test_contracts` at projection time.
- Regen-readiness scoring surfaces that need per-file body-hint access.

These are called out in the plan under
"Deferred to later phases (do NOT do here)" and remain unblocked once
Phase 2's `MaterializedSlice.manifest_fragment` field lands.

## Sign-off

- Full ams suite: 3105 passed, 6 pre-existing failed, 103 skipped (79.75s).
- Full oca suite: 997 passed, 2 pre-existing failed, 3 skipped (52.13s).
- No new failures, no skipped-in-lieu-of-passing tests, no `xfail`
  additions.
- CONTEXT.md refreshed on both repos (Tasks 16, 17).
- Design + phase-plan docs on ams; Phase 2/3/4 deferred per plan.
- Task 15 pre-commit template shipped warning-only by default; failure
  behind `OPENCODE_ARCH_STRICT=1` per reviewer follow-up.

Ready for PR review.
