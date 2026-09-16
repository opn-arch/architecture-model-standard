# CAP-SL Exercise — Self-Application of the Substrate

**Date:** 2026-09-16
**Shelf item:** #4 CAP-SL exercise
**Lesson emitted:** L16

## Purpose

Item #4 on the session shelf was "exercise CAP-SL to identify a next lesson."
CAP-SL's promise (PR-CAP-SL-intent) is to produce focused subgraph slices of
the v3 model as substrate for downstream tasks. This exercise applies the
capability to itself — take a slice and try to feed it into the walk
substrate that our viewer already runs on the whole model — and reports
what breaks.

## Method

1. Load merged model via `build_v3_viewer._merge_sources`.
2. Reshape merged model to v3 pipeline shape (`entities.<kind>` as
   `list[dict]`, not `dict[id -> dict]`).
3. Slice by `COMP-VIEWER` via
   `architecture_model.pipeline_v3.slice.slice_by_component(model,
   'COMP-VIEWER', include_neighbors=True)`.
4. Feed the sliced output back into the walk helpers
   (`_mermaid_neighbors`, `_mermaid_realization`,
   `_mermaid_pipeline`) after reshaping to the walker's
   `{kind_plural: {id: entity}}` contract.
5. Observe.

## Observations

**Slice output shape:** the slice returns only
`entities.components`. The six other canonical kinds
(`capabilities`, `behaviors`, `interfaces`, `actors`, `constraints`,
`layers`) are absent from the output entirely.

**Neighbor count collapse:** COMP-VIEWER's full 1-hop neighborhood in
the merged model spans capabilities (CAP-DF.2, CAP-DF.4, CAP-SL,
CAP-PB fragments), interfaces, and behaviors. Post-slice, only
COMP-1896b055 (the one component-to-component edge) survives.
`include_neighbors=True` closes over `relationships` but the closure
only accepts targets present in `by_id` (component ids), so cross-kind
targets are silently dropped.

**Walk substrate compatibility:**

| Walk                              | Outcome on slice          | Reason                                    |
|-----------------------------------|---------------------------|-------------------------------------------|
| `_mermaid_neighbors(COMP-VIEWER)` | Renders (degraded)        | 1 neighbor vs ~8 on full model            |
| `_mermaid_realization(COMP-VIEWER, "component")` | None (silent skip) | hop1 (`realizes` outbound) targets are capabilities, filtered out |
| `_mermaid_pipeline("CAP-DF")`      | None (unknown cap)        | `capabilities` bucket dropped from slice  |
| `_mermaid_cross_capability_flow`   | None (unknown cap)        | Same as pipeline                          |
| `_mermaid_constraint_impact`       | Not exercised — no constraints in slice | Same shape issue    |
| `_mermaid_decomposition`           | Runs, but truncated       | `contains` closure hits non-component kinds |
| `_constraint_compliance_gaps`      | Empty — no constraints    | Nothing to audit                          |

3 of 7 walks return `None` outright; 2 more return degraded output;
only 2 are viable.

## L16 — CAP-SL is not walk-substrate-complete

CAP-SL's `slice_by_component` is a component-only slicer. Its
`include_neighbors=True` mode closes over `relationships` but only
retains targets whose ids are already in the components map. Any
`realizes`, `exposes`, `traces-to`, `constrained-by`, `triggers`, or
cross-kind `contains` edge is dropped along with its non-component
endpoint. The resulting sub-model cannot substrate 5 of the 7 walks
the viewer relies on.

This is a genuine gap in PR-CAP-SL-requirements, which is already
`status: open`:

> - accept a v3 model + focus spec (component id, capability id,
>   attribute filter)
> - return a sub-model that itself validates against
>   promise-graph.schema.json
> - preserve all promises on retained entities (no truncation of
>   attribute vocabulary)

The current implementation delivers component-id focus only. Capability
focus and attribute-filter focus are unimplemented. And even for
component focus, the "preserve all promises on retained entities" line
is trivially satisfied (promises live on components) but the SPIRIT of
substrate-completeness is not: any downstream walk that needs the
components' realizes/exposes targets to be present will silently
degrade.

### What "walk-substrate-complete" would look like

`slice_by_component(component_id, include_neighbors=True)` should, at
minimum, close over these edges and pull in the target entity from
whatever kind it lives in:

- `realizes`   → target capability
- `exposes`    → target interface
- `traces-to`  → target behavior
- `constrained-by` → target constraint
- `contains`   → target of any kind (already component-only today)
- `depends-on` → target component (already handled)
- `triggers`   → target behavior (for actor-rooted slices later)

This is a bounded change (~30 LOC in `slice.py`) but is a Part 2
authoring TODO, not this-session scope. Filing as L16 makes it
visible in the CAP-DF lessons stream and links it to the exercise
that surfaced it.

## Verification

Reproduce with:

```python
import importlib.util
spec = importlib.util.spec_from_file_location('bv', 'scripts/build_v3_viewer.py')
bv = importlib.util.module_from_spec(spec); spec.loader.exec_module(bv)
from architecture_model.pipeline_v3 import slice as v3slice

sources = bv._load_sources(bv.DEFAULT_MODEL)
_, ebk, rels, _ = bv._merge_sources(sources)
v3model = {
    'meta': {},
    'entities': {k: list(v.values()) for k, v in ebk.items()},
    'relationships': rels,
}
sliced = v3slice.slice_by_component(v3model, 'COMP-VIEWER')
assert set(sliced['entities'].keys()) == {'components'}   # 6 kinds dropped
```

## Next actions (deferred)

1. Extend `slice_by_component` to include cross-kind edge targets
   (`realizes`, `exposes`, `traces-to`, `constrained-by`, `contains`).
2. Implement `slice_by_capability` and `slice_by_attribute` per
   PR-CAP-SL-requirements.
3. Add pytest coverage to `tests/pipeline_v3/` (or wherever slicer
   tests live) using the same walk-substrate-compatibility criterion:
   after slicing, each of the 7 walks must produce byte-identical
   output on the slice as it does on the same subset of the full
   model.

Not this session.
