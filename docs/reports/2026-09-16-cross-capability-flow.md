# Cross-capability flow diagram (5th entity-page walk)

**Date:** 2026-09-16
**Commit:** feat(viewer): add cross-capability flow walker
**Follows:** `fc474bc feat(model)` — 8 lessons + 3 CAP-DF triggers edges
**Precedes:** none (final of Task B follow-ups)

## Motivation

After Task B added three `triggers` edges connecting `BEH-view-note →
BEH-walk-author`, `BEH-walk-author → BEH-run-pipeline`, and `BEH-view-note →
COMP-VIEWER`, the flow diagrams on `CAP-DF` and `CAP-DF.1` remained empty.
Root cause: the existing `_mermaid_pipeline` helper only walks `triggers`
edges whose endpoints are behaviors **directly contained** by the target
capability. It cannot represent flows that cross sub-capability boundaries
or reach into a sibling capability. That is exactly the shape of every
edge landed in Task B.

## Design

Added `_mermaid_cross_capability_flow(entities_by_kind, relationships,
cap_id)`, a fifth entity-page graph-walk helper following the pattern
established for decomposition / realization / neighbors (helper returns
`(mermaid_string, refs) | None`; payload stamped on record; single JS
render loop iterates a `targets` array).

Walk algorithm:

1. **Descendant behavior set** — transitively walk `contains` edges from
   `cap_id` and collect every behavior reachable through any depth of
   sub-capabilities.
2. **Touching triggers** — collect every `triggers` edge where at least
   one endpoint is in the descendant set.
3. **Grouping** — internal behaviors grouped into sub-capability
   subgraphs by walking each internal behavior's `contains` chain
   upward until a direct child of `cap_id` is found (that child names
   the subgraph). External endpoints go into a single "External"
   subgraph.
4. **Silent skip** — return `None` when the descendant set has no
   touching triggers (avoids noisy empty diagrams).
5. **Duplicate suppression** — payload-stamping site only writes
   `cross_flow_mermaid` when its string differs from `flow_mermaid`,
   avoiding two identical cards for capabilities whose flow is fully
   internal (single-cap case).

Card ordering on entity page: cross-flow **first**, then decomposition,
realization, per-attribute promise cards, neighbors, notes. Placing
cross-flow first surfaces cross-boundary orchestration before local
structure — matches the "outside-in" reading order SEs expect.

## Data validation

```
CAP-DF   : flow=False xflow=True xrefs=9   (both CAP-DF.1, CAP-DF.2 subgraphs + external BEH-run-pipeline)
CAP-DF.1 : flow=False xflow=True xrefs=5   (external BEH-run-pipeline, BEH-view-note)
CAP-DF.2 : flow=False xflow=True xrefs=5   (external BEH-run-pipeline, BEH-walk-author)
CAP-PB   : flow=True  xflow=True xrefs=10  (single-cap flow extended by cross-boundary edges to view-browse, walk-author)
```

Duplicate-suppression working: capabilities whose only triggers stay
within a single sub-capability get no separate cross-flow card.

## Verification

- `python scripts/build_v3_viewer.py` — clean build, 67 entities, 130
  edges, 775 promises, 60 gaps (unchanged totals from `fc474bc`).
- Determinism: two consecutive builds diff-clean on both HTML and JSON
  outputs.
- `node --check` on extracted `<script>` — clean.
- Data assertions above run against `v3_viewer_data.json`.

## Lessons

1. **Graph-walk pattern generalizes to a 5th case with zero framework
   change** — the helper-returns-tuple-or-None + payload-stamp + JS
   render-targets-array contract remains stable across five distinct
   walks (pipeline, decomposition, realization, neighbors, cross-flow).
   This is now proven pattern territory, not exploratory design.
2. **Duplicate-suppression at the stamp site, not the walker** — the
   walker is pure (always emits when data exists); the payload stamper
   decides whether the result is redundant. Keeps the walker
   composable and testable in isolation.
3. **Card ordering encodes reading direction** — cross-flow-first
   surfaces cross-boundary orchestration before local decomposition,
   matching how SEs read: context → structure → detail.

## Files changed

- `scripts/build_v3_viewer.py`
  - New helper `_mermaid_cross_capability_flow` (~L907)
  - Payload stamping in capabilities-only block (~L1184)
  - JS `xflowCard` in `selectEntity` (~L1597)
  - `targets` array entry `[xflowCard.id, 'cross_flow']` (~L1679)
- `.architecture/viewers/v3_viewer.html` (regenerated)
- `.architecture/viewers/v3_viewer_data.json` (regenerated)
- `docs/reports/2026-09-16-cross-capability-flow.md` (this file)

## Follow-ups (unchanged from `fc474bc`)

- Add `COMP-2 realizes CAP-PB` edge to give CAP-PB a realization_mermaid.
