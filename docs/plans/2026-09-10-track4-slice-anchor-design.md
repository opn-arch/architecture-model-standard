# Track 4 Design — Slice Anchor for Viewer Panels

**Date:** 2026-09-10
**Status:** Approved (2026-09-10)
**Pass:** 1 of N (functional panel end-to-end; other panels compute anchor but do not consume yet)

## Problem

Viewer panels (`conops`, `functional`, `logical`, `use_cases`) in `.architecture/diagrams/viewer.html` currently render from the full `ArchitectureModel`. Their content is not anchored to any explicit, deterministic scope over `(model, files, artifacts)`. This means:

- We cannot audit what a panel is "about" without reading the rendered output.
- Curation drift (see Track 3) is invisible until the viewer surfaces phantom refs.
- There is no ground-truth mapping between what the model says and what the page shows.

The `architecture_model.core.slicer` module already exposes `slice_for_artifact(model, artifact_name)` with named per-artifact slicers (`_slice_for_functional`, `_slice_for_logical`, `_slice_for_use_cases`, `_slice_for_conops`, and more) — but nothing in the viewer pipeline invokes it. `_cmd_viewer` in `src/architecture_model/cli/main.py:1141` loads the full model and passes it directly to `generate_html_viewer`, which routes it into every panel generator.

## Goal

For every viewer panel there is exactly one **`SliceAnchor`** — a deterministic tuple `(sliced_model, files, artifacts)` derived from the view name. No YAML changes to `viewer-curation.yaml`. The anchor is computed at viewer entry time, before any panel diagram generator runs. Panels render only from the anchored model.

## Non-goals

- Changing the on-disk `viewer-curation.yaml` schema.
- Adding an LLM call anywhere in the anchor derivation.
- Applying anchors to all four panels in this pass. Pass 1 is functional-only. Other views compute anchors (for observability) but panel generators still receive the full model.
- Filtering the underlying model file. The full model stays intact; only what the viewer renders is scoped.

## Design

### §1 — Anchor definition

New dataclass in `src/architecture_model/core/slice_anchor.py`:

```python
@dataclass(frozen=True)
class SliceAnchor:
    view_name: str                   # "functional" | "logical" | "use_cases" | "conops"
    artifact_name: str               # "functional-architecture" | ...
    model: ArchitectureModel         # slice_for_artifact + 1-hop closure
    files: tuple[str, ...]           # sorted union of component.source_files
    artifacts: tuple[str, ...]       # from name table + optional front-matter scan
```

Constants (not YAML):

```python
VIEW_TO_ARTIFACT = {
    "conops": "conops",
    "functional": "functional-architecture",
    "logical": "logical-architecture",
    "use_cases": "use-cases",
}
ARTIFACT_TO_DOC = {
    "conops": ".architecture-models/docs/se/conops.md",
    "functional-architecture": ".architecture-models/docs/se/functional-analysis.md",
    "logical-architecture": ".architecture-models/docs/se/logical-architecture.md",
    "use-cases": ".architecture-models/docs/se/use-cases.md",
}
```

### §2 — 1-hop closure algorithm

After `slice_for_artifact(full_model, artifact_name)`, compute 1-hop closure:

1. Start with `S = set(sliced entity IDs)`.
2. For each relationship `r` in **full_model.relationships** whose `type ∈ {realizes, contains, depends-on}`:
   - If `r.from_id ∈ S` and `r.to_id ∉ S`: add `r.to_id`'s entity and `r` to the slice.
   - If `r.to_id ∈ S` and `r.from_id ∉ S`: add `r.from_id`'s entity and `r` to the slice.
3. One pass only. No transitive expansion.

Iteration order is sorted by `(entity_id, from_id, to_id)` for determinism. Entities added by closure are deep-copied from the full model, exactly as `slice_for_artifact` deep-copies its own retained entities.

### §3 — files derivation

