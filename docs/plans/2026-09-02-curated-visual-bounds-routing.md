# Curated Visual Bounds and Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bound every curated panel while eliminating callout and ConOps routes through unrelated nodes without losing recursively accessible entities.

**Architecture:** Add deterministic recursive spec pagination at the projector/spec boundary, retaining primary context and exposing omitted records through typed summary drilldowns. Route targeted callouts and operational-lane edge classes through separate orthogonal exterior channels; leave untargeted notices in the footer only. Keep semantic edges intact and compact their visible labels.

**Tech Stack:** Python dataclasses, deterministic SVG generation, pytest, XML geometry assertions.

---

### Task 1: Lock Down Callout Routing

**Files:**
- Modify: `tests/test_diagram_renderer.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`

1. Add failing tests proving untargeted callouts have no connector and targeted connectors are orthogonal and avoid unrelated node rectangles.
2. Run focused tests and confirm failure.
3. Implement obstacle-aware footer connector routing.
4. Run focused tests and confirm pass.

### Task 2: Lock Down Operational Lanes

**Files:**
- Modify: `tests/test_diagram_renderer.py`
- Modify: `tests/test_conops_projector.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`
- Modify: `src/architecture_model/core/se_view_projectors.py`

1. Add failing route-analyzer tests for source, scenario-chain, boundary, and outcome channels.
2. Add label-compaction assertions while retaining all semantic edge records.
3. Implement separate exterior orthogonal channels and safe boundary ports.
4. Run focused tests and confirm pass.

### Task 3: Bound Recursive Drilldowns

**Files:**
- Modify: `tests/test_diagram_spec.py`
- Modify: `tests/test_*_projector.py`
- Modify: `src/architecture_model/core/diagram_spec.py`
- Modify: `src/architecture_model/core/se_view_projectors.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`

1. Add failing tests for <=25 nodes, <=40 edges, deterministic nested summary pages, complete recursive entity coverage, and sequence order.
2. Implement deterministic recursive bounding with typed `More ... (N)` nodes and bounded depth.
3. Wrap long linear layouts into columns/lanes and enforce <=2400x1800 render bounds.
4. Run focused projector and renderer tests.

### Task 4: Verify Actual Artifacts and Parity

**Files:**
- Modify: `tests/test_curated_viewer.py`

1. Add the actual logs-db viewer traversal test for dimensions, drilldown references, recursive coverage, ConOps routes, and Use Case callouts.
2. Verify viewer/export/docs overview parity, themes, and security tests.
3. Run `pytest tests/ -v --ignore=tests/test_config_loader.py`, compare only against the nine known failures, and run the architecture gate.
4. Commit all intended source, tests, and plan changes once as `fix(viewer): bound curated drilldowns and routing`, excluding telemetry dirt.
