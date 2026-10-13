# Constraint impact walk, build-time diagnostics, and CAP-DF loop close

**Date:** 2026-09-16
**Follows:** `3c6950b fix(model)` — realizes direction fix
**Scope:** Single commit combining 5 CAP-DF-loop items delivered
walk-fashion where the pattern applied.

## Motivation

The CAP-DF loop pattern is `view → note → walk/author → re-extract → view`.
After L9 (realizes-direction fix), a full cycle was owed: browse the
newly-populated diagrams, harvest lessons, extend the walk substrate,
and enrich the realizer that now anchors every capability's realization
chain. This report documents that cycle end-to-end.

## Changes

### 1. Constraint impact walk (6th diagram helper)

`_mermaid_constraint_impact(entities_by_kind, relationships, cons_id)`
— extends the 1-hop constraint case in `_mermaid_realization` to a
2-hop impact graph. Walks `constrained-by` inbound (hop 1), then per
constrained-entity kind, follows the appropriate downstream edge:

```
capability  -> outbound contains  (sub-caps / behaviors affected)
component   -> outbound contains  (sub-components affected)
behavior    -> inbound  traces-to (components that implement it)
interface   -> inbound  exposes    (components exposing it)
```

Silent-skip when hop 2 is empty (identical to 1-hop realization —
no new info). Stamped on constraint records as
`constraint_impact_mermaid` / `constraint_impact_refs`. All 6
constraints in the v3 model populated (refs 5-15 nodes each).

Placed after cross-flow, before decomposition/realization in the
entity page (same additive pattern as cross_flow vs flow).

### 2. Build-time diagnostics (L2 lesson realized)

Two pure-function diagnostic passes stamped into
`payload["diagnostics"]`:

**`_lint_edge_note_directions(relationships)`** — scans every edge for
note-text patterns that describe the OPPOSITE direction of the stored
edge. Catches:

- "X is realized by Y" on edge `X -realizes-> Y` (expect `Y -> X`)
- "X depends on Y" on edge `Y -depends-on-> X` (expect `X -> Y`)
- "X is contained in Y" on edge `X -contains-> Y` (expect `Y -> X`)
- "X exposes Y" on edge `Y -exposes-> X` (expect `X -> Y`)

Returns deterministic `list[{from, to, type, note, warning}]`. Would
have caught the L9 bug at build time. Currently fires zero warnings
(clean after L9 fix).

**`_realization_skip_reasons(entities_by_kind, out_edges, in_edges)`**
— for every entity that has NO `realization_mermaid` populated but
DOES have adjacent edges of the shape the walker examines, records a
one-line reason. Currently fires zero silent-skips. Present as
tripwire.

Both surface in three ways:
- Console: `WARN:` lines at build time
- Payload: `data.diagnostics` for programmatic consumers
- Viewer: yellow banner on overview page when either is non-empty

### 3. COMP-c5a72728 enrichment (3 new promises)

Added to realizer of CAP-PB + CAP-SL to give realization chains
substantive hop-2 content:

- `stage_decomposition` — the 8 pipeline_v3 stages (scan → derive
  → cluster → link → containerize → verify → publish → orchestrator),
  each with typed intermediate + test file citation
- `verification` — self-application, 95+ tests, byte-determinism
  round-trip, arch-agent benchmark reference
- `assumptions` — input tree shape, `AMS_DETERMINISTIC_NOW` pinning,
  AST-only constraint, in-memory intermediate size

Promise total: 775 → 778 (delta +3).

### 4. CAP-DF `lessons_learned` (L9-L11)

- **L9** — follow-up notes framed as "add one edge" can hide systemic
  direction bugs; probe the CONSUMER contract before adding data.
- **L10** — silent-skip masks bugs; mitigate with build-time diagnostic
  passes + in-viewer diagnostics banner. Fires zero warnings today
  (L9 fix cleared all).
- **L11** — additive walks in a separate helper + separate stamped
  field beat in-place extension. Reinforces L6 substrate. Same
  pattern for constraint_impact vs realization as cross_flow vs flow.

Content total: 8 → 11 lessons.

## Verification

- Deterministic build (double-run diff clean HTML + JSON)
- `node --check` clean on extracted script
- Diagnostics banner: `direction_warnings=[]`, `realization_skip_reasons={}`
- All 6 constraints have `constraint_impact_mermaid` populated
- COMP-c5a72728: 32 promises across 10 attrs (was 29 / 7)
- CAP-DF: 11 lessons (was 8)
- Totals: 67/130/778/61 (entities/edges/promises/gaps)

## Lessons on the CAP-DF loop itself

The full cycle in this session was: view (L9 diagrams) → note (L9-L11
harvested) → walk (constraint_impact + diagnostic passes) → author
(COMP-c5a72728 enrichment) → re-extract → view (banner clean, diagrams
populated). Elapsed: ~1 session hour. Zero broken states, zero
rework. The walk-fashion delivery (each item pattern-matched to the
same substrate) is what made batching possible without cognitive
overhead.

The diagnostics banner is the mechanism-level payoff of L10: the
loop now has a tripwire built into the artifact it produces. Future
direction bugs will surface on the very next build.

## Files changed

- `scripts/build_v3_viewer.py`
  - `_mermaid_constraint_impact` helper (~L1034)
  - `_lint_edge_note_directions` helper (~L1119)
  - `_realization_skip_reasons` helper (~L1165)
  - Stamping + diagnostics collection in `_build_payload` (~L1385)
  - Payload emits `diagnostics` (~L1476)
  - JS `cimpCard` in `selectEntity` + render-targets array
  - Diagnostics banner in `showOverview`
- `.architecture/model/enrichment.v3.yaml` — 3 new COMP-c5a72728 promises
- `.architecture/model/capabilities.v3.yaml` — L9-L11 in CAP-DF lessons + verified_by refs
- `.architecture/viewers/v3_viewer.html` (regenerated)
- `.architecture/viewers/v3_viewer_data.json` (regenerated)
- `docs/reports/2026-09-16-constraint-impact-and-diagnostics.md` (this file)

## Follow-ups

- Model-side: no leftover items from the fc474bc → 3c6950b → this thread.
- Substrate: 6 walks in place. Next candidate would be constraint-driven
  diagnostics (e.g., surface `CONS-determinism` impact on components
  that lack `verification` promises).
