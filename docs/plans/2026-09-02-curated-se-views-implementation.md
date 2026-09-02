# Curated SE Architecture Views Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build hierarchy-aware, curated ConOps, Functional Architecture, Logical Architecture, and Use Case overview/drilldown views rendered as native offline SVG.

**Architecture:** Introduce a renderer-neutral `DiagramSpec` and a hierarchy-aware `ArchitectureViewContext`; four small projectors reduce model semantics into deterministic overview and drilldown specs. Optional `.architecture/viewer-curation.yaml` changes presentation only, while the existing HTML viewer and SE document generators consume the same projections and native SVG renderer.

**Tech Stack:** Python 3.11 dataclasses, PyYAML, existing architecture-model types/hierarchy loader, inline SVG/XML, pytest.

---

### Task 1: Define The Semantic Diagram Contract

**Files:**
- Create: `src/architecture_model/core/diagram_spec.py`
- Create: `tests/test_diagram_spec.py`

**Step 1: Write the failing tests**

Add tests for stable node/edge/group IDs, semantic roles, drilldown references, provenance and diagnostics serialization, duplicate-ID rejection, and deterministic dictionary output.

```python
def test_spec_serializes_semantics_and_provenance():
    spec = DiagramSpec(id="conops", title="ConOps")
    spec.add_node(DiagramNode(id="ACT-1", label="Operator", role="actor",
                              provenance=[Provenance(kind="model", ref="ACT-1")]))
    assert spec.to_dict()["nodes"][0]["provenance"][0]["ref"] == "ACT-1"
```

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_diagram_spec.py -v`

Expected: FAIL because `architecture_model.core.diagram_spec` does not exist.

**Step 3: Implement the minimal contract**

Add frozen provenance/diagnostic records and mutable `DiagramNode`, `DiagramEdge`, `DiagramGroup`, and `DiagramSpec` dataclasses. Validate references and duplicate IDs at insertion/finalization, sort only at serialization boundaries, and expose plain JSON-safe dictionaries.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_diagram_spec.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/diagram_spec.py tests/test_diagram_spec.py
git commit -m "feat: define semantic diagram specification"
```

### Task 2: Build Hierarchy-Aware View Context

**Files:**
- Create: `src/architecture_model/core/view_context.py`
- Modify: `src/architecture_model/core/hierarchy.py`
- Create: `tests/test_view_context.py`

**Step 1: Write the failing tests**

Build root/submodel fixtures and test qualified identity, ownership, containment ancestry, deterministic cross-model relationship queries, unique unqualified resolution, and diagnostics for missing or ambiguous references.

```python
def test_context_preserves_duplicate_ids_across_submodels(hierarchy_fixture):
    context = ArchitectureViewContext.build(*hierarchy_fixture)
    assert context.resolve("payments::COMP-1").owner == "payments"
    assert context.resolve("COMP-1") is None
    assert context.diagnostics[0].code == "ambiguous-entity"
```

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_view_context.py -v`

Expected: FAIL because `ArchitectureViewContext` is missing.

**Step 3: Implement the minimal context**

Reuse `load_model_hierarchy()` for safe loading and add only the hierarchy metadata needed to retain source model identity. Index qualified records and relationships without flattening or rewriting model IDs; expose `resolve`, `children`, `ancestors`, `relationships`, and `provenance_for` queries.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_view_context.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/view_context.py src/architecture_model/core/hierarchy.py tests/test_view_context.py
git commit -m "feat: add hierarchy-aware architecture view context"
```

### Task 3: Load Presentation-Only Curation

**Files:**
- Create: `src/architecture_model/core/viewer_curation.py`
- Create: `tests/test_viewer_curation.py`
- Create: `tests/fixtures/viewer-curation/valid.yaml`
- Create: `tests/fixtures/viewer-curation/invalid.yaml`

**Step 1: Write the failing tests**

Test absent-file defaults, supported aliases/groups/order/include/exclude/preferred-root/drilldown keys, qualified selector resolution, unknown-key diagnostics, malformed YAML fallback, path containment, and rejection of entity/relationship/raw markup fields.

