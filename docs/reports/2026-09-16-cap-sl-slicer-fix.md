# L16 CAP-SL slicer gap closure

**Date:** 2026-09-16
**Scope:** Close the L16 bounded fix identified in the CAP-SL self-exercise.

## Diagnosis (recap from L16)

`slice_by_component(model, "COMP-VIEWER")` retained COMP-VIEWER but dropped:

- All non-component entity kinds (capabilities, behaviors, interfaces,
  constraints, layers, actors) — 6 of 7 canonical kinds.
- All relationships pointing to non-component entities, even when the
  relationship touched the target component.

Root cause: the neighbor-closure loop only added ids that were already
in the component id map, so any `realizes`/`exposes`/`traces-to`/
`constrained-by`/`contains` edge from COMP-VIEWER to another kind was
silently dropped.

## Fix

`src/architecture_model/pipeline_v3/slice.py`:

1. Added `_all_entities_by_kind(model)` — returns `{kind_plural: [ent, ...]}`
   across every entity bucket.
2. Added `_id_to_kind(model)` — builds an id → kind_plural index over
   ALL entity kinds.
3. Rewrote `slice_by_component` neighbor closure to use the global
   id_to_kind index instead of the component-only map.
4. Grouped retained entities back into their original kind buckets in
   the output (`entities.components`, `entities.capabilities`, ...) so
   downstream walk-substrate consumers see the graph.
5. Preserved deterministic ordering (sorted by id within each bucket).
6. Preserved existing semantics: same target-only behavior when
   `include_neighbors=False`; same relationship-inside-kept-set filter;
   same meta stamping.

Impact size: ~30 LOC as L16 predicted.

## Verification

`tests/pipeline_v3/test_slice.py`:

- All 14 existing tests pass unchanged (backward compatibility).
- 4 new cross-kind tests added (18 total):
  - `test_slice_by_component_retains_cross_kind_neighbors` — a component
    with realizes/exposes/traces-to/constrained-by/contains edges pulls
    in one entity of each neighbor kind; distant entities (2 hops away)
    are excluded.
  - `test_slice_by_component_no_neighbors_drops_other_kinds` —
    `include_neighbors=False` returns only the target bucket.
  - `test_slice_by_component_retains_cross_kind_edges` — all 5 edges
    touching the target are in the sliced relationships; distant edges
    are not.
  - `test_slice_by_component_multi_kind_deterministic` — repeated calls
    produce byte-identical YAML.
- Broader `tests/pipeline_v3/` + `tests/viewer/` run: 220 passed.
- Viewer rebuild: byte-deterministic (no direct dependency; sanity
  check only).

## Status

- CAP-SL is now walk-substrate-complete for the 1-hop case.
- `PR-CAP-SL-requirements` can be closed on the next authoring pass;
  L16 lesson updated in-place to note resolution.
- Multi-hop closure (contains-chain expansion, transitive
  `realizes`-through-capability) remains a Part 2 refinement if
  downstream needs it — not required by the current walk substrate.

## Shelf status (final)

- [x] #3 harness (42 tests)
- [x] #1 L15 evidence tiers (62 tests)
- [x] #4 CAP-SL self-exercise (L16 filed)
- [x] #2 8th walk unrealized-capability (L17, 75 tests)
- [x] +1 UI wiring: unrealized card + severity badge in v3_viewer.html
- [x] +2 L16 fix: cross-kind slice_by_component (18 tests)

**All committed work is verified byte-deterministic and test-passing.**
