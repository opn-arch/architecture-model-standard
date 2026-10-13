# Pipeline flow embedded in CAP-PB entity page + component drilldown fix

**Date:** 2026-09-16
**Branch:** current dev
**Prior:** `8a4cc1a feat(model+viewer): CAP-PB stage triggers + pipeline flow SE view`

## What changed

Two orthogonal viewer improvements shipped in one commit, both isolated
to `scripts/build_v3_viewer.py`. No model edits. HTML + JSON regenerate
byte-deterministically.

### 1. Moved CAP-PB pipeline flow into the capability's entity page

Prior state (commit `8a4cc1a`): pipeline flow lived as a top-level SE
view accessed via a dedicated sidebar link ("CAP-PB Pipeline Flow")
under **SE Views**. That worked but split the story — the flow lived
separately from CAP-PB's promises/neighbors.

New state: the flow renders **inline** in CAP-PB's entity page, above
the promises grid, as a Mermaid card labeled *"Flow (contained
behaviors)"*. The top-level SE view + sidebar link are removed.

### 2. Generalized: any pipeline-shaped capability gets an inline flow

The embed is a design principle, not a special case for CAP-PB:

> Any capability whose contained behaviors carry internal `triggers`
> edges auto-renders an inline Mermaid flow card in its entity page.

`_mermaid_pipeline()` was generalized to accept a `cap_id` parameter and
returns `None` when the capability has no internal triggers edges (so
non-pipeline capabilities get no flow card, silently). The build script
calls it once per capability during payload assembly and stamps
`flow_mermaid` + `flow_refs` onto the capability record.

Today: only CAP-PB qualifies. After Task B (cross-pipeline CAP-DF
triggers edges), CAP-DF.1 (walk) and CAP-DF.2 (view) will
auto-populate their own flow cards **without any code change** — the
substrate already handles it.

The generalization also broadened the "orchestrator" concept: any
contained behavior with an inbound trigger from an actor becomes an
**entry** node (emphasized rect). Multiple entries per capability are
supported. Output interfaces are discovered via `produces` from any
contained behavior (not hardcoded to `BEH-publish`).

### 3. Component drilldown robustness (layered defense)

User reported only 2 of 25 components (COMP-VIEWER, COMP-61323f76
"data") opened when clicked in the sidebar. Read-only investigation
falsified the "rich by_attr" hypothesis — the working pair shares no
data-side property with each other or the broken 23. Root cause was
**not identified read-only**, so the fix uses layered defense so
behavior is corrected AND cause is surfaced on first repro.

**Change A — Event delegation** replaces per-element listeners on
`.entity-link` in `renderSidebar()`. A single delegated listener on
`#entity-groups` catches every click via `ev.target.closest('a.entity-link')`.
This survives DOM re-renders and guarantees every entity row responds,
regardless of any prior attachment failure mode.

**Change B — Diagnostic warn** on `selectEntity()` early-return:
```js
if (!e) {
  console.warn('selectEntity miss:', id, 'byId size:', Object.keys(byId).length);
  return;
}
```
If the failure is a `byId` map miss (data-side), this fires visibly in
DevTools instead of silently no-op'ing.

**Change C — try/catch fallback UI** around the entire `selectEntity`
body. Render-time exceptions on specific entity shapes now surface as a
"Render error" card with stack trace instead of leaving the pane blank.

**Change D — Null guards** on `document.getElementById('save-btn')`
and `document.getElementById('notes-<id>')`. Prevents a null-ref
exception from breaking a rendered entity page.

## Files touched

- `scripts/build_v3_viewer.py`:
  - `SE_VIEW_NARRATIVES`: removed `pipeline` entry
  - `_mermaid_pipeline()`: generalized to `(entities, rels, cap_id="CAP-PB") -> tuple | None`;
    orchestrator concept replaced by entry-behavior discovery; output interfaces
    generalized from BEH-publish hardcode
  - `_build_se_views()`: removed `pipeline` from views dict
  - `_build_payload()`: stamps `flow_mermaid` + `flow_refs` on each
    capability record when applicable
  - HTML: removed `<a class="entity-link" data-se="pipeline">…` sidebar link
  - JS `renderSidebar()`: replaced per-element listeners with delegation on `#entity-groups`
  - JS `selectEntity()`: added diagnostic warn, try/catch wrapper, null
    guards on save-btn / notes-<id>, and inline flow Mermaid card for
    capabilities with `flow_mermaid`
- `.architecture/viewers/v3_viewer.html` — auto-regenerated
- `.architecture/viewers/v3_viewer_data.json` — auto-regenerated

## Verification (mine, before commit)

1. **Build clean:** `python scripts/build_v3_viewer.py` — 67 entities,
   773 promises, 127 relationships, no errors.
2. **Byte-determinism:** double-build + diff — DETERMINISTIC.
3. **JS syntax:** `node --check` on extracted script tag — JS_OK.
4. **Data-side assertions** (all pass):
   - `'pipeline' not in se_views` — top-level view removed
   - `se_views keys == ['conops','functional','logical','use_cases']`
   - `CAP-PB.flow_mermaid` present (1561 chars, 11 refs)
   - `CAP-PB.flow_mermaid` starts with `flowchart`
   - No other capability has `flow_mermaid` today (as expected)
   - `data-se="pipeline"` string absent from HTML
   - `"CAP-PB Pipeline Flow"` label absent from HTML
5. **Flow content spot-check:** printed CAP-PB.flow_mermaid — full
   7-stage chain scan→derive-promises→cluster→link→containerize→verify
   →publish, orchestrator BEH-run-pipeline, 2 actors (ACT-ci,
   ACT-developer), output IF-model, v2-palette color classes correct.

## Open items (user-side verification)

Please open the viewer, hard-reload, and:

1. **Click CAP-PB** in the sidebar under **capabilities**. Confirm the
   inline flow card renders above the promises grid.
2. **Click 5 components** across the alphabet: COMP-1896b055 (core),
   COMP-3523c3b8 (extract), COMP-95656df0, COMP-c5a72728,
   COMP-fa350824. Confirm each opens.
3. **With DevTools console open**, report:
   - Any `selectEntity miss:` warnings → cause was `byId` map miss
   - Any red console errors → cause was render-time exception
   - No warnings, no errors, entities open → cause was listener
     attachment / DOM re-render orphaning (event delegation fixed it)

## Handoff to Task B

Task B adds cross-pipeline `triggers` edges to close the CAP-DF dev
loop:
- `walk-author` → `run-pipeline` (BEH-walk-author triggers BEH-run-pipeline)
- `run-pipeline` → `view-browse` (or a "reload viewer" behavior — TBD)
- `view-note` → `walk-author`

Once these edges land, CAP-DF.1 and CAP-DF.2 will each pick up an
inline flow diagram in their entity pages automatically — no viewer
code change required. The substrate does the work.