```python
files = tuple(sorted({sf
    for c in anchored_model.entities.components
    for sf in c.source_files}))
```

Empty tuple is legal (e.g., a conops slice may contain no components).

### §4 — artifacts derivation

1. Start with `artifacts = [ARTIFACT_TO_DOC[artifact_name]]` if the file exists on disk.
2. Scan `.architecture-models/docs/se/*.md` for a YAML front-matter block containing `artifact: <artifact_name>`. Append every match.
3. Deduplicate and sort. Missing files skipped without error.

Front-matter scan is best-effort. A missing `.architecture-models/` directory returns just step 1 (or empty tuple if that file is also missing).

### §5 — Wiring

New helper `build_slice_anchor(model, view_name, repo_path) -> SliceAnchor` in `src/architecture_model/core/slice_anchor.py`.

Call sites:

- `src/architecture_model/cli/main.py:_cmd_viewer` (line ~1141) — after `load_model`, compute `anchors = {v: build_slice_anchor(model, v, repo_path) for v in VIEW_NAMES}` and pass `anchors=` kwarg to `generate_html_viewer`.
- `src/architecture_model/core/visualize.py:generate_html_viewer` (line 2421) — accept optional `anchors: dict[str, SliceAnchor] | None = None` kwarg. When routing to the functional panel generator (Pass 1), substitute `anchors["functional"].model` for the full `model`. Other three panels still receive the full model in Pass 1.
- New feature gate constant `_APPLY_ANCHOR: set[str] = {"functional"}` inside `visualize.py`. Determines which panels consume anchors in Pass 1. Later passes flip additional entries.

### Pass-1 scope

- Compute anchors for all four views.
- Consume only the `functional` anchor.
- Emit a debug log `viewer: anchor computed view=<v> entities=<n> files=<n> artifacts=<n>` per anchor at INFO level.

### Failure modes

- If `slice_for_artifact` returns an empty model (unknown artifact): `build_slice_anchor` returns an anchor with the full model as fallback and logs `WARN viewer: no slicer for view=<v>`. Prevents pass-1 regression on unmapped views.
- If `component.source_files` is missing on some components: skipped silently. Files tuple is best-effort.
- Front-matter parse error on a docs file: skipped silently, continue.

## Test plan (TDD)

1. `tests/core/test_slice_anchor.py` — unit tests on `build_slice_anchor` for each of the 4 views + 1 fallback case. Assert entity counts, files sorted-unique, artifacts exist.
2. `tests/core/test_slice_anchor_closure.py` — 1-hop closure specifics: components realizing capabilities pulled back into functional slice; no transitive expansion beyond one hop.
3. `tests/test_viewer_anchored.py` — functional panel HTML contains only entities from the anchor; a capability outside the anchor's `entities` set does NOT appear in the functional Mermaid block.
4. Regression: existing viewer tests (`tests/test_viewer_v3.py`, `tests/test_curated_viewer.py`) continue to pass — other 3 panels unchanged in Pass 1.

## Blast radius

- New file: `src/architecture_model/core/slice_anchor.py` (dataclass + `build_slice_anchor`).
- `src/architecture_model/cli/main.py` `_cmd_viewer` (line 1141) — pass `anchors=` kwarg.
- `src/architecture_model/core/visualize.py` `generate_html_viewer` (line 2421) — accept kwarg, route functional panel through anchor.
- No YAML changes.
- No changes to slicer.py, view_curation.py, or any panel diagram generator body.

## Follow-ups (out of scope for Pass 1)

- Pass 2: consume `logical`, `use_cases`, `conops` anchors.
- Pass 3: emit anchor summary into viewer HTML metadata (`data-slice-anchor` on each panel), enabling reader audit.
- Pass 4: expose `SliceAnchor` on curation load — fail viewer generation if `curation.featured` contains IDs outside `anchor.model`. Ties Track 4 back into Track 3's curation cleanup.
