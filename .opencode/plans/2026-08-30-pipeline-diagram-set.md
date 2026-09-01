# Pipeline Diagram Set — Complete Extraction Pipeline Visualization

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce a complete, hierarchical, click-navigable Mermaid diagram set for the extraction pipeline — from high-level context down to per-stage behavior detail.

**Architecture:** Add ~76 pipeline behaviors to the model YAML, build 2 new per-entity diagram generators (`component_detail`, `use_case`), wire click navigation between diagram levels, and generate the full output to `.architecture/diagrams/pipeline/`.

**Tech Stack:** Python, Mermaid flowcharts, YAML, pytest

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp`
**Branch:** `feature/model-quality-16wp`
**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
**Baseline:** 7 failed, 1636 passed, 98 skipped

---

## Task 1: Add Pipeline Behaviors to Model YAML

**Files:**
- Modify: `.architecture-model.yaml` (append to `entities.behaviors` after BEH-25 at ~line 1089, append relationships at end of file)
- Create: `tests/test_pipeline_behaviors.py`

**Step 1: Write the failing test**

```python
# tests/test_pipeline_behaviors.py
"""Tests for pipeline behavior hierarchy in the architecture model."""
import pytest
from pathlib import Path
from architecture_model.core.parser import load_model

MODEL_PATH = Path(__file__).parent.parent / ".architecture-model.yaml"

@pytest.fixture
def model():
    return load_model(MODEL_PATH)

class TestPipelineBehaviorHierarchy:
    def test_top_level_pipeline_behavior_exists(self, model):
        beh_ids = {b.id for b in model.entities.behaviors}
        assert "BEH-P1" in beh_ids

    def test_all_10_stage_behaviors_exist(self, model):
        beh_ids = {b.id for b in model.entities.behaviors}
        for i in range(1, 11):
            assert f"BEH-P1.{i}" in beh_ids, f"Missing BEH-P1.{i}"

    def test_llm_refinement_behavior_exists(self, model):
        beh_ids = {b.id for b in model.entities.behaviors}
        assert "BEH-P1.R" in beh_ids

    def test_observe_sub_behaviors(self, model):
        beh_ids = {b.id for b in model.entities.behaviors}
        for i in range(1, 12):
            assert f"BEH-P1.1.{i}" in beh_ids, f"Missing BEH-P1.1.{i}"

    def test_contains_relationships_wire_hierarchy(self, model):
        contains = [(r.from_id, r.to_id) for r in model.relationships
                    if getattr(r.type, 'value', r.type) == 'contains']
        assert ("BEH-P1", "BEH-P1.1") in contains
        assert ("BEH-P1", "BEH-P1.10") in contains

    def test_traces_to_relationships(self, model):
        traces = [(r.from_id, r.to_id) for r in model.relationships
                  if getattr(r.type, 'value', r.type) == 'traces-to']
        assert ("COMP-2.2", "BEH-P1.1") in traces

    def test_pipeline_behavior_count(self, model):
        pipeline_behs = [b for b in model.entities.behaviors if b.id.startswith("BEH-P1")]
        assert len(pipeline_behs) >= 70
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_behaviors.py -v`
Expected: FAIL — BEH-P1 not found

**Step 3: Add behaviors and relationships to `.architecture-model.yaml`**

Append to `entities.behaviors` (after BEH-25). All use `status: ACTIVE`.

**Top-level behavior:**
```yaml
  - id: BEH-P1
    name: Run Extraction Pipeline
    status: ACTIVE
    description: Execute the 10-stage extraction pipeline to produce an architecture model from source code
    pattern: sequential
    steps: [observe, infer, allocate, relate, specify, contract, validate, decompose, synthesize, emit]
