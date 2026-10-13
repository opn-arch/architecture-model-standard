# AMS v3 — CAP-PB Stage Triggers + Pipeline View (Task A)

*Follow-up to [2026-09-16 CAP-PB walk](2026-09-16-cap-pb-walk.md). Closes the stage-to-stage flow gap identified in the behavior-flow analysis by asserting 6 `triggers` relationships and rendering a dedicated Pipeline SE view in the v3 viewer.*

**Date:** 2026-09-16
**Branch:** `feat/phase-5-fanout-provenance-family5`
**Artifacts:** [`.architecture/model/capabilities.v3.yaml`](../../.architecture/model/capabilities.v3.yaml) · [v3 viewer](../../.architecture/viewers/v3_viewer.html) · [prior CAP-PB walk](2026-09-16-cap-pb-walk.md)

---

## Motivation

After the CAP-PB walk landed, a behavior-flow analysis found that the merged model contained the 8 CAP-PB behaviors and 1 orchestrator→scan trigger, but was silent on the 6 stage-to-stage edges that actually make the pipeline a pipeline. The model asserted *what runs* (`CAP-PB contains BEH-scan..BEH-publish`) but not *in what order*. Every SE consumer had to read `pipeline_v3/orchestrator.py` to recover the sequence.

Task A closes this gap. Task B (upcoming) will close the cross-pipeline dev loop.

## Model delta

**`.architecture/model/capabilities.v3.yaml`:**

Six `triggers` relationships appended:

```yaml
- {from: BEH-scan,            to: BEH-derive-promises, type: triggers}
- {from: BEH-derive-promises, to: BEH-cluster,         type: triggers}
- {from: BEH-cluster,         to: BEH-link,            type: triggers}
- {from: BEH-link,            to: BEH-containerize,    type: triggers}
- {from: BEH-containerize,    to: BEH-verify,          type: triggers}
- {from: BEH-verify,          to: BEH-publish,         type: triggers}
```

One `verified` promise added on `BEH-run-pipeline` (`PR-BEH-run-pipeline-sequence`) documenting the sequence in prose, evidenced by `src/architecture_model/pipeline_v3/orchestrator.py`.

**Build result deltas:**

|  | Before | After | Δ |
|---|---:|---:|---:|
| Entities | 67 | 67 | 0 |
| Promises | 772 | **773** | +1 |
| Relationships | 121 | **127** | +6 |
| `gap_type_hist` | (unchanged) | (unchanged) | — |
| `kinds_present` | 7 | 7 | 0 |

## Pipeline SE view

New view registered as `se_views["pipeline"]`, sidebar link "CAP-PB Pipeline Flow" placed between ConOps and Functional. Rendered as a `flowchart LR` Mermaid diagram with per-kind color coding mirroring the v2 pipeline-dashboard palette:

- **Actors** (round, blue border) — `ACT-developer`, `ACT-ci`
- **Orchestrator** (bold rect, purple border) — `BEH-run-pipeline`
- **Stages** (rect, violet border, grouped in `STAGES` subgraph, ordered by topological sort of `triggers` edges) — 7 nodes
- **Output interface** (parallelogram, green border) — `IF-model`

**Layout, left to right:**

```
Actors → BEH-run-pipeline → [scan → derive-promises → cluster → link
                             → containerize → verify → publish] → IF-model
```

The stage ordering is derived deterministically from `triggers` edges via topological sort (Kahn's algorithm, tiebreak by id). If the model's `triggers` chain changed, the diagram would re-order automatically — no hand-maintained sequence.

**Drilldown** reuses the existing entity-chip mechanism: below the diagram, each referenced entity appears as a clickable chip → opens its entity page → surfaces `verified_by`, `provides`, `failure_modes`, and all other promises. No new panel machinery.

## Verification results

- ✅ `python scripts/build_v3_viewer.py` — clean build
- ✅ Byte-determinism rerun-diff — `DETERMINISTIC`
- ✅ `node --check` on extracted JS — `JS_OK`
- ✅ `se_views["pipeline"]["mermaid"]` inspected — 7-stage chain in expected order, actor edges, orchestrator edge, IF-model produce edge, `classDef` bindings correct
- ✅ `totals` = `{entities: 67, promises: 773, relationships: 127}` as predicted
- ✅ `gap_type_hist` unchanged from prior commit

## What this changes for a downstream reader

Before this commit, an SE reviewing the model in the viewer could see the 8 CAP-PB behaviors listed under CAP-PB but had no visual signal of ordering or data flow. The Functional view showed capabilities only; the Use Cases view showed actor→behavior triggers. Neither answered "how does extract *run*?"

After this commit, the Pipeline view is that answer, in one Mermaid diagram, and every edge in the diagram is a `git blame`-traceable model claim rather than a hand-drawn visualization. Extending the pipeline (e.g., inserting a new stage) requires exactly one model edit — a new `triggers` edge — and the view regenerates.

## Task B preview

Three cross-pipeline edges remain unmodeled:

1. `BEH-walk-author` → `BEH-run-pipeline` (fragment YAML feeds re-extract)
2. `BEH-run-pipeline` → `BEH-view-browse` (IF-model consumed by viewer)
3. `BEH-view-note` → `BEH-walk-author` (notes seed the next walk)

Adding these closes the CAP-DF loop as an assertable subgraph. Task B will also extend the Pipeline view (or add a companion "Dev Loop" view) to render all 16 behaviors across 4 pipelines with cross-pipeline edges highlighted.

---

**Commit:** `feat(model+viewer): CAP-PB stage triggers + pipeline flow SE view`