```python
def test_curation_cannot_create_architecture_facts(tmp_path):
    path = tmp_path / ".architecture" / "viewer-curation.yaml"
    write_yaml(path, {"entities": [{"id": "FAKE"}]})
    result = load_viewer_curation(tmp_path)
    assert result.profile.is_empty
    assert result.diagnostics[0].code == "unsupported-curation-key"
```

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_viewer_curation.py -v`

Expected: FAIL because the curation loader does not exist.

**Step 3: Implement the minimal loader**

Parse `.architecture/viewer-curation.yaml` with `yaml.safe_load`, normalize supported presentation fields into typed records, and return diagnostics plus an empty profile on invalid input. Keep all semantic existence checks in `ArchitectureViewContext`.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_viewer_curation.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/viewer_curation.py tests/test_viewer_curation.py tests/fixtures/viewer-curation
git commit -m "feat: load presentation-only viewer curation"
```

### Task 4: Infer External Evidence

**Files:**
- Create: `src/architecture_model/core/view_evidence.py`
- Create: `tests/test_view_evidence.py`

**Step 1: Write the failing tests**

Cover explicit `ExternalSystem` precedence; interface provider/consumer, behavior actor/trigger/step, and manifest boundary evidence; deterministic inferred IDs; confidence/provenance; deduplication; omission of weak or ambiguous strings; and the rule that curation can promote but cannot originate evidence.

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_view_evidence.py -v`

Expected: FAIL because evidence inference is missing.

**Step 3: Implement the minimal inference rules**

Return evidence records rather than mutating models or specs. Give explicit model evidence highest precedence, normalize stable names, merge equivalent evidence, and emit diagnostics for rejected candidates.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_view_evidence.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/view_evidence.py tests/test_view_evidence.py
git commit -m "feat: infer provenance-backed external evidence"
```

### Task 5: Project The ConOps View

**Files:**
- Create: `src/architecture_model/core/view_projectors/__init__.py`
- Create: `src/architecture_model/core/view_projectors/conops.py`
- Create: `tests/test_conops_projector.py`

**Step 1: Write the failing tests**

Test a bounded overview of actors, external systems, system boundary, and operational capability groups; interaction edges; configured ordering/aliases; inferred evidence labels; actor/capability drilldowns; provenance; omitted-detail counts; and sparse-model diagnostics.

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_conops_projector.py -v`

Expected: FAIL because `project_conops` is missing.

**Step 3: Implement the minimal projector**

Implement `project_conops(context) -> DiagramBundle`, where the bundle contains one overview and keyed drilldown specs. Use only context queries and evidence records; do not emit renderer syntax.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_conops_projector.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/view_projectors tests/test_conops_projector.py
git commit -m "feat: project curated ConOps views"
```

### Task 6: Project The Functional Architecture View

**Files:**
- Create: `src/architecture_model/core/view_projectors/functional_architecture.py`
- Create: `tests/test_functional_architecture_projector.py`

**Step 1: Write the failing tests**

Test capability-root selection, one-level bounded overview, containment and functional-flow edges, preferred roots, capability drilldowns, realizing systems/components, actor/requirement context, hierarchy qualification, omitted counts, and missing-parent diagnostics.

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_functional_architecture_projector.py -v`

Expected: FAIL because the functional projector is missing.

**Step 3: Implement the minimal projector**

Project capability semantics only. Keep dependency and module edges out of the overview; add realization and requirement context only in drilldowns.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_functional_architecture_projector.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/view_projectors/functional_architecture.py tests/test_functional_architecture_projector.py
git commit -m "feat: project curated functional architecture views"
```

### Task 7: Project The Logical Architecture View

**Files:**
- Create: `src/architecture_model/core/view_projectors/logical_architecture.py`
- Create: `tests/test_logical_architecture_projector.py`

**Step 1: Write the failing tests**

Test systems grouped by layer/curated domain, important inter-system dependencies, external evidence, deterministic handling of unassigned components, system drilldowns with owned components/interfaces/constraints, qualified subsystem IDs, and bounded overviews.

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_logical_architecture_projector.py -v`

Expected: FAIL because the logical projector is missing.

**Step 3: Implement the minimal projector**

Select logical systems first, derive only evidence-backed overview edges, and move component/interface details into per-system drilldowns. Represent unassigned components in an explicit deterministic group.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_logical_architecture_projector.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/view_projectors/logical_architecture.py tests/test_logical_architecture_projector.py
git commit -m "feat: project curated logical architecture views"
```

### Task 8: Project The Use Case View

