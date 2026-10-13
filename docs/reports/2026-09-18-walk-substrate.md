# Walk substrate — retrospective (Parts 1–7)

**Date:** 2026-09-18
**Scope:** parts 1–7 of the walk-as-capability refactor, closing with meta-walk substrate
**Companion docs:**
- Plan: `docs/plans/2026-09-16-walk-substrate.md`
- v3 SE walk: `docs/reports/2026-09-14-v3-se-walk.md`
- Graph adapter (Stage 1): `docs/graph-export.md`

---

## What changed

Before Part 1, "walks" were 13 hand-rolled Python functions inside
`scripts/build_v3_viewer.py` — one per audit concern — each carrying its
own traversal, classification, and card-shaping logic. Coverage was
implicit (whatever `build_v3_viewer.py` bothered to compute), invalidation
was ad-hoc, and adding a new walk meant editing viewer code.

Parts 1–7 promoted walks to first-class capabilities:

1. **Part 1 — substrate promotion.** `pipeline_v3.substrate.Pipeline`
   grew a 6-stage walk pipeline: `select → traverse → classify → rollup →
   evidence → emit`. Each stage is a pure function over a shared context
   dict.
2. **Part 2 — WalkSpec loader.** Declarative YAML schema
   (`architecture_model.walks.spec.loader`) with runtime-checkable
   dataclasses for `ScopeSpec / TraverseSpec / HopSpec / ClassifySpec /
   VerdictRule / RollupSpec / EvidenceSpec / EmitSpec`.
3. **Part 3 — walks-as-capabilities.** CAP-WK umbrella + one sub-cap per
   walk in `capabilities.v3.yaml`. Each sub-cap's `verified_by` points
   at its WalkSpec YAML file; the `audits` relationship (list-valued)
   declares which caps each walk targets.
4. **Part 4 — pilot retrofit.** `WALK-unrealized-cap` shipped as the
   first declarative walk, running in parallel with its Python
   counterpart under a parity test.
5. **Part 5 — rollup + viewer wiring.** `worst-child` rollup along
   `contains` closed Concern B (parent-cap severity propagation);
   viewer consumed walk outputs directly.
6. **Part 6 — six-walk retrofit sweep.** `descend`, `realize` (7
   kind-dispatched hops), `browse`, `constraint-impact`, and 2×
   `realization-skip` walks all migrated with parity tests.
7. **Part 7 — meta-walk substrate (this report).** Two meta-walks that
   audit the substrate itself: `walk_coverage` (Python) audits WalkSpec
   YAMLs against the CAP-WK sub-cap inventory; `attribute-completeness`
   (declarative WalkSpec) audits promise coverage on every entity.

## Real-repo signal after Part 7

`architecture_model.walks.meta.audit_walk_coverage` reports:

| verdict | count | subjects |
|---|---|---|
| covered | 5 | `attribute-completeness`, `browse`, `constraint-impact`, `descend`, `unrealized-cap` |
| duplicate-walk | 2 | `realize` (7 kind-dispatched hops), `realization-skip` (capability + component sides) |
| uncovered | 6 | `author`, `direction-lint`, `meta-coverage`, `note`, `promotion`, `save` |

Two dangling refs from before Part 7 are **eliminated** — Part 7 added
`CAP-WK.constraint-impact` and `CAP-WK.realization-skip` sub-caps to
match walks that already existed. Six sub-caps remain proposed-but-not-
realized; they are the natural Part 8+ backlog.

The `duplicate-walk` verdict is informational, not a defect: two
substrate patterns legitimately produce many walks per sub-cap.
Kind-dispatched `realize` splits by target entity kind for readability;
`realization-skip` audits both sides of the `realizes` edge.

## Why declarative wins (evidence)

| axis | pre-Part 1 (hand-rolled) | post-Part 7 (WalkSpec) |
|---|---|---|
| walk count | 13 Python funcs, ~1200 LOC | 13 YAML files, ~600 LOC + 6 shared stages |
| adding a walk | edit viewer, hand-code select+classify+emit | write a YAML file (~30 lines) |
| rollup logic | duplicated per walk | one implementation in `stages/rollup.py` |
| coverage audit | impossible (walks weren't entities) | `audit_walk_coverage` (this report) |
| kind dispatch | conditional branches inside walker | `HopSpec.by_kind` map |
| composition | not supported | `scope.from_walk` chains walks |
| invalidation | full rebuild | meta-walk flags stale sub-cap coverage |

## Meta-walk design decisions

- **`walk_coverage` is Python, not YAML.** Its subject is filesystem
  WalkSpec files, not entities in the model graph. A declarative walk
  cannot express "scan a directory" without introducing filesystem
  primitives into the DSL. Python is the honest tool here.
- **`attribute-completeness` is pure YAML.** Its subject is
  `entity.promises` — a first-class model field. The classify DSL's
  `promise_status_count:<status>` atom bucketed the data cleanly; no
  Python needed. This is the substrate working as designed.
- **Umbrella `CAP-WK` excluded from coverage.** It's the parent, not
  a walk realization. Sub-caps are the units of realization.
- **Non-CAP-WK audits (e.g., `CAP-PB`, `CAP-SL`, `CAP-DF`) are not
  dangling.** Walks legitimately audit other capabilities; only
  `CAP-WK.*` audits are checked against the sub-cap inventory.

## Follow-on work (deferred)

- **Part 8 — retrofit remaining walks.** author, note, save, promotion
  walks are proposed but not yet realized. direction-lint has a sub-cap
  but no WalkSpec YAML (viewer's `_lint_edge_note_directions` still
  hand-rolled).
- **Custom classify DSL atoms.** `attribute-completeness` uses
  count-based bucketing; a `promise_for:<attribute>` atom would enable
  finer-grained audits ("has an `intent` promise", "has a `slos`
  promise").
- **NetworkX graph adapter (Stage 1 shipped separately).** Once walks
  are the only consumer of the model graph, we can swap the walk
  substrate's traversal backend to NetworkX (Stage 2).

## Files touched (Part 7)

Added:
- `src/architecture_model/walks/meta/__init__.py`
- `src/architecture_model/walks/meta/walk_coverage.py`
- `.architecture/model/walks/attribute-completeness.v3.yaml`
- `tests/walks/test_meta_walk_coverage.py` (13 tests)
- `tests/walks/test_pilot_attribute_completeness.py` (11 tests)
- `docs/reports/2026-09-18-walk-substrate.md` (this file)

Modified:
- `.architecture/model/capabilities.v3.yaml` — added 4 CAP-WK.* sub-caps
  (`constraint-impact`, `realization-skip`, `meta-coverage`,
  `attribute-completeness`) with contains + audits edges; appended
  L18–L21 to `PR-CAP-DF-lessons_learned`; annotated L6/L11 as superseded.
- `CONTEXT.md` — new "Walk substrate (Parts 1–7)" section.
