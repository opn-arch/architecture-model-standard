# G1 — Pipelines v3 Authored Fragment (Design)

**Status:** in-progress (2026-09-20)
**Depends on:** — (independent)
**Enables:** G2 (viewer re-render with pipelines visible), G5 (final promotion-strict sweep)

## Problem

The seven operational pipelines that define AMS as a running system —
**BEH-P1 EXTRACT**, **BEH-26 SLICE**, **BEH-27 SELF-IMPROVEMENT**,
**BEH-28 DEV-LOOP**, **BEH-LLM**, **BEH-SIL**, **BEH-FBK** — are
first-class citizens in the legacy schema-2.x model
(`.architecture-model.yaml`, L687–1650) but absent from every v3
source:

* `.architecture-model.v3.yaml` (pipeline_v3 output) — pure AST-derived,
  cannot synthesize authored conceptual flows.
* `.architecture/model/capabilities.v3.yaml` (authored fragment) —
  declares CAP-* + authored BEH-* for the substrate walk, but not the
  operational pipelines.

Consequences:

* `.architecture/viewers/v3_viewer.html` has zero pipeline nodes.
* Substrate walks (`promotion-strict`, `attribute-completeness`) never
  see the pipeline behaviors, so metrics under-report coverage.
* Downstream MCP tools (`architect_slice --focus=BEH-P1`) return empty
  for anything scoped to a pipeline.

## Non-Goals

* **Not** a mechanical port from `.architecture-model.yaml`. The 2.x
  entries are inspiration; the v3 authored form uses MBSE promises,
  not flat prose fields.
* **Not** the sub-sub behaviors (BEH-P1.1.1..BEH-P1.5.x). Those are
  stage-internal steps that a future v3-native decomposition walk
  should discover; hand-authoring them now would compete with that
  walk and force us to maintain two sources.
* **Not** cross-block flow edges (`triggers`) between pipelines. Those
  belong to a Phase-2 flow-modeling substrate
  (`docs/plans/2026-09-20-flow-modeling-substrate.md`) and are out of
  scope for G1.

## Scope

Author 7 top-level pipeline behaviors + their 30 direct sub-behaviors
in a new fragment `.architecture/model/pipelines.v3.yaml`. Auto-picked
up by `architecture_model.core.v3_loader.load_sources` (globs
`*.v3.yaml` in `.architecture/model/`, verified at `v3_loader.py:63`).

### Entities in scope

| Top-level | Direct subs (in-scope) |
|-----------|-----------------------|
| BEH-P1 (Run Extraction Pipeline) | BEH-P1.1 observe, BEH-P1.2 infer, BEH-P1.3 allocate, BEH-P1.4 relate, BEH-P1.5 specify, BEH-P1.6 contract, BEH-P1.7 validate, BEH-P1.8 decompose, BEH-P1.9 synthesize, BEH-P1.10 emit, BEH-P1.R recursive-decompose |
| BEH-26 (Slice-Scoped Context) | — |
| BEH-27 (Self-Improvement / Learning Loop) | — |
| BEH-28 (Development Loop) | — |
| BEH-LLM (Provider Layer) | BEH-LLM.1..BEH-LLM.8 |
| BEH-SIL (Structural Interface Layer) | BEH-SIL.1..BEH-SIL.8 |
| BEH-FBK (Feedback Journals) | BEH-FBK.1..BEH-FBK.4 |

**Total: 7 tops + 30 direct subs = 37 behaviors.**

### v3-native promise style

Each behavior carries five to seven promises following the R9 pattern
established in `capabilities.v3.yaml`:

* `PR-<id>-intent` (attribute: `intent`) — one-sentence purpose.
* `PR-<id>-goals` (attribute: `goals`) — outcome-focused list.
* `PR-<id>-requirements` (attribute: `requirements`) — non-negotiable
  constraints.
* `PR-<id>-success_criteria` (attribute: `success_criteria`) —
  measurable pass conditions.
* `PR-<id>-failure_modes` (attribute: `failure_modes`) — concrete
  ways this can break.