**Files:**
- Create: `src/architecture_model/core/view_projectors/use_cases.py`
- Create: `tests/test_use_case_projector.py`

**Step 1: Write the failing tests**

Test top-level behavior selection, actor/theme grouping, cross-use-case trigger edges, drilldowns with trigger/participants/ordered steps/outcomes/interfaces/requirements, structured-step sequence semantics, incomplete-step diagnostics, aliases, and omitted-detail counts.

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_use_case_projector.py -v`

Expected: FAIL because the use-case projector is missing.

**Step 3: Implement the minimal projector**

Project behavior and trigger semantics; derive participants from explicit relationships and structured steps. Keep sequence detail in drilldowns and mark incomplete evidence instead of synthesizing missing steps.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_use_case_projector.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/view_projectors/use_cases.py tests/test_use_case_projector.py
git commit -m "feat: project curated use case views"
```

### Task 9: Render Deterministic Native SVG

**Files:**
- Create: `src/architecture_model/core/svg_renderer.py`
- Create: `tests/test_svg_renderer.py`

**Step 1: Write the failing tests**

Parse rendered output with `xml.etree.ElementTree` and assert valid SVG, deterministic bytes, semantic CSS classes, stable `data-entity-id`/`data-view-id`, focus and ARIA attributes, escaped hostile labels, wrapped long labels, typed edge markers, groups, empty states, diagnostics, and no remote assets/scripts.

```python
def test_svg_is_offline_and_escapes_labels(hostile_spec):
    svg = render_diagram_svg(hostile_spec)
    ET.fromstring(svg)
    assert "<script" not in svg
    assert "https://" not in svg
```

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_svg_renderer.py -v`

Expected: FAIL because the renderer is missing.

**Step 3: Implement the minimal renderer**

Use deterministic layered layout helpers and Python string/XML escaping. Render inline SVG directly from semantic roles; do not invoke Mermaid, a browser, Graphviz, or network resources.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_svg_renderer.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/svg_renderer.py tests/test_svg_renderer.py
git commit -m "feat: render semantic diagrams as offline SVG"
```

### Task 10: Integrate Curated Views Into The HTML Viewer

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `tests/test_viewer_pipeline_diagrams.py`
- Modify: `tests/test_html_viewer.py`
- Modify: `tests/test_viewer_v3.py`

**Step 1: Write the failing tests**

Assert that `generate_html_viewer(..., repo_path=...)` embeds all four overview/drilldown bundles and native SVG, loads optional curation, exposes diagnostics/provenance, and contains no Mermaid dependency for curated views. Add interaction-contract assertions for click and keyboard selection, drilldown navigation, selected-entity synchronization, and browser history.

**Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_viewer_pipeline_diagrams.py tests/test_html_viewer.py tests/test_viewer_v3.py -v`

Expected: FAIL because the viewer does not embed semantic bundles or native curated SVG.

**Step 3: Implement the minimal integration**

Build one `ArchitectureViewContext` in `generate_html_viewer`, project and render the four views, embed JSON-safe provenance/diagnostics, and add event delegation for semantic SVG hit targets. Preserve existing entity explorer and legacy diagram APIs during this task; switch only the four curated SE tabs.

**Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_viewer_pipeline_diagrams.py tests/test_html_viewer.py tests/test_viewer_v3.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/test_viewer_pipeline_diagrams.py tests/test_html_viewer.py tests/test_viewer_v3.py
git commit -m "feat: integrate curated SE views into viewer"
```

### Task 11: Share Projections With SE Documents

**Files:**
- Modify: `src/architecture_model/docs/se/conops.py`
- Modify: `src/architecture_model/docs/se/functional_analysis.py`
- Modify: `src/architecture_model/docs/se/logical_architecture.py`
- Modify: `src/architecture_model/docs/se/use_cases.py`
- Modify: `src/architecture_model/docs/se/generator.py`
- Modify: `tests/test_se_docs.py`
- Modify: `tests/test_se_diagrams.py`

**Step 1: Write the failing tests**

Assert that each generator consumes its corresponding `DiagramBundle`, emits the curated overview SVG or stable artifact link, identifies drilldowns, and surfaces projection diagnostics. Verify that model-only calls retain deterministic defaults and do not duplicate projection logic.

**Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_se_docs.py tests/test_se_diagrams.py -v`

Expected: FAIL because SE generators still call legacy Mermaid-specific paths.

**Step 3: Implement the minimal integration**

Create the context once in `generate_se_docs` and pass the appropriate bundle into each generator. Keep prose generation unchanged; replace only diagram assembly and related provenance/diagnostic sections.

**Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_se_docs.py tests/test_se_diagrams.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/architecture_model/docs/se/conops.py src/architecture_model/docs/se/functional_analysis.py src/architecture_model/docs/se/logical_architecture.py src/architecture_model/docs/se/use_cases.py src/architecture_model/docs/se/generator.py tests/test_se_docs.py tests/test_se_diagrams.py
git commit -m "feat: share curated projections with SE documents"
```

### Task 12: Add And Exercise The Logs-DB Profile

**Files:**
- Create in logs-db consumer repository: `.architecture/viewer-curation.yaml`
- Create: `tests/fixtures/viewer-curation/logs-db.yaml`
- Create: `tests/test_logs_db_viewer_curation.py`

**Step 1: Write the failing regression test**

Copy the intended logs-db profile into the local fixture and assert its selectors resolve against a compact logs-db-like hierarchy, its aliases/order/groups affect all four overviews, and every promoted external element has model or manifest evidence.

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_logs_db_viewer_curation.py -v`

Expected: FAIL until the profile and fixture are present and valid.

**Step 3: Add the minimal profile**

Define only logs-db aliases, preferred roots, overview groups/order, evidenced external promotions, and drilldown choices. Do not duplicate entities or relationships from `.architecture-model.yaml`.

**Step 4: Run the test and generate the consumer viewer**

Run: `pytest tests/test_logs_db_viewer_curation.py -v`

Expected: PASS.

Run from the logs-db repository using its established viewer-generation command; open the resulting HTML with networking disabled and inspect all four overview/drilldown paths.

Expected: The profile is applied, every promoted external node exposes evidence, and no curated view requires a network resource.

**Step 5: Commit each repository separately**

```bash
# architecture-model-standard
git add tests/fixtures/viewer-curation/logs-db.yaml tests/test_logs_db_viewer_curation.py
git commit -m "test: cover logs-db viewer curation profile"

# logs-db
git add .architecture/viewer-curation.yaml
git commit -m "docs: curate systems engineering viewer"
```

### Task 13: Verify The Complete Change

**Files:**
- Modify if public behavior changed: `docs/reference.md`

**Step 1: Run focused semantic and viewer tests**

Run: `pytest tests/test_diagram_spec.py tests/test_view_context.py tests/test_viewer_curation.py tests/test_view_evidence.py tests/test_conops_projector.py tests/test_functional_architecture_projector.py tests/test_logical_architecture_projector.py tests/test_use_case_projector.py tests/test_svg_renderer.py tests/test_viewer_pipeline_diagrams.py tests/test_html_viewer.py tests/test_viewer_v3.py tests/test_se_docs.py tests/test_se_diagrams.py tests/test_logs_db_viewer_curation.py -v`

Expected: PASS.

**Step 2: Run existing visualization regressions**

Run: `pytest tests/test_visualize.py tests/test_visualize_shapes.py tests/test_visualize_new_diagrams.py tests/test_visualize_detail.py tests/test_viewer_subsystem_modules.py -v`

Expected: PASS.

**Step 3: Run the repository suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`

Expected: PASS, excluding the documented pre-existing ignored test file.

**Step 4: Run architecture checks**

Run the `architect_check` and `architect_gate` tools against the repository root.

Expected: changed files are represented by the architecture model and the gate reports `phase_requirements_met=true`.

**Step 5: Inspect generated artifacts offline**

Generate viewers for a sparse fixture, a hierarchical fixture with duplicate IDs, and logs-db. Parse every embedded SVG as XML, search generated HTML for remote URLs and Mermaid runtime use in curated tabs, and manually exercise pointer/keyboard drilldown, back/forward, provenance, and malformed-curation diagnostics.

Expected: all viewers remain navigable offline, deterministic on regeneration, and explicit about inference or errors.

**Step 6: Update public documentation only if needed**

If curation is a supported public interface, add its schema, non-semantic guarantees, and a minimal example to `docs/reference.md`; otherwise leave documentation unchanged.

**Step 7: Commit verification documentation**

```bash
git add docs/reference.md
git commit -m "docs: document viewer curation profile"
```

Skip this commit when `docs/reference.md` did not require a change.
