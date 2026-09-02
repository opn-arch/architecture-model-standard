# Executive Diagram Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the curated ConOps, use-case, and logical diagrams compact, legible, and geometrically safe using strict test-first changes.

**Architecture:** Keep projector semantics intact and specialize deterministic placement/routing for the three existing layout modes. Make measured text wrapping, clipping, and compact edge-label metadata shared renderer guarantees, then exercise the real logs-db optional profile through SVG geometry and rsvg PNG acceptance checks.

**Tech Stack:** Python, deterministic SVG, ElementTree geometry assertions, pytest, optional `rsvg-convert`.

---

### Task 1: Specify Shared Text Safety

**Files:**
- Modify: `tests/test_diagram_renderer.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`

1. Add hostile long-token tests requiring a unique per-node clip path and bounded text metadata.
2. Run the focused tests and verify they fail for missing clips.
3. Implement pixel-estimated wrapping/ellipsis and clipped node text groups.
4. Re-run focused tests.

### Task 2: Specify ConOps Operational Lanes

**Files:**
- Modify: `tests/test_diagram_renderer.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`

1. Add real logs-db assertions for centered singleton lanes, node-derived lane bounds, compact labels and local route buses.
2. Run the focused test and verify the current top alignment/perimeter routing fails.
3. Implement centered lane placement, compact label metadata, and source/chain/delivery/outcome buses.
4. Re-run the focused test.

### Task 3: Specify Actor-Owned Use-Case Bands

**Files:**
- Modify: `tests/test_diagram_renderer.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`

1. Add real logs-db assertions for exactly two actor bands, 4/6 associated cases, in-band routes, and zero crossings.
2. Run the focused test and verify the column catalog fails.
3. Implement actor-row placement with at most five cases per subrow and one local participation bus per row.
4. Re-run the focused test.

### Task 4: Specify Logical Tier Gutters

**Files:**
- Modify: `tests/test_diagram_renderer.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`
- Modify: `src/architecture_model/core/se_view_projectors.py`

1. Add assertions that dependency routes avoid lane borders/headers, cycle labels are hidden, cycles are thin, and isolated badges are concise.
2. Run the focused test and verify current border routing/labels fail.
3. Route cross-tier dependencies through inter-tier gutters, hide dependency labels while retaining full metadata, and shorten isolated badges.
4. Re-run the focused test.

### Task 5: Visual and Full Verification

**Files:**
- Verify all changed source, tests, and plan files.

1. Generate all four real logs-db SVG/PNG outputs into a temporary review directory.
2. Inspect the three affected PNGs directly and correct only demonstrated geometry defects.
3. Run focused projector/renderer/viewer tests.
4. Run `pytest tests/ -v --ignore=tests/test_config_loader.py`.
5. Run architecture checks, inspect diff/status, and commit `fix(viewer): polish executive diagram layouts`.
