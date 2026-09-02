# Curated Rendering Outputs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make viewer, standalone exports, and SE documents render the same curated architecture views with reliable contrast and bounded, noncrossing executive layouts.

**Architecture:** Add one core assembly helper that loads `ArchitectureViewContext`, resolves optional curation, projects the four native `DiagramSpec` objects, and renders them with a caller-selected theme. Viewer uses dark panels; exports and document assets use light panels. Keep model-only document generator APIs unchanged.

**Tech Stack:** Python 3.11+, dataclasses, native SVG/XML, pytest, optional librsvg and logs-db integration fixtures.

---

### Task 1: Lock Shared Output Behavior With Failing Tests

**Files:**
- Modify: `tests/test_curated_viewer.py`
- Modify: `tests/test_se_docs.py`
- Modify: `tests/test_diagram_renderer.py`
- Modify: `tests/test_conops_projector.py`
- Modify: `tests/test_logical_projector.py`

1. Assert viewer panel metadata and all nested SVGs use dark theme and explicit attributes.
2. Assert standalone exports use light theme and exactly match viewer/doc `DiagramSpec` node and edge IDs under the same curation.
3. Assert no-curation and explicit-curation plumbing.
4. Correct the logs-db semantic bundling expectation to four overview external nodes preserving five drilldown entries.
5. Assert ConOps crossings/collisions/dimensions and logical hidden labels/cycle styling.
6. Run focused tests and confirm failures precede implementation.

### Task 2: Resolve SVG Palette Explicitly

**Files:**
- Modify: `src/architecture_model/core/diagram_renderer.py`
- Test: `tests/test_diagram_renderer.py`

1. Define resolved light/dark palettes with accessible text, surfaces, strokes, and cycle colors.
2. Emit explicit `fill`, `stroke`, and marker colors on critical SVG presentation elements instead of relying on CSS variables.
3. Keep CSS classes for semantics and viewer interaction.
4. Run renderer tests, including optional `rsvg-convert` sampling.

### Task 3: Add Shared Curated View Assembly

**Files:**
- Create: `src/architecture_model/core/curated_views.py`
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `src/architecture_model/docs/se/generator.py`
- Modify: `src/architecture_model/cli/main.py`
- Test: `tests/test_curated_viewer.py`
- Test: `tests/test_se_docs.py`
- Test: `tests/test_cli_visualize.py`

1. Build one context and resolve default, explicit, or disabled curation.
2. Project all four specs once and render every overview/drilldown in the selected theme.
3. Use dark output in viewer and light output in SVG exports and SE docs.
4. Add visualize CLI `--curation`/`--no-curation` options and pass them through.
5. Keep direct model-only SE generator calls narrative-only.

### Task 4: Deterministic Executive Routing

**Files:**
- Modify: `src/architecture_model/core/diagram_renderer.py`
- Modify: `src/architecture_model/core/se_view_projectors.py` only if projection metadata must distinguish route roles
- Test: `tests/test_diagram_renderer.py`
- Test: `tests/test_conops_projector.py`
- Test: `tests/test_logical_projector.py`

1. Route operational-lane external inputs, scenario chain, boundary delivery, and outcomes on deterministic separated buses.
2. Hide low-priority crowded labels while retaining full edge title/provenance.
3. Hide logical single dependency labels and retain only safe aggregate labels.
4. Render cycles with a thinner accessible amber/red stroke and reciprocal summary semantics.
5. Verify crossings, node/label collisions, clipping, and 1800x1200 bounds on the temp fixture and optional logs-db profile.

### Task 5: Verify and Commit

**Files:**
- All files above

1. Run focused projector, renderer, viewer, CLI, and SE-doc tests.
2. Run `pytest tests/ -v --ignore=tests/test_config_loader.py` and compare failures with the known nine-failure baseline.
3. Run architecture representativeness and completion gates.
4. Stage only implementation, tests, and this plan; preserve telemetry dirt unstaged.
5. Commit as `fix(viewer): unify curated rendering outputs`.
