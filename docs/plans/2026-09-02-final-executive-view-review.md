# Final Executive View Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve final semantic, theme, and geometry review findings without editing logs-db curation.

**Architecture:** Projectors retain exact evidence-backed semantics and expose layout data through existing nodes/edges. The renderer adds explicit palettes and specialized deterministic use-case placement/routing.

**Tech Stack:** Python, dataclasses, pytest, SVG/XML, optional librsvg.

---

### Task 1: External Roles and Exact ConOps Semantics

**Files:** `src/architecture_model/core/view_curation.py`, `src/architecture_model/core/se_view_projectors.py`, `tests/test_view_curation.py`, `tests/test_conops_projector.py`

1. Add failing allowlist, unknown-role non-bundling, exact participant, curated-outcome precedence, and outcome-edge tests.
2. Run focused tests and confirm expected failures.
3. Implement strict kind parsing, role-aware keys, exact participant collection, explicit-primary outcomes, and scenario-to-outcomes edges/drilldown mapping.
4. Run focused tests to green.

### Task 2: Explicit SVG Themes

**Files:** `src/architecture_model/core/diagram_renderer.py`, `tests/test_diagram_renderer.py`

1. Add failing light/dark option, panel payload, contrast, background, and optional PNG pixel tests.
2. Run tests and confirm failures.
3. Add validated theme options, fixed palettes/backgrounds, panel theme serialization, and drilldown propagation.
4. Run renderer tests to green.

### Task 3: Use-Case Catalog Geometry

**Files:** `src/architecture_model/core/diagram_renderer.py`, `tests/test_diagram_renderer.py`

1. Add failing actor-lane, contiguous membership, shared-case centering, bus routing, and crossing analyzer tests.
2. Confirm red on actual logs-db.
3. Implement membership-aware catalog placement and participation bus routing.
4. Run use-case and renderer tests to green.

### Task 4: Logical Isolates and Geometry

**Files:** `src/architecture_model/core/se_view_projectors.py`, `src/architecture_model/core/diagram_renderer.py`, `tests/test_logical_projector.py`, `tests/test_diagram_renderer.py`

1. Add failing explicit isolate badge and logical crossing objective tests.
2. Confirm red.
3. Rename isolate badge and minimally adjust deterministic routes if needed.
4. Run logical tests to green.

### Task 5: Verification and Commit

1. Run focused viewer suites with `PYTHONPATH=src`.
2. Run `PYTHONPATH=src pytest tests/ -v --ignore=tests/test_config_loader.py`.
3. Run architecture checks and record pre-existing gate limitations.
4. Commit all task files in one new commit with an accurate review-fix message.
