# Curated Drilldown Layouts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace generic drilldown flowcharts with compact semantic layouts and make the curated logs-db views satisfy geometry and readability regressions.

**Architecture:** Projectors assign semantic `DiagramSpec.layout` modes and structural lanes/groups. The native renderer dispatches each mode to a deterministic compact placement and local orthogonal routing strategy while preserving existing spec bounding, nested drilldowns, metadata, and security behavior.

**Tech Stack:** Python dataclasses, deterministic SVG generation, pytest, optional `rsvg-convert` PNG regression.

---

### Task 1: Specify Semantic Drilldowns

**Files:**
- Modify: `tests/test_conops_projector.py`
- Modify: `tests/test_functional_projector.py`
- Modify: `tests/test_logical_projector.py`
- Modify: `tests/test_use_case_projector.py`
- Modify: `src/architecture_model/core/se_view_projectors.py`

1. Add failing assertions for ConOps detail cards, functional allocation sections, populated ordered logical lanes, and ordered use-case sequence sections.
2. Run the four focused projector suites and confirm failures identify generic drilldown layouts.
3. Assign semantic layouts and section membership in the projectors; omit empty logical lanes and emit `LOGICAL_EMPTY_GROUP_OMITTED` diagnostics.
4. Re-run the projector suites and confirm they pass.

### Task 2: Render Compact Semantic Modes

**Files:**
- Modify: `tests/test_diagram_renderer.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`

1. Add failing renderer tests for layout ordering, utilization, canvas bounds, empty containers, edge-node intersections, edge crossings, and ConOps label visibility/title retention.
2. Run focused renderer tests and confirm failures.
3. Implement compact card, functional allocation, logical lane, and use-case sequence placement plus local orthogonal routes and label decluttering.
4. Re-run renderer tests and confirm they pass.

### Task 3: Exercise Actual logs-db Rendering

**Files:**
- Modify: `tests/test_curated_viewer.py`

1. Add an optional regression selecting the largest panel in each actual logs-db view, rendering SVG and PNG when `rsvg-convert` is available, and checking utilization, dimensions, crossings, route-through-node, empty containers, and ConOps label geometry.
2. Run the regression and use failures to make minimal projector/renderer corrections.
3. Re-run curated viewer and all focused projector/renderer suites.

### Task 4: Verify and Commit

**Files:**
- Verify all changed source and test files.

1. Run `pytest tests/test_conops_projector.py tests/test_functional_projector.py tests/test_logical_projector.py tests/test_use_case_projector.py tests/test_diagram_renderer.py tests/test_curated_viewer.py -v`.
2. Run `pytest tests/ -v --ignore=tests/test_config_loader.py`.
3. Run architecture checks and inspect the final diff/status.
4. Commit once with `fix(viewer): refine curated drilldown layouts`.
