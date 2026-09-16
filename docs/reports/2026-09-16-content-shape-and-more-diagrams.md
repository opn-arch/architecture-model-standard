# Content-shape fix + three entity-page diagrams (2026-09-16)

## Problem

23 of 25 components rendered a "Render error" card in the v3 viewer. The
Phase-1 diagnostic try/catch (commit `aafe62d`) surfaced the failure but
did not identify the source. Two components — `COMP-VIEWER` (fully
authored) and `COMP-61323f76` (data, empty docstring) — worked, which
inverted the usual "author error" hypothesis and pointed at a
pipeline-emit vs. authored-fragment shape divergence.

## Root cause

`Promise.content` is inconsistently typed across sources:

- **Authored fragments** (`viewer.v3.yaml`, `enrichment.v3.yaml`,
  `capabilities.v3.yaml`) — always `list[str]`.
- **Pipeline-emit** (`.architecture-model.v3.yaml`) — `intent`
  promises store the module docstring as a **raw string**, while
  `delivers`/`provides` promises use lists.

The viewer JS at `selectEntity` did
`escapeHtml((p.content || []).join(', '))`. When `content` is a
truthy non-empty string, `.join` throws `TypeError: p.content.join is
not a function`, caught by the entity-page try/catch and rendered as
"Render error". The two working components hit the short-circuit
(`'' || []` → `[]`) because their docstrings were empty.

## Fix

Normalized `content` shape at the single Python boundary
(`_build_payload` in `scripts/build_v3_viewer.py:~714`), before it
enters the JSON payload:

- `None` → `[]`
- `str` → `[str]` (empty/whitespace-only → `[]`)
- `list` → `[str(x) for x in ...]`
- other scalar → `[str(x)]`

Same normalization applied to `gap_flat.content`. Single source of
truth; JS `.join()` is now shape-safe. CSS `.content-text` gained
`white-space: pre-wrap;` so multi-line docstrings render with their
original line breaks (option 1a from the finalized plan — no JS or
data-shape change required).

Post-fix data assertion: **0 content-shape violations across 773
promises**. `COMP-51592584.by_attr.intent[0].content` is now a
single-element list carrying the full module docstring.

## Bonus: three graph-walk diagrams per entity

Generalized the graph-walk-as-capability pattern established by
`_mermaid_pipeline`. Three new helpers stamp Mermaid + entity_refs
fields on entity records (silent skip when N/A):

**`_mermaid_decomposition`** — BFS ≤ 2 hops of outbound `contains`,
cap 30 nodes, overflow rendered as `...N more` sink. Applies to
every entity kind (silent skip when no outbound `contains`). Result:
**7 entities** carry a decomposition diagram — the layered domains
and the pipeline capability.

**`_mermaid_realization`** — kind-dispatched 2-hop walk:

| Kind        | Walk                                                                        |
|-------------|-----------------------------------------------------------------------------|
| capability  | cap ← realizes ← components → contains → sub-components                     |
| component   | comp → realizes → capabilities ← contains ← parent caps                     |
| behavior    | beh ← traces-to ← components → realizes → capabilities                      |
| interface   | if ← exposes ← components → realizes → capabilities                         |
| layer       | layer → contains → components → realizes → capabilities                     |
| actor       | actor → triggers → behaviors ← traces-to ← components                       |
| constraint  | constraint ← constrained-by (1-hop only)                                    |

Returns `None` when hop 1 is empty. Result: **15 entities** carry a
realization diagram. `ACT-developer` correctly walks
`triggers` → 4 behaviors → back through `traces-to` to `COMP-VIEWER`.

**`_mermaid_neighbors`** — 1-hop typed-edge neighborhood, threshold
20 (`|inbound| + |outbound|`). Uses `out_edges` / `in_edges` (rel-type
preserving) — NOT the deduplicated `outbound`/`inbound` on the record.
Edges labeled with rel_type. Result: **62 of 67 entities** carry a
neighbors diagram; the 5 skipped are 4 with zero 1-hop neighbors +
`COMP-1896b055` (core, 20+ neighbors — falls back to chip lists only).

Each new card also emits an "entities referenced" chip list matching
the existing SE view aesthetic (drill-down enabled via existing
`.chip` click delegation).

## Entity page order (post-change)

1. Breadcrumb + header + subtitle
2. Summary
3. Flow (capabilities only, when triggers-shaped)
4. **Decomposition** (new)
5. **Realization** (new)
6. Promise attribute cards (intent / delivers / provides / other)
7. **Neighbors diagram** (new)
8. Neighbors chip lists (Depends on / Depended on by)
9. Notes

## Rendering pattern

All 4 diagrams (flow + 3 new) share a single JS render loop at the
tail of `selectEntity`. Each is a `_walkCard(title, mmd, refs, slug)`
that returns `{id, html}`; the render loop iterates the 4 target
ids and calls `mermaid.run({ nodes: [el] })` with per-diagram error
fallback (`<pre>` with escaped error text). Pattern generalizes
cleanly for future walks — add helper, stamp field, extend `targets`
array by one line.

## Verification

```
DETERMINISTIC       # byte-identical rebuild
JS_OK               # node --check on extracted logic script
content-shape violations: 0
diagram counts (out of 67 entities): {'flow': 1, 'decomposition': 7, 'realization': 15, 'neighbors': 62}
CAP-PB has flow: True decomp: True realiz: False neigh: True
COMP-1896b055 (>20 neighbors): neighbors_mermaid present? False
```

CAP-PB has no `realization_mermaid` because no component currently
`realizes` it — semantically correct; the pipeline capability is the
walk substrate, not a walk target. This can be closed in Task B by
adding `COMP-2 realizes CAP-PB` if we decide the pipeline module owns
the capability.

## Files changed

- `scripts/build_v3_viewer.py` — content normalization
  (~lines 714, 753); 3 new mermaid helpers + shared node/class emitters
  (before `_build_se_views`); per-entity stamping in `_build_payload`
  (all kinds, not just capabilities); `_walkCard` JS helper +
  render-loop generalization in `selectEntity`; CSS `white-space:
  pre-wrap` on `.content-text`.
- `.architecture/viewers/v3_viewer.html` — regenerated (465 KB).
- `.architecture/viewers/v3_viewer_data.json` — regenerated (570 KB).

## Next

Task B — close CAP-DF dev loop with 3 cross-pipeline `triggers`
edges (`walk-author → run-pipeline`, `run-pipeline → view-browse`,
`view-note → walk-author`). Once landed, CAP-DF.1 / CAP-DF.2 will
auto-populate `flow_mermaid` via the same generic capability walk.
