# View-Aware Presentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce semantically correct, compact, collision-free curated SE diagrams with deterministic view-aware SVG layouts.

**Architecture:** Projectors emit view semantics and select a renderer-neutral layout mode. The native SVG renderer dispatches to deterministic mode-specific placement and routing while retaining its generic fallback.

**Tech Stack:** Python dataclasses, pytest, XML/SVG geometry assertions, optional librsvg (`rsvg-convert`).

---

### Task 1: Lock Projector Semantics

**Files:**
- Modify: `tests/test_conops_projector.py`
- Modify: `tests/test_logical_projector.py`
- Modify: `tests/test_use_case_projector.py`
- Modify: `src/architecture_model/core/se_view_projectors.py`

1. Add failing tests for layout metadata, ConOps lane assignment and connected boundary, logical actor/summary suppression and dependency aggregation, and use-case omission callouts.
2. Run the focused projector tests and confirm the new assertions fail.
3. Implement only the semantic projection changes needed by those tests.
4. Run the focused projector tests and confirm they pass.

### Task 2: Lock Renderer Geometry

**Files:**
- Modify: `tests/test_diagram_renderer.py`
- Modify: `src/architecture_model/core/diagram_renderer.py`

1. Add failing SVG geometry tests for all four modes, including lane containment, boundary degree, canvas bounds/utilization, label collisions, and reciprocal path distinction.
2. Run each new test and confirm it fails for the expected geometry reason.
3. Add deterministic mode-specific node layout, routing, compact labels, and label collision allocation while preserving generic rendering.
4. Run renderer and projector tests and confirm they pass.

### Task 3: Real Render Harness

**Files:**
- Create: `tests/test_curated_se_rendering.py`
- Modify only if required: `src/architecture_model/core/diagram_renderer.py`

1. Add an optional logs-db fixture test and rsvg PNG review harness with objective SVG assertions.
2. Run it against the available fixture and confirm failures reflect the supplied render defects.
3. Make minimal renderer adjustments until geometry and PNG generation pass.
4. Render the four diagrams and inspect resulting PNGs.

### Task 4: Verify And Commit

**Files:** all files changed above.

1. Run focused projector, renderer, and visual integration tests.
2. Run `pytest tests/ -v --ignore=tests/test_config_loader.py`.
3. Run architecture representativeness and completion gates.
4. Inspect the final diff and commit once with a concise presentation-fix message.