* `PR-<id>-constraints` (attribute: `constraints`) — substrate coupling
  (SI&L, LLM policy, etc.). Omit when nothing to say.
* `PR-<id>-verified_by` (attribute: `verified_by`) — explicit codebase
  artifacts backing the promises.

Every promise carries `owner_entity`, `delivered_from: null` (unless
delivered by a parent capability), `verified_by` (list of codebase
refs; empty list flips `status` to `open`), `status` (`verified` |
`open`), `gap_type` (null when verified), `provenance` (short comment
naming the source).

### Relationships in scope

* `contains` — parent → child within each pipeline block.
* `realizes` — every top-level pipeline realizes the appropriate
  capability from `capabilities.v3.yaml` (CAP-PB for BEH-P1, CAP-SL
  for BEH-26, CAP-DF for BEH-28; new CAP-* entries out of scope —
  BEH-27/LLM/SIL/FBK will trace to CAP-DF for now with a note).
* `traces-to` — sub-behaviors trace to the component that realizes
  them (BEH-P1.1 → COMP for `pipeline/observe.py`, etc.). Use the
  `pipeline_v3` COMP ids where they exist; fall back to
  `capabilities.v3.yaml`'s COMP-c5a72728 single-component allocation
  where sub-decomposition doesn't exist yet.

## File shape

```yaml
meta:
  schema_version: '3.0'
  project: architecture-model-standard
  subsystem: pipelines
  generated_by: hand-authored
  generated_at: '2026-09-20T00:00:00Z'
  source_root: .architecture/model/
  note: |
    Authored v3 counterparts of the seven operational pipelines that
    define AMS as a running system. Inspired by (not ported from) the
    schema-2.x entries at .architecture-model.yaml:687-1650. Scope:
    7 tops + 30 direct sub-behaviors + capability trace edges.
    Sub-sub behaviors (BEH-P1.1.1..BEH-P1.5.x) and cross-pipeline
    flow edges are deliberately out of scope — see
    docs/plans/2026-09-20-g1-pipelines-v3-fragment-design.md.

entities:
  behaviors:
  - id: BEH-P1
    name: run_extraction_pipeline
    promises: [...]
  # ... 36 more behaviors

relationships:
- {from: BEH-P1, to: BEH-P1.1, type: contains}
# ... contains + realizes + traces-to
```

## Exit criteria

1. `python -c "from architecture_model.core.v3_loader import load_v3_model; m = load_v3_model('.architecture-model.v3.yaml'); ids = {b['id'] for b in m['entities']['behaviors']}; print(sorted(i for i in ids if i.startswith(('BEH-P1', 'BEH-26', 'BEH-27', 'BEH-28', 'BEH-LLM', 'BEH-SIL', 'BEH-FBK'))))"` returns all 37 ids.
2. `python -m pytest tests/ -q` still passes (4517+ tests, no regressions).
3. `promotion-strict` walk on the merged v3 model shifts at least the
   7 tops from `insufficient-strict` toward `partial-strict` or
   `ready-to-code-strict`. Baseline (2026-09-20 HEAD `7270c0c`): 0
   ready / 13 partial / 512 insufficient across 525 entities.
4. `walk_coverage` meta-walk verdict remains stable (no new
   `dangling-ref` verdicts introduced by new relationship edges).

## Follow-ons (explicit non-goals for G1, filed for later)

* **G1.1** — sub-sub-behaviors decomposition via a new v3 walk that
  reads pipeline stage source files and derives step-level BEH-P1.X.Y.
* **G1.2** — flow-modeling substrate: cross-pipeline `triggers` edges
  (BEH-P1 triggers BEH-27 on completion, BEH-28 triggers BEH-P1 on
  save, etc.). See `docs/plans/2026-09-20-flow-modeling-substrate.md`.
* **G1.3** — dedicated capabilities for BEH-27/LLM/SIL/FBK if the
  narrative demands them (currently they trace to CAP-DF with a
  provenance note flagging the loose fit).
