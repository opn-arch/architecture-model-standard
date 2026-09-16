# Lessons-to-model + CAP-DF loop closure (2026-09-16)

## What

Two-part model enrichment:

1. **Lessons harvested** — 8 concrete lessons from CAP-PB walk + viewer
   content-shape fix + 3-diagram generalization, encoded as
   `PR-CAP-DF-lessons_learned` (attribute: `lessons_learned`, 8 content
   lines) and `PR-CAP-DF1-failure_modes` (5 walk-failure modes derived
   from those lessons).

2. **Task B — dev loop closed** — 3 cross-pipeline `triggers` edges
   linking CAP-DF ↔ CAP-PB, completing the
   view → note → walk → re-extract → view cycle:

   | From                | To                | Meaning                                         |
   |---------------------|-------------------|-------------------------------------------------|
   | `BEH-walk-author`   | `BEH-run-pipeline`| author fragment → re-run extraction             |
   | `BEH-run-pipeline`  | `BEH-view-browse` | pipeline emits IF-model → open viewer           |
   | `BEH-view-note`     | `BEH-walk-author` | notes surface deltas → author next walk fragment|

## Lessons captured

Encoded as a single 8-content-line promise on `CAP-DF`
(attribute: `lessons_learned`, status verified) with each lesson
tagged by origin walk. The full text lives in
`.architecture/model/capabilities.v3.yaml:PR-CAP-DF-lessons_learned`.
Summary:

- **L1** (CAP-PB): capability decomposition ≠ component decomposition
  — collapsed hash traces are deliberate.
- **L2** (CAP-PB): semantic attributes ARE the walk, not decoration —
  every walk emits intent + ≥1 reflective attribute.
- **L3** (CAP-PB): user-triggered entry behaviors must be first-class
  (BEH-run-pipeline was missing until L5).
- **L4** (viewer): cross-source shape divergence normalizes at the
  Python boundary in `_build_payload`, never at the JS consumer.
- **L5** (viewer): try/catch surfaces bugs but hides root cause —
  diagnose by reading DATA shape, not code (falsification proved the
  content-str-vs-list theory).
- **L6** (viewer): graph-walk-as-capability generalizes — helper +
  stamp + render-loop entry. 3 new walks landed via the same pattern.
- **L7** (viewer): silent-skip on N/A beats always-render — adaptive
  caps (BFS depth 2, 30 nodes, neighbor threshold 20).
- **L8** (viewer): kind-dispatched walks unavoidable when semantic
  shape varies across kinds (7 realization strategies).

L4-L8 are also mirrored into CAP-DF.1's `failure_modes` promise so
the walk-as-capability entity page carries a per-walk checklist.

## Task B — CAP-DF loop closure

Prior state: CAP-PB flow was internally connected (7 stage triggers
edges landed in previous commit), but CAP-DF sub-behaviors were
isolated from CAP-PB — no edge crossed the capability boundary. The
"dev loop" existed only in prose, not in the graph.

Post-state: 3 triggers edges close the cycle. Verified via neighbor
inspection:

```
BEH-walk-author:  outbound=[BEH-run-pipeline]     inbound=[ACT-se, BEH-view-note, CAP-DF.1]
BEH-run-pipeline: outbound=[BEH-scan, BEH-view-browse, COMP-c5a72728]
                  inbound=[ACT-ci, ACT-developer, BEH-walk-author, CAP-PB]
BEH-view-note:    outbound=[BEH-walk-author, COMP-VIEWER]
                  inbound=[ACT-developer, CAP-DF.2]
```

Every dev-loop behavior now has both an inbound and outbound trigger,
forming a walkable cycle. Realization walker on any of the three
correctly surfaces the new upstream / downstream neighbor via the
`neighbors_mermaid` diagram.

## Why not flow_mermaid on CAP-DF?

`CAP-DF` contains sub-capabilities (`CAP-DF.1..4`), not behaviors, so
`_mermaid_pipeline` correctly returns None. Similarly `CAP-DF.1`
contains behaviors, but its contained set (`BEH-walk-*`) has no
INTERNAL triggers — every new triggers edge crosses the CAP-DF.1
boundary. This is semantically correct: the dev loop is a
cross-capability flow, not a within-capability pipeline. The
`neighbors_mermaid` on each behavior surfaces the cross-boundary
edges directly.

Follow-up candidate: a "cross-capability flow" walk that lifts the
`_mermaid_pipeline` template to detect flows spanning multiple
containing capabilities. Would auto-populate on CAP-DF.

## Verification

```
DETERMINISTIC       # byte-identical rebuild
promises: 773 -> 775  (+2)
verified promises: 104 -> 106  (+2)
edges:    127 -> 130  (+3)
CAP-DF lessons_learned promises: 1 (8 content lines)
CAP-DF.1 failure_modes promises: 1 (5 content lines)
BEH-view-note neighbors_mermaid: present
```

## Files changed

- `.architecture/model/capabilities.v3.yaml` — 2 new promises + 3 new
  triggers relationships (~60 added lines).
- `.architecture/viewers/v3_viewer.html` — regenerated (470 KB).
- `.architecture/viewers/v3_viewer_data.json` — regenerated (575 KB).

## Next

Two candidates on the shelf:

1. **Cross-capability flow walker** — lift `_mermaid_pipeline` to
   detect flows crossing capability boundaries; would auto-populate
   `flow_mermaid` on CAP-DF from the newly-added triggers edges.
2. **Add `realizes` edge from COMP-2 (pipeline component) to CAP-PB**
   — closes the "CAP-PB has no realization_mermaid" gap noted in the
   prior commit (currently semantically correct but visually empty on
   the CAP-PB entity page).
