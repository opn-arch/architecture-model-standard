# Executive Architecture Backbones Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add evidence-backed curated ConOps semantics, a lossless deterministic logical backbone, and crossing-minimized executive SVG rendering.

**Architecture:** Extend the presentation-only curation and diagram-spec types, keeping canonical architecture entities immutable. Curated projectors aggregate only overview presentation while preserving complete semantics in embedded drilldowns/facets; the renderer consumes layout hints deterministically.

**Tech Stack:** Python 3.11+, dataclasses, PyYAML, pytest, XML/SVG, optional librsvg.

---

### Task 1: Evidence-Backed Scenario Schema

**Files:**
- Modify: `src/architecture_model/core/view_curation.py`
- Test: `tests/test_view_curation.py`

**Step 1: Write the failing tests**

Add tests that load a scenario containing `goal`, `outcomes`, `requirements`, `moes`, and repo-contained structured `evidence`; assert a typed `CuratedScenario` with resolved members. Add parameterized failures for unknown keys, malformed lists, annotations without evidence, missing/escaping evidence files, and unsafe text; assert the ConOps view fails closed.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_view_curation.py -v`

Expected: FAIL because scenario annotations are unsupported and scenarios are generic `CuratedGroup` values.

**Step 3: Write minimal implementation**

Add `CuratedScenario` with group fields plus annotation fields and evidence. Parse scenarios separately from `_groups`, validate every list through `_safe_text_list`, require `_evidence` whenever any annotation is nonempty, preserve strict key checking, and include scenarios in semantic ID/member validation.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_view_curation.py -v`

Expected: PASS.

### Task 2: Curated ConOps Semantic Aggregates

**Files:**
- Modify: `src/architecture_model/core/se_view_projectors.py`
- Test: `tests/test_conops_projector.py`

**Step 1: Write the failing tests**

Build a five-scenario fixture with five inferred externals, missing canonical outcomes, direct systems, and behavior component ownership. Assert exactly five scenario nodes, two bundled external nodes, one nonempty `Operational Outcomes` node, one connected boundary, at most 15 nodes, labels no longer than 22 characters, and no context-model mutation. Assert external, outcome, and boundary drilldowns preserve all five externals, scenario-specific outcomes, and all eight systems with evidence/provenance.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_conops_projector.py -v`

Expected: FAIL on annotation fallback, two-way external bundling, ownership-derived boundary systems, and lossless outcome drilldown.

**Step 3: Write minimal implementation**

Add helpers to collect canonical-first scenario semantics, participating systems, and compatible convergent external bundles. Emit one shared outcomes aggregate and drilldown, stable external bundles with child drilldowns, and a connected operational boundary. Preserve full labels in edge titles/provenance while applying `_compact_edge_label` to visible labels.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_conops_projector.py tests/test_view_curation.py -v`

Expected: PASS.

### Task 3: Lossless Logical Backbone

**Files:**
- Modify: `src/architecture_model/core/diagram_spec.py`
- Modify: `src/architecture_model/core/se_view_projectors.py`
- Test: `tests/test_logical_projector.py`
- Test: `tests/test_diagram_spec.py`

**Step 1: Write the failing tests**

Create a deterministic 19-edge, five-tier fixture with connected nodes, one reciprocal cycle, interface exchanges, and shuffled input order. Assert explicit curated mode keeps all displayed systems/aggregates, selects at most nine edges, preserves canonical connectivity, emits at most one overview cycle pair, and produces identical output after shuffling. Assert the full 19-edge payload and both cycle directions survive in facets/provenance and relevant drilldowns. Assert truly disconnected nodes are marked `isolated`.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_logical_projector.py tests/test_diagram_spec.py -v`

Expected: FAIL because `DiagramSpec` has no facets and logical overview emits every aggregate edge.

**Step 3: Write minimal implementation**

Add a JSON-safe `facets` mapping to `DiagramSpec` validation and round-trip serialization. Build all canonical aggregate edges first, collapse reciprocal cycle display candidates, and select a weighted maximum-spanning forest followed by bounded interface/critical/cycle extras. Store complete edge dictionaries in `facets["logical_dependencies"]`, counts in overview provenance/callout, and complete relevant edges in system and aggregate drilldowns. Mark only canonically disconnected overview nodes.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_logical_projector.py tests/test_diagram_spec.py -v`