```

**11 stage behaviors:** BEH-P1.1 (Observe) through BEH-P1.10 (Emit) + BEH-P1.R (LLM Refinement)

Each with descriptive name, status: ACTIVE, and steps listing their sub-operations.

**~65 sub-behaviors:** BEH-P1.1.1 through BEH-P1.10.7, BEH-P1.R.1 through BEH-P1.R.4

Complete hierarchy:
- BEH-P1.1 Observe: 11 sub-behaviors (Filter Files, Scan Module, Extract Functions/Classes/Constants/Imports, Resolve Import Edges, Detect Routes/Constraints, Find Tests/Docs)
- BEH-P1.2 Infer: 10 sub-behaviors (Routes, Triggers, Domain Modules, CLI, Infrastructure, Package Grouping, Default Actors, Behaviors, Library Behaviors, Fallback)
- BEH-P1.3 Allocate: 9 sub-behaviors (Detect Project Type, Seed from Capabilities, Import Affinity, Per-File, Split Oversized, Merge Undersized, Infer Layer, Boundary Coherence, Package Grouping)
- BEH-P1.4 Relate: 6 sub-behaviors (Realizes, Depends-On, Contains, Exposes, Constrained-By, Build File Map)
- BEH-P1.5 Specify: 5 sub-behaviors (REST, CLI, Library API, Name Library Interface, Fallback)
- BEH-P1.6 Contract: 2 sub-behaviors (Match Target, Match by Directory)
- BEH-P1.7 Validate: 5 sub-behaviors (Capability Realization, Orphans, File Coverage, Boundary Coherence, Confidence)
- BEH-P1.8 Decompose: 4 sub-behaviors (Identify Autonomous, Decompose Large, Cluster by Dir, Merge Coupled)
- BEH-P1.9 Synthesize: 6 sub-behaviors (Decide Stages, Scoped Sub-Pipeline, Build Model YAML, Build Manifest, Build SoS, Collect Lessons)
- BEH-P1.10 Emit: 7 sub-behaviors (Write Files, Build Test Map, Generate SE Docs, Enrich Model, System Interactions, LLM Reviews, Inline Reviews)
- BEH-P1.R LLM Refinement: 4 sub-behaviors (Build Prompt, Normalize Output, Diff Outputs, Apply Corrections)

**Relationships to append (~90 total):**
- 11 `contains` from BEH-P1 → stage behaviors
- 9 `triggers` for sequential stage flow (BEH-P1.1→BEH-P1.2→...→BEH-P1.10)
- 4 `triggers` for LLM refinement (BEH-P1.2/3/4/5 → BEH-P1.R)
- ~65 `contains` from stage → sub-behaviors
- 12 `traces-to` from COMP-2.x → stage behaviors

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_behaviors.py -v`

**Step 5: Run full suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`

**Step 6: Commit**

```bash
git add .architecture-model.yaml tests/test_pipeline_behaviors.py
git commit -m "feat(model): add 76 pipeline behavior entities with 3-level hierarchy"
```

---

## Task 2: Build `generate_component_detail_diagram`

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (add function before `generate_all_diagrams` at line 590)
- Modify: `src/architecture_model/cli/visualize.py` (add to re-exports)
- Create: `tests/test_visualize_detail.py`

**Step 1: Write the failing test**

```python
# tests/test_visualize_detail.py
"""Tests for per-entity detail diagram generators."""
import pytest
from architecture_model.core.types import (
    ArchitectureModel, Meta, Entities, Component, Capability,
    Interface, Behavior, Relationship, Layer, Status, RelationType,
    InterfaceType,
)
from architecture_model.core.visualize import (
    generate_component_detail_diagram,
    generate_use_case_diagram,
)

def _make_model():
    return ArchitectureModel(
        meta=Meta(project="test", schema_version="2.0"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Parser", status=Status.ACTIVE,
                          source_files=["parser.py", "ast_utils.py"]),
                Component(id="COMP-2", name="Validator", status=Status.ACTIVE),
            ],
            capabilities=[Capability(id="CAP-F1", name="Parsing", status=Status.ACTIVE)],
            interfaces=[Interface(id="IF-1", name="Parse API", status=Status.ACTIVE, type=InterfaceType.INTERNAL)],
            behaviors=[
                Behavior(id="BEH-1", name="Parse File", status=Status.ACTIVE),
                Behavior(id="BEH-1.1", name="Tokenize", status=Status.ACTIVE),
                Behavior(id="BEH-1.2", name="Build AST", status=Status.ACTIVE),
            ],
            layers=[Layer(id="LAY-1", name="Core", status=Status.ACTIVE)],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-F1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="IF-1", type=RelationType.EXPOSES),
            Relationship(from_id="COMP-1", to_id="BEH-1", type=RelationType.TRACES_TO),
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON),
            Relationship(from_id="LAY-1", to_id="COMP-1", type=RelationType.CONTAINS),
            Relationship(from_id="BEH-1", to_id="BEH-1.1", type=RelationType.CONTAINS),
            Relationship(from_id="BEH-1", to_id="BEH-1.2", type=RelationType.CONTAINS),
        ],
    )

