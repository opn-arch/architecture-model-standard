# Native Diagram Renderer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Render curated `DiagramSpec` values as deterministic, safe, accessible offline SVG and JSON-safe interaction panel payloads.

**Architecture:** Add one stdlib-only core renderer with private layout and SVG serialization helpers. Public functions return SVG, a frozen structured panel, and an exact drilldown panel map; existing visualization/HTML code remains unchanged.

**Tech Stack:** Python dataclasses, XML/SVG, `html`, `json`, `textwrap`, pytest.

---

### Task 1: Define structural and safety contracts

**Files:**
- Create: `tests/test_diagram_renderer.py`

**Step 1:** Add representative LR/TB specs covering groups, lanes, all semantic shapes, parallel edges, callouts, diagnostics, provenance, hostile values, interactions, and nested drilldowns.

**Step 2:** Add XML structural assertions for node/edge/group counts, bounding-box separation, distinct edge paths, escaping, accessibility attributes, global bounds, viewBox, deterministic shuffled input, and exact drilldown mapping.

**Step 3:** Run `pytest tests/test_diagram_renderer.py -v` and verify collection fails because `architecture_model.core.diagram_renderer` does not exist.

### Task 2: Implement layout and SVG rendering

**Files:**
- Create: `src/architecture_model/core/diagram_renderer.py`
- Test: `tests/test_diagram_renderer.py`

**Step 1:** Define frozen JSON-safe renderer option, toolbar action, and panel result dataclasses.

**Step 2:** Implement stable rank/container-aware LR/TB layout with fixed spacing, bounded dimensions, group expansion, and parallel-edge offsets.

**Step 3:** Implement escaped semantic SVG primitives, edge markers/styles/evidence titles, wrapped text, interactions, legend, callouts, diagnostics, and provenance footer.

**Step 4:** Implement standalone SVG, panel, and exact recursive drilldown-map public APIs.

**Step 5:** Run `pytest tests/test_diagram_renderer.py -v`, make the minimal corrections needed, and verify all focused tests pass.

### Task 3: Verify and review

**Files:**
- Review: `src/architecture_model/core/diagram_renderer.py`
- Review: `tests/test_diagram_renderer.py`

**Step 1:** Run `pytest tests/ -v --ignore=tests/test_config_loader.py` and compare failures with the known baseline.

**Step 2:** Inspect `git diff --check`, the complete diff, API safety, deterministic ordering, and test gaps; fix any findings and rerun affected tests.

**Step 3:** Run the architecture gate and record any model-health limitation separately from code correctness.

**Step 4:** Commit the intended implementation and tests as `feat(viewer): render curated diagrams offline` without including unrelated worktree changes.