Expected: PASS.

### Task 4: Deterministic Crossing-Minimized Layout and Routing

**Files:**
- Modify: `src/architecture_model/core/diagram_renderer.py`
- Test: `tests/test_diagram_renderer.py`

**Step 1: Write the failing tests**

Add reusable orthogonal segment analyzers that exclude shared endpoints/trunks and count proper edge-edge and edge-label crossings. Add fixtures for convergent operational sources, a functional graph requiring adjacent-rank reordering, and tiered logical backbone routing. Assert operational and functional zero crossings and logical at most three, unique source-segment label placement, monotonic scenario paths, and deterministic SVG under shuffled input.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_diagram_renderer.py -v`

Expected: FAIL with crossings under lexical lane/rank ordering and independent track routing.

**Step 3: Write minimal implementation**

Apply stable median/barycentric down/up sweeps to functional ranks and lane members. Introduce layout-specific route planning: shared convergent buses for operational edges, monotonic scenario tracks, aggregated boundary trunks, and crossing-scored local tracks for logical edges. Anchor labels to source-unique segments and retain full detail in edge titles.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_diagram_renderer.py -v`

Expected: PASS.

### Task 5: Transparent Standalone SVG Contrast

**Files:**
- Modify: `src/architecture_model/core/diagram_renderer.py`
- Test: `tests/test_diagram_renderer.py`

**Step 1: Write the failing test**

Assert rendered SVG has no opaque canvas fill, defines explicit light/dark-safe foreground and label-halo variables, applies an explicit readable color to title/footer/source text, and remains parseable.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_diagram_renderer.py -k transparent -v`

Expected: FAIL because current footer text inherits a light-theme-only color.

**Step 3: Write minimal implementation**

Define SVG CSS variables with explicit foreground values and `@media (prefers-color-scheme: dark)` overrides. Keep the canvas transparent, use variables for all text, and retain a contrasting paint-order halo for labels.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_diagram_renderer.py -k transparent -v`

Expected: PASS.

### Task 6: Optional Actual-Profile Geometry and Full Verification

**Files:**
- Modify: `tests/test_conops_projector.py`
- Modify: `tests/test_logical_projector.py`
- Modify: `tests/test_diagram_renderer.py`

**Step 1: Tighten optional integration tests**

Without editing `/Users/baigm2/Documents/Projects/logs_db/.architecture/viewer-curation.yaml`, assert its curated projection has five scenarios, two external aggregates, one nonempty outcomes aggregate, a connected boundary with eight-system drilldown, five logical lanes/eight systems/three aggregates, no semantic loss, ConOps and Functional zero crossings, Logical at most three, and canvas at most `1800x1200`. Render through `rsvg-convert` when installed.

**Step 2: Run focused suite**

Run: `pytest tests/test_view_curation.py tests/test_conops_projector.py tests/test_functional_projector.py tests/test_logical_projector.py tests/test_diagram_spec.py tests/test_diagram_renderer.py -v`

Expected: PASS (optional tests may skip only when external profile/tool is unavailable).

**Step 3: Run full suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`

Expected: PASS with only documented skips.

**Step 4: Run architecture checks**

Run `architect_check` and `architect_gate` for the curated worktree. Expected: representativeness reported and phase requirements met.

**Step 5: Commit once as requested**

```bash
git add docs/plans/2026-09-02-executive-architecture-backbones-design.md docs/plans/2026-09-02-executive-architecture-backbones.md src/architecture_model/core/view_curation.py src/architecture_model/core/diagram_spec.py src/architecture_model/core/se_view_projectors.py src/architecture_model/core/diagram_renderer.py tests/test_view_curation.py tests/test_conops_projector.py tests/test_logical_projector.py tests/test_diagram_spec.py tests/test_diagram_renderer.py
git status --short --branch
```

Expected: commit succeeds and worktree is clean.