class TestComponentDetailDiagram:
    def test_returns_flowchart(self):
        assert generate_component_detail_diagram(_make_model(), "COMP-1").startswith("flowchart TB")

    def test_shows_component_node(self):
        assert "Parser" in generate_component_detail_diagram(_make_model(), "COMP-1")

    def test_shows_realized_capabilities(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "CAP_F1" in mmd and "Parsing" in mmd

    def test_shows_exposed_interfaces(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "IF_1" in mmd and "Parse API" in mmd

    def test_shows_traced_behaviors(self):
        assert "BEH_1" in generate_component_detail_diagram(_make_model(), "COMP-1")

    def test_shows_dependencies(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "COMP_2" in mmd and "Validator" in mmd

    def test_shows_source_files(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "parser.py" in mmd and "ast_utils.py" in mmd

    def test_shows_containing_layer(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-1")
        assert "LAY_1" in mmd or "Core" in mmd

    def test_unknown_component(self):
        mmd = generate_component_detail_diagram(_make_model(), "COMP-999")
        assert "not found" in mmd.lower()

    def test_has_click_directives(self):
        assert "click" in generate_component_detail_diagram(_make_model(), "COMP-1")
```

**Step 2: Run to verify failure** — ImportError

**Step 3: Implement `generate_component_detail_diagram`**

Signature: `generate_component_detail_diagram(model: "ArchitectureModel", component_id: str) -> str`

Shows: central component, containing layer, realized capabilities (subgraph), exposed interfaces (subgraph), traced behaviors (subgraph + click to use-case), dependencies, source files as module nodes.

Returns "not found" flowchart for unknown component_id.

Click directives on behavior nodes: `click {sid} "use-case-{id}.mmd" "View use case detail"`

**Step 4: Update CLI re-exports** — add to import and `__all__` in `cli/visualize.py`

**Step 5: Run tests**

**Step 6: Commit**

```bash
git commit -m "feat(viz): add generate_component_detail_diagram with click navigation"
```

---

## Task 3: Build `generate_use_case_diagram`

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `src/architecture_model/cli/visualize.py`
- Modify: `tests/test_visualize_detail.py`

**Step 1: Write failing tests**

```python
class TestUseCaseDiagram:
    def test_returns_flowchart(self):
        assert generate_use_case_diagram(_make_model(), "BEH-1").startswith("flowchart TB")

    def test_shows_behavior_node(self):
        assert "Parse File" in generate_use_case_diagram(_make_model(), "BEH-1")

    def test_shows_sub_behaviors(self):
        mmd = generate_use_case_diagram(_make_model(), "BEH-1")
        assert "Tokenize" in mmd and "Build AST" in mmd

    def test_shows_implementing_component(self):
        assert "Parser" in generate_use_case_diagram(_make_model(), "BEH-1")

    def test_unknown_behavior(self):
        assert "not found" in generate_use_case_diagram(_make_model(), "BEH-999").lower()

    def test_click_on_sub_behaviors(self):
        assert "click" in generate_use_case_diagram(_make_model(), "BEH-1")
```

**Step 2-6:** Implement, update re-exports, test, commit.

Signature: `generate_use_case_diagram(model: "ArchitectureModel", behavior_id: str) -> str`

Shows: central behavior, implementing components (traces-to reverse), sub-behaviors (contains), triggered-by/triggers edges. Click on sub-behaviors and components.

```bash
git commit -m "feat(viz): add generate_use_case_diagram with click navigation"
```

---

## Task 4: Wire Click Navigation into Existing Diagrams

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (update `generate_behaviors_diagram`, `generate_components_diagram`)
- Modify: `tests/test_visualize_detail.py`

Add click directives after each behavior/component node:
- `generate_behaviors_diagram`: `click {sid} "use-case-{id}.mmd" "View use case detail"`
- `generate_components_diagram`: `click {sid} "component-{id}.mmd" "View component detail"`

```bash
git commit -m "feat(viz): add click navigation to behaviors and components diagrams"
```

---

## Task 5: Update `generate_all_diagrams` for Per-Entity Output

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (update `generate_all_diagrams`)
- Update: existing diagram count assertions in tests

After the 10 standard diagrams, add:
```python
for comp in model.entities.components:
    # generate_component_detail_diagram → "component-{id}.mmd"
for beh in model.entities.behaviors:
    # generate_use_case_diagram → "use-case-{id}.mmd"
```

Fix existing test assertions that check `len(paths) == 10`.

```bash
git commit -m "feat(viz): generate per-entity detail diagrams in generate_all_diagrams"
```

---

## Task 6: Generate and Output the Complete Pipeline Diagram Set

No code changes. Run generation:

```bash
/opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_all_diagrams
model = load_model(Path('.architecture-model.yaml'))
paths = generate_all_diagrams(model, Path('.architecture/diagrams/pipeline'))
print(f'Generated {len(paths)} diagrams')
"
```

Spot-check: `behaviors.mmd`, `use-case-BEH-P1.mmd`, `use-case-BEH-P1.1.mmd`, `component-COMP-2.1.mmd`.

```bash
git add .architecture/diagrams/ && git commit -m "docs: generate complete pipeline diagram set"
```

---

## Task 7: Run Full Suite, Push

```bash
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py
git -c http.proxy="" push https://opn-arch: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@github.com/opn-arch/architecture-model-standard.git feature/model-quality-16wp
```

---

## Summary

| Task | What | Output |
|------|------|--------|
| 1 | 76 pipeline behaviors + 90 relationships in model YAML | Model enrichment |
| 2 | `generate_component_detail_diagram` | Per-component exploded view |
| 3 | `generate_use_case_diagram` | Per-behavior exploded view |
| 4 | Click navigation in existing diagrams | Wires diagram levels together |
| 5 | `generate_all_diagrams` update | Includes per-entity diagrams |
| 6 | Generate full diagram set | 120+ .mmd files |
| 7 | Push | PR update |
