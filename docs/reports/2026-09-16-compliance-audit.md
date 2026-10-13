# Constraint compliance audit (7th walk)

**Date:** 2026-09-16
**Follows:** `e9671df feat(viewer)` — constraint impact walk + diagnostics
**Category:** substrate extension (7th walk) + audit tier

## Motivation

The follow-up note in `2026-09-16-constraint-impact-and-diagnostics.md`
proposed a "constraint-driven diagnostics" pass to surface entities
impacted by a constraint but lacking evidence of upholding it. This
closes the auditability loop: the substrate can now not only DRAW the
impact graph (6th walk) but also FLAG which impacted entities have no
verified promise proving compliance.

## Design

Two pure functions in `scripts/build_v3_viewer.py`:

### `_constraint_compliance_gaps(entities_by_kind, relationships, entity_records)`

For each constraint, walks the same 2-hop impact set as
`_mermaid_constraint_impact` (guaranteeing audit and viewer agree),
then per-entity checks whether it satisfies the universal evidence
rule (L12): **\u22651 verified promise with attribute in
`{verification, verified_by, slos, success_criteria}`**.

Returns a deterministic
`list[{constraint_id, constraint_name, entity_id, entity_kind,
entity_name, reason}]`.

### `_stamp_compliance_gaps_on_entities(gaps, entity_records)`

Reverse-indexes the gap list onto each affected entity record as
`compliance_gaps: list[constraint_id]` so entity pages can render the
auditor's view without re-computing.

Wired into `_build_payload`:
- Console: `INFO: N constraint compliance gap(s) across M constraint(s)` at build time
- Payload: `diagnostics.constraint_compliance_gaps` (flat list)
- Payload: per-entity `compliance_gaps` field (when non-empty)
- Overview banner: grouped-by-constraint with clickable entity chips
- Entity page: yellow "Compliance gaps" card after neighbors card

## Findings (16 gaps across 12 entities, 3 constraints)

Legitimate authoring todos surfaced by the audit:

| Constraint | Gap entities |
|---|---|
| `CONS-determinism` | `CAP-DF.2`, `CAP-SL`, `BEH-view-browse`, `BEH-view-note`, `BEH-view-save` |
| `CONS-no-runtime-deps` | `CAP-DF.2`, `BEH-view-browse`, `BEH-view-note`, `BEH-view-save` |
| `CONS-open-schema` | `CAP-DF.1`, `CAP-DF.4`, `BEH-S1`, `BEH-S2`, `BEH-walk-author`, `BEH-walk-descend`, `BEH-walk-realize` |

Zero gaps flagged for `CONS-ast-only`, `CONS-pinned-clock`,
`CONS-resumable` \u2014 all impacted entities either are CAP-PB
(fully-verified) or BEH-PB.* (which have `verified_by` promises citing
test files). This is precisely the correct signal.

## Verification

- Deterministic build (double-run diff clean).
- `node --check` clean on extracted script.
- 12 entities carry per-entity `compliance_gaps` field matching the
  flat list (round-trip correct).
- CONS-ast-only / CONS-pinned-clock / CONS-resumable show zero gaps
  because their impact set (BEH-PB.* + CAP-PB) is fully evidenced.
- Totals unchanged: 67 entities, 130 edges, 778 promises, 61 gaps.
  (The 16 compliance gaps live in `diagnostics`, not `gaps` \u2014
  they're audit output, not typed model gaps.)

## Lessons

- **L12** \u2014 Universal evidence attrs beat per-constraint rules for the
  initial audit tier. Defining evidence as *any* verified promise on
  `{verification, verified_by, slos, success_criteria}` caught 16 real
  gaps with zero per-constraint mapping. Per-constraint rules can
  layer on top later without changing the substrate.
- **L13** \u2014 The audit's job is to make gaps visible; closing them is
  authoring work. Loop pattern continues: view (banner) \u2192 note (12
  entities flagged) \u2192 walk/author (fill promises in a later cycle).
  Do NOT batch-fill in the same commit that adds the audit \u2014 that
  hides the audit's value.

## Follow-ups (authoring, deferred to next loop cycle)

For each of the 12 flagged entities, add \u22651 verified promise on one
of the four evidence attrs. Priority order:

1. `CAP-DF.2` (Review) \u2014 has 2 constraints; highest-signal target
2. `CAP-DF.1` (graph_walk_as_capability) \u2014 impacted by CONS-open-schema; ironic
3. `CAP-SL` (Slice) \u2014 needs determinism SLO citing tests/pipeline_v3/test_slice.py
4. `CAP-DF.4` (LLM adapter) \u2014 CONS-open-schema; add slos re: prompt structure
5. `BEH-view-*` (3 behaviors) \u2014 add `verified_by` citing viewer test files
6. `BEH-walk-*` (3 behaviors) \u2014 add `verified_by` citing walk-authored fragments
7. `BEH-S1`, `BEH-S2` \u2014 add `verified_by` citing pipeline stage tests

## Files changed

- `scripts/build_v3_viewer.py`
  - `_COMPLIANCE_EVIDENCE_ATTRS` frozenset (~L1207)
  - `_entity_has_compliance_evidence` helper
  - `_constraint_compliance_gaps` walker
  - `_stamp_compliance_gaps_on_entities` reverse index
  - Wiring in `_build_payload` + console INFO line
  - Overview banner: constraint-grouped gap card with entity chips
  - `selectEntity`: per-entity Compliance gaps card
- `.architecture/model/capabilities.v3.yaml` \u2014 L12-L13 lessons + report ref
- `.architecture/viewers/v3_viewer.html` (regenerated)
- `.architecture/viewers/v3_viewer_data.json` (regenerated)
- `docs/reports/2026-09-16-compliance-audit.md` (this file)
