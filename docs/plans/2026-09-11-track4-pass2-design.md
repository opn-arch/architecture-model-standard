# Track 4 Pass 2 — Extended Routing, Shape Distinction, Drill-Down Enrichment

**Date:** 2026-09-11
**Branch:** `feat/phase-5-fanout-provenance-family5`
**Preceded by:** `docs/plans/2026-09-10-track4-slice-anchor-design.md`, `docs/plans/2026-09-10-track4-pass1-slice-anchor-plan.md`
**Status:** approved for implementation

## Motivation

Track 4 Pass 1 anchored the functional-architecture panel of `viewer.html` to a
deterministic `(model, files, artifacts)` slice via `slice_for_artifact` +
1-hop closure. Reviewer feedback after inspecting the regenerated viewer:

1. **Anchor routing must extend to the other three high-level views** —
   logical, conops, use-cases — so every panel is grounded in an auditable
   sub-model rather than the full model.
2. **Drill-down detail is thin.** Opening a capability shows only a subset
   of schema 2.1 semantic fields, and related entities / requirements are
   not surfaced with enough structure.
3. **Components and capabilities render as identical rectangles** in every
   panel. There is no visual distinction between structural and functional
   entities.

Pass 2 addresses all three concerns as one bundled release.

## Design

### 1. Routing extension

`_APPLY_ANCHOR` in `visualize.py` widens from `frozenset({"functional"})` to
`frozenset({"functional", "logical", "conops", "use_cases"})`. The existing
generic swap loop in `generate_html_viewer` handles arbitrary keys — no
control-flow change required. Each newly-routed view gets a count-based
regression test cloned from `cb52e66` to prevent Task 5's original
false-green from recurring.

### 2. Shape distinction

New module-level constant `_MERMAID_SHAPE` in `visualize.py` maps entity
kind → Mermaid bracket pair. All node emitters (`_sid`-based) route
through a new `_shape(kind, sid, label) -> str` helper that returns the
correctly-wrapped Mermaid node syntax.

| Kind       | Mermaid syntax         | Rationale                          |
|------------|-------------------------|------------------------------------|
| Component  | `sid[label]`            | Default rectangle — structural     |
| Capability | `sid{{label}}`          | Hexagon — SysML functional block   |
| Actor      | `sid((label))`          | Circle — external agent            |
| Behavior   | `sid([label])`          | Stadium — SysML use case oval      |
| Interface  | `sid[/label/]`          | Parallelogram — data/boundary flow |
| Constraint | `sid{label}`            | Rhombus — decision/gate            |
| Layer      | `subgraph` (unchanged)  | Already grouped                    |

Unknown kinds fall back to `sid[label]` with `_log.debug`. Total for the
seven current kinds; fallback protects forward-compat (e.g., `System`).

### 3. Drill-down enrichment

Three orthogonal sub-changes in `build_entity_properties` +
`propCardHtml`:

**3a. Schema 2.1 field expansion.** `_base` universal-fields loop
currently emits `intent, goals, requirements, rationale, moes,
value_function, failure_modes, trade_offs, interface_refs, decisions,
monitored`. Add the 9 missing schema 2.1 semantic fields:
`stakeholders, success_criteria, assumptions, open_questions,
verification, slos, owner, maturity, dependencies_rationale`. All 9 are
already parsed into the model dataclasses per Phase 2 substrate; the
serialization gap is the viewer-side loop.

**3b. Relationship grouping.** `propCardHtml` JS currently emits one
flat list of outgoing followed by one flat list of incoming
relationships. Group both under semantic headers derived from
`RelationshipType.value`: `Realized By`, `Realizes`, `Traces To`,
`Traces From`, `Consumes`, `Consumed By`, `Constrained By`,
`Constrains`, `Depends On`, `Depended On By`, `Contains`, `Contained
In`, `Exposes`, `Exposed By`, plus catch-all `Other`.

**3c. Linked requirements section.** Load
`.architecture/derived_requirements.yaml` in `generate_html_viewer`,
build `entity_id → list[requirement]` index, expose in
`diagram_data["requirements_by_entity"]`, render as a new "Linked
Requirements" section in `propCardHtml` above the grouped
relationships. Missing file → empty index + `_log.info` (not warn —
absence is expected on some repos).

## Data flow

```
model
  ↓
build_entity_properties (2.1 semantic fields expanded in _base)
  ↓ props[entity_id] = { type, name, description, status, properties, depth }
  ↓
merge with requirements_by_entity (from derived_requirements.yaml loader)
  ↓
diagram_data = {
  "properties": ...,
  "requirements_by_entity": ...,     # NEW
  ...
}
  ↓
per-panel Mermaid diagram generation
  ↓ every node emitted via _shape(kind, sid, label)
  ↓
HTML output
  ↓
propCardHtml (JS) renders: card + Linked Requirements + grouped Relationships
```

