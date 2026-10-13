# Unrealized-capability walk (shelf item #2, L17)

**Date:** 2026-09-16
**Scope:** 8th walk on the v3 viewer substrate — capability-level realization audit.
**Loop position:** CAP-DF self-improvement, shelf item #2 of 4 (last in the batch).

## Goal

Close the audit loop started by the compliance walk (L12–L15, promise-tier
level) by adding a capability-tier walk that answers, per capability:
"is this capability realized, and are its promises verified?"

## Substrate

Four pure helpers in `scripts/build_v3_viewer.py`, wired into `_build_payload`:

- `_capability_realization_status(cap_id, ebk, rels) -> dict | None` —
  classifier. Returns `{cap_id, realizer_count, realizers,
  open_promise_count, open_promise_ids, severity}`. Severity from the
  cartesian of (0 vs ≥1 realizers) × (0 vs ≥1 open promises):

  | realizers | open promises | severity      |
  |----------:|:-------------:|---------------|
  |         0 |      0        | `unrealized`  |
  |         0 |     ≥1        | `critical`    |
  |        ≥1 |     ≥1        | `partial`     |
  |        ≥1 |      0        | `ok`          |

- `_unrealized_capability_summary(ebk, rels) -> list[dict]` — model-level
  audit. Deterministically sorted by (severity_rank, cap_id). Silent-skips
  the `ok` case.

- `_mermaid_unrealized(ebk, rels, cap_id) -> tuple[body, refs] | None` —
  per-cap Mermaid card. Silent-skips `ok` and unknown ids. Non-ok cases
  render the capability node, its realizer components (if any), a
  sentinel `NO_REALIZER{{"(no realizer)"}}` when unrealized, and
  `OPEN_{pid}{{"OPEN: <pid>"}}` pseudo-nodes for each open promise.
  Root capability is classed `gapcrit` (critical) or `gapwarn` (partial /
  unrealized).

- `_stamp_unrealized_on_entities(summary, records)` — reverse-indexes
  the audit onto capability records as
  `unrealized: {severity, open_promise_count, realizer_count}`.

Wiring: `_build_payload` invokes the summary after the compliance walk,
stamps annotations onto records, stamps per-cap Mermaid onto records, and
prints a build-time INFO summary grouped by severity.

## Findings on the current model

Build-time INFO output (verbatim):

```
INFO: 6 unrealized-capability audit finding(s): critical=2, partial=2, unrealized=2
  [critical] CAP-DF: 0 realizers, 2 open promises
  [critical] CAP-DF.4: 0 realizers, 3 open promises
  [unrealized] CAP-DF.1: 0 realizers, 0 open promises
  [unrealized] CAP-DF.3: 0 realizers, 0 open promises
  [partial] CAP-PB: 1 realizers, 2 open promises
  [partial] CAP-SL: 1 realizers, 1 open promises
```

Interpretation:

- **CAP-DF critical (flagship).** The evolve-forward capability has 2 open
  promises and no `realizes` edge from any component. This is the same
  gap the compliance walk (L12) surfaced at the promise level, now
  visible at the capability level — CAP-DF is what this whole shelf run
  is *about* and yet no component claims to realize it. Expected until
  Part 2 authoring lands.
- **CAP-DF.4 critical.** 3 open promises, no realizer. Same shape as
  CAP-DF but at the sub-capability level.
- **CAP-DF.1 / CAP-DF.3 unrealized.** No realizer, but also no open
  promises — silent placeholders. Candidates for either promotion (add
  promises + realizers in Part 2) or removal.
- **CAP-PB partial.** Realized by COMP-PIPELINE. 2 promises remain open —
  these are the L12–L13 authoring todos already logged.
- **CAP-SL partial.** Realized by COMP-SLICER. 1 open promise —
  `PR-CAP-SL-requirements`, which L16 confirmed is a legitimate gap in
  `slice_by_component` (drops 6 of 7 entity kinds). Deferred to Part 2.

None of the six findings are walker bugs. All map to authoring todos
already tracked in prior lessons (L12, L13, L16) or in the shelf itself.

## Lesson learned (L17)

Recorded in `.architecture/model/capabilities.v3.yaml` on CAP-DF. Key
points:

1. **Same substrate.** Capability-level realization uses the same
   graph-walk-as-capability pattern as every other walk on the shelf —
   pure classifier + Mermaid renderer + reverse-stamp, silent-skip on
   ok / unknown.
2. **No schema change.** Classifier reads existing `promises` list and
   `realizes` edges. Same design point as L15's tier classifier.
3. **Gap is the visual.** For non-ok cases, the diagram *is* the gap:
   sentinel `NO_REALIZER` node when there is no realizer, `OPEN_pid`
   pseudo-nodes for each open promise. Silent-skip the ok case; make
   non-ok cases loud. Same shape as L7 (silent-skip) + L11 (additive
   walker) combined.
4. **Loop closure.** L12 opened the compliance loop at the promise
   level; L17 closes it at the capability level. Both walks now use
   the same auditable substrate, and both surface findings that are
   authoring todos rather than walker bugs.

## Verification

- 13 new unit tests in `tests/viewer/test_walks.py` (62 → 75 total, all
  passing). Coverage: 4 severity classes, non-capability rejection,
  unknown-id rejection, ok-skip, deterministic ordering, sentinel
  presence in critical + partial Mermaid, reverse-stamp shape.
- Byte-determinism preserved: `build_v3_viewer.py` output diffed
  identical across two consecutive runs (both HTML + JSON payload).
- Build INFO summary matches the 6 findings enumerated above.

## Shelf status

- [x] #3 harness (42 tests)
- [x] #1 L15 evidence tiers (62 tests)
- [x] #4 CAP-SL self-exercise (L16, deferred fix)
- [x] #2 8th walk unrealized-capability audit (L17, 75 tests)

All four items done. Next direction TBD — offer follow-ups: banner UI
for tier summary, extend CAP-SL to close L16, wire unrealized card
into viewer HTML.
