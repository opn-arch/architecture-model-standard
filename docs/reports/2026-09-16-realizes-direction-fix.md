# Fix realizes direction — enable realization diagrams for all 5 affected entities

**Date:** 2026-09-16
**Follows:** `6af2823 feat(viewer)` — cross-capability flow walker
**Category:** model correctness

## Problem

Investigation for the `COMP-2 realizes CAP-PB` follow-up (from `fc474bc`)
revealed the follow-up description was too narrow. The actual defect was
that **all three** `realizes` edges in `.architecture/model/capabilities.v3.yaml`
were stored in the wrong direction:

```
CAP-PB    → realizes → COMP-c5a72728   ← reversed
CAP-SL    → realizes → COMP-c5a72728   ← reversed
CAP-DF.2  → realizes → COMP-VIEWER     ← reversed
```

The `_mermaid_realization` walker (`scripts/build_v3_viewer.py:825-833`)
for `kind == "capability"` expects `ins_by(entity_id, "realizes")` —
i.e. incoming `realizes` edges — matching the standard convention
"component **realizes** capability". Even the notes on the edges read
"CAP-PB is realized by pipeline_v3", which agrees with the walker and
disagrees with the stored direction.

Consequence: **no** capability or component in the v3 model had a
`realization_mermaid` populated. The walker was silently returning
`None` because hop 1 was empty in every case.

## Fix

Reversed all three edges to `COMP → realizes → CAP` and updated the
notes to match. No walker code change.

## Verification

Post-fix, all five affected entities carry `realization_mermaid`:

```
CAP-PB           realiz=True refs=2   [CAP-PB, COMP-c5a72728]
CAP-SL           realiz=True refs=2   [CAP-SL, COMP-c5a72728]
CAP-DF.2         realiz=True refs=2   [CAP-DF.2, COMP-VIEWER]
COMP-c5a72728    realiz=True refs=4   [CAP-PB, CAP-SL, COMP-c5a72728, L-tooling]
COMP-VIEWER      realiz=True refs=3   [CAP-DF, CAP-DF.2, COMP-VIEWER]
```

Component-side realization automatically picks up hop 2 through
`contains` (L-tooling → COMP-c5a72728, CAP-DF → CAP-DF.2), giving richer
chains for components than for capabilities-as-leaves.

- Deterministic build (double-run diff clean on HTML + JSON).
- `node --check` clean on extracted script.
- Totals stable: 67 entities, 130 edges, 775 promises.
- Gaps: 60 → 61 (one previously miscounted `unrealized` corrected).

## Lessons

1. **Follow-up notes can be too narrow.** The "add COMP-2 realizes CAP-PB
   edge" note framed this as a missing single edge. Investigation
   revealed a systemic direction bug affecting 3 edges and 5 entities.
   Always probe the walker/consumer contract before adding data.
2. **Silent-skip is a double-edged sword.** The walker's decision to
   return `None` when hop 1 is empty is correct — it prevents noise —
   but it also masked this bug for months. Consider a `--strict-realiz`
   diagnostic mode in the viewer that logs skipped entities so
   systemic direction issues surface early.
3. **Note-text can validate edge direction.** The three notes all said
   "X is realized by Y" — semantically `Y → realizes → X` — which
   directly contradicted the stored `X → realizes → Y`. A linter that
   checks note text against edge direction would have caught this.

## Files changed

- `.architecture/model/capabilities.v3.yaml` — 3 edges reversed,
  notes updated with L9 provenance
- `.architecture/viewers/v3_viewer.html` (regenerated)
- `.architecture/viewers/v3_viewer_data.json` (regenerated)
- `docs/reports/2026-09-16-realizes-direction-fix.md` (this file)