## Error handling

- **Missing `derived_requirements.yaml`** → empty index, `_log.info`, no
  requirements section rendered.
- **Malformed YAML** → `_log.warning`, empty index, no exception
  propagated.
- **Unknown entity kind for shape** → `_log.debug`, fall back to
  `sid[label]`.
- **Unknown relationship type in grouping JS** → falls under `Other`
  header.
- **Anchor routing extension** — reuses `_panel_model` helper; unknown
  view key falls back to full model per Pass 1 contract.

## Testing

~18–22 new tests across 9 tasks, mirroring Pass 1's cadence:

| Task | Scope | Tests | Files |
|------|-------|-------|-------|
| T1 | shape mapping constants + `_shape` helper | 3 | `tests/core/test_mermaid_shapes.py` |
| T2 | apply shapes in native panels | 2 | `tests/core/test_shapes_in_panels.py` |
| T3 | schema 2.1 field serialization | 3 | `tests/core/test_entity_properties_2_1_fields.py` |
| T4 | relationship grouping in propCardHtml | 2 | `tests/core/test_relationship_grouping.py` |
| T5 | requirements loader | 2 | `tests/core/test_requirements_loader.py` |
| T6 | requirements section in drill-down | 1 | `tests/core/test_requirements_section.py` |
| T7a | logical view routing + count regression | 1 | `tests/test_viewer_anchored.py` (extend) |
| T7b | conops view routing + count regression | 1 | `tests/test_viewer_anchored.py` (extend) |
| T7c | use_cases view routing + count regression | 1 | `tests/test_viewer_anchored.py` (extend) |
| T8 | full regression + regenerate viewer | — | verification only, no commit |

**Total new tests:** ~16–18. Baseline pre-Pass-2: 3664 passed / 104
skipped. Target post-Pass-2: ~3680–3682 passed.

**Rigor requirement:** every task must produce genuine RED before GREEN.
Task 5 of Pass 1 shipped with a false-green (tests passed against
pre-implementation code); fix commit `cb52e66` locked routing in via a
count-comparison test. Every T7 test must reproduce that pattern —
build a full-model entity exclusive to the view's un-anchored render,
assert the anchored HTML count is strictly less.

## Task granularity + parallelization

Nine commits, one per task (T1–T7c). Subagent-driven-development per
Pass 1's rhythm: implementer → spec reviewer → quality reviewer per
task. Independent tasks that can be dispatched in parallel:

- **T1, T3, T5** are structurally independent (constants + serialization
  gap + loader). Can dispatch implementers concurrently after design
  approval.
- **T2 depends on T1** (uses `_shape`).
- **T4 depends on T3** (uses expanded properties).
- **T6 depends on T5** (uses loader).
- **T7a/T7b/T7c** are independent of each other and of T1–T6; can be
  dispatched concurrently, or serialized for review clarity.

Estimated runtime: 60–90 minutes with parallel dispatch of T1/T3/T5 and
T7a/T7b/T7c, sequential T2/T4/T6.

## Non-goals

- No schema bump. Fields are already schema 2.1; this closes a viewer-
  side serialization gap only.
- No nav-sidebar changes. Nav still surfaces full-model entities
  regardless of anchor — that's a Pass 3 concern.
- No new shape mappings for `System` or `Layer` beyond current
  handling.
- No emission of anchor metadata into HTML (`data-slice-anchor` attrs)
  — Pass 3.
- No `curation.featured ⊆ anchor.model` validation — Pass 4.
- No changes to the routing gate mechanism itself (still
  `_APPLY_ANCHOR` frozenset + `_panel_model` helper).

## Success criteria

1. All 4 high-level view panels (functional, logical, conops,
   use_cases) route through `anchor.model` in the rendered HTML.
2. Opening a capability in any panel shows all 14 schema-2.1 semantic
   fields when populated, grouped relationships by type, and a
   Linked Requirements section when the entity is referenced in
   `derived_requirements.yaml`.
3. Every panel visually distinguishes components (rectangles) from
   capabilities (hexagons); actors/behaviors/interfaces/constraints
   also have distinct shapes.
4. Full test suite: no regressions; ~18 new tests all pass with
   genuine RED evidence.
5. `viewer.html` regenerates cleanly and rendering is visually
   validated by user review before Pass 3.
