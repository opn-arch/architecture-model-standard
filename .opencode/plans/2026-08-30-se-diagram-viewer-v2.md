# SE Diagram Viewer v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build SE-quality interactive Mermaid diagram viewer with hierarchical capabilities, formal layers, and entity exploration — a single self-contained HTML file viewable on a phone.

**Architecture:** Enrich the `.architecture-model.yaml` with ~80 L3 sub-capabilities and 5 formal layer entities. Add 4 new SE-quality diagram generators (ConOps, Functional Architecture, Logical Architecture, Behavior Overview). Add entity explorer generator. Rebuild HTML viewer with structured navigation and accordion-style entity exploration.

**Tech Stack:** Python, Mermaid.js (CDN), vanilla HTML/CSS/JS (single file), YAML model editing

---

## Task 1: Add Capability Hierarchy to Model

**Files:**
- Modify: `.architecture-model.yaml` (entities.capabilities + relationships sections)
- Create: `tests/test_capability_hierarchy.py`

### Curated L3 Capability Tree (~78 new capabilities)

The hierarchy: CAP-0 (root) → CAP-0.1..0.4 (L1 groups) → CAP-1..15 (existing L1) → CAP-X.Y (new L2 sub-caps).

**New parent capabilities to add (5):**
```yaml
- id: CAP-0
  name: Provide Architecture-as-Code Standard
  status: ACTIVE
  description: Root capability encompassing all system functions
- id: CAP-0.1
  name: Understand Software Architecture
  status: ACTIVE
  description: Analyze and represent software architecture from source code
- id: CAP-0.2
  name: Validate Architectural Claims
  status: ACTIVE
  description: Verify architectural claims against code reality
- id: CAP-0.3
  name: Generate Architecture Artifacts
  status: ACTIVE
  description: Produce documentation, models, and exports from architectural knowledge
- id: CAP-0.4
  name: Evolve Architecture Over Time
  status: ACTIVE
  description: Track changes, decompose systems, and maintain model quality
```

**New L2 sub-capabilities by parent (curated from 187 → 78):**

**CAP-1: Validate Architecture Models (8 sub-caps)**
```yaml
- id: CAP-1.1
  name: Validate JSON Schema Compliance
- id: CAP-1.2
  name: Enforce Entity ID Uniqueness
- id: CAP-1.3
  name: Check Referential Integrity
- id: CAP-1.4
  name: Detect Orphan Entities
- id: CAP-1.5
  name: Verify Capability Realization
- id: CAP-1.6
  name: Check Hierarchy Consistency
- id: CAP-1.7
  name: Detect Dependency Cycles
- id: CAP-1.8
  name: Validate Domain Profile Rules
```

**CAP-2: Extract Architecture from Code (6 sub-caps)**
```yaml
- id: CAP-2.1
  name: Derive Capabilities from Config
- id: CAP-2.2
  name: Infer Actors from Routes
- id: CAP-2.3
  name: Derive Components from Manifest
- id: CAP-2.4
  name: Derive Cross-Block Interfaces
- id: CAP-2.5
  name: Detect Code Constraints
- id: CAP-2.6
  name: Derive Entity Relationships
```

**CAP-3: Run Modular Extraction Pipeline (10 sub-caps — one per stage)**
```yaml
- id: CAP-3.1
  name: AST-Scan Source Files
- id: CAP-3.2
  name: Infer Capabilities from Code
- id: CAP-3.3
  name: Allocate Files to Components
- id: CAP-3.4
  name: Derive Entity Relationships
- id: CAP-3.5
  name: Derive Interface Specifications
- id: CAP-3.6
  name: Extract Test Contracts
- id: CAP-3.7
  name: Validate Pipeline Output
- id: CAP-3.8
  name: Detect System Boundaries
- id: CAP-3.9
  name: Run Scoped Sub-Pipelines
- id: CAP-3.10
  name: Emit Final Artifacts
```

**CAP-4: Generate Reality Manifest (6 sub-caps)**
```yaml
- id: CAP-4.1
  name: Scan Python AST
- id: CAP-4.2
  name: Extract Function Body Hints
- id: CAP-4.3
  name: Build Call Graph
- id: CAP-4.4
  name: Analyze Test Files
- id: CAP-4.5
  name: Group Modules into Components
- id: CAP-4.6
  name: Scan Multi-Language Sources
```

**CAP-5: Generate SE Documentation (8 sub-caps)**
```yaml
- id: CAP-5.1
  name: Generate ConOps Document
- id: CAP-5.2
  name: Generate Functional Analysis
- id: CAP-5.3
  name: Generate Logical Architecture Doc
- id: CAP-5.4
  name: Generate Use Case Document
- id: CAP-5.5
  name: Generate Component Specifications
- id: CAP-5.6
  name: Generate Interface Specification
- id: CAP-5.7
  name: Generate Mermaid Diagrams
- id: CAP-5.8
  name: Generate Health Report
```

**CAP-6: Author Model from Requirements (3 sub-caps)**
```yaml
- id: CAP-6.1
  name: Parse Requirements Markdown
- id: CAP-6.2
  name: Parse Actor Definitions
- id: CAP-6.3
  name: Parse Capability Hierarchy
```

**CAP-7: Slice and Query Models (4 sub-caps)**
```yaml
- id: CAP-7.1
  name: Slice by Source Block
- id: CAP-7.2
  name: Slice by Architecture Layer
- id: CAP-7.3
  name: Slice for Artifact Regeneration
- id: CAP-7.4
  name: Slice for SE Document Views
```

**CAP-8: Diff Model Versions (3 sub-caps)**
```yaml
- id: CAP-8.1
  name: Diff Entity Lists by ID
- id: CAP-8.2
  name: Detect Field-Level Changes
- id: CAP-8.3
  name: Determine Affected Artifacts
```

**CAP-9: Decompose Models Hierarchically (5 sub-caps)**
```yaml
- id: CAP-9.1
  name: Compute Component Complexity
- id: CAP-9.2
  name: Identify System Candidates
- id: CAP-9.3
  name: Detect System Boundaries
- id: CAP-9.4
  name: Trace Connected Entities
- id: CAP-9.5
  name: Write Sub-Models to Disk
```

**CAP-10: Enrich Models with Code Intelligence (4 sub-caps)**
```yaml
- id: CAP-10.1
  name: Extract Function Signatures
- id: CAP-10.2
  name: Extract Module-Level Constants
- id: CAP-10.3
  name: Extract Test Contracts
- id: CAP-10.4
  name: Discover Test Files by Convention
```

**CAP-11: Assess Regen Readiness (3 sub-caps)**
```yaml
- id: CAP-11.1
  name: Compute System Readiness Score
- id: CAP-11.2
  name: Compute Component Readiness
- id: CAP-11.3
  name: Classify Body Hint Quality
```

**CAP-12: Check Development Gate (2 sub-caps)**
```yaml
- id: CAP-12.1
  name: Check Code-Intent Alignment
- id: CAP-12.2
  name: Evaluate Stage Quality Gates
```

**CAP-13: Detect and Fix Model Drift (3 sub-caps)**
```yaml
- id: CAP-13.1
  name: Generate Drift Report
- id: CAP-13.2
  name: Identify Stale Artifacts
- id: CAP-13.3
  name: Compare Model to Code Reality
```

**CAP-14: Manage Global Learnings (5 sub-caps)**
```yaml
- id: CAP-14.1
  name: Store Heuristic Rules
- id: CAP-14.2
  name: Match Archetype Patterns
- id: CAP-14.3
  name: Record User Corrections
- id: CAP-14.4
  name: Track Quality History
- id: CAP-14.5
  name: Generate Lessons from Diagnostics
```

**CAP-15: Export for AI Consumption (4 sub-caps)**
```yaml
- id: CAP-15.1
  name: Build Flat File Export
- id: CAP-15.2
  name: Generate Schema Reference
- id: CAP-15.3
  name: Generate Custom Instructions
- id: CAP-15.4
  name: Concatenate Sub-Model Artifacts
```

**Total new capabilities: 5 parents + 74 sub-caps = 79 new entries**

### Relationships to add

**Hierarchy (contains) relationships:**
- CAP-0 contains CAP-0.1, CAP-0.2, CAP-0.3, CAP-0.4
- CAP-0.1 contains CAP-2, CAP-3, CAP-4, CAP-7
- CAP-0.2 contains CAP-1, CAP-11, CAP-12
- CAP-0.3 contains CAP-5, CAP-6, CAP-10, CAP-15
- CAP-0.4 contains CAP-8, CAP-9, CAP-13, CAP-14
- CAP-1 contains CAP-1.1..CAP-1.8
- CAP-2 contains CAP-2.1..CAP-2.6
- ... (each parent contains its sub-caps)

**Realizes relationships (component → sub-capability):**
Map sub-capabilities to their implementing sub-components. E.g.:
- COMP-1.1 (Parser) realizes CAP-7.1 (Slice by Source Block) — if parser is involved
- Research which sub-components implement which sub-caps from the source file mapping above

### Step 1: Write failing test

```python
# tests/test_capability_hierarchy.py
"""Tests for capability hierarchy in the architecture model."""
import yaml
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / ".architecture-model.yaml"

def _load_model():
    with open(MODEL_PATH) as f:
        return yaml.safe_load(f)

def test_root_capability_exists():
    model = _load_model()
    caps = {c["id"]: c for c in model["entities"]["capabilities"]}
    assert "CAP-0" in caps
    assert caps["CAP-0"]["name"] == "Provide Architecture-as-Code Standard"

def test_l1_group_capabilities_exist():
    model = _load_model()
    caps = {c["id"] for c in model["entities"]["capabilities"]}
    for cap_id in ["CAP-0.1", "CAP-0.2", "CAP-0.3", "CAP-0.4"]:
        assert cap_id in caps, f"Missing L1 group capability {cap_id}"

def test_l2_sub_capabilities_count():
    """At least 70 L2 sub-capabilities should exist."""
    model = _load_model()
    caps = model["entities"]["capabilities"]
    l2_caps = [c for c in caps if "." in c["id"] and c["id"].count(".") == 1
               and not c["id"].startswith("CAP-0.")]
    assert len(l2_caps) >= 70, f"Only {len(l2_caps)} L2 sub-capabilities"

def test_hierarchy_contains_relationships():
    """Every sub-capability should have a contains relationship from its parent."""
    model = _load_model()
    contains_rels = {(r["from"], r["to"]) for r in model["relationships"]
                     if r["type"] == "contains"}
    caps = model["entities"]["capabilities"]
    for cap in caps:
        cid = cap["id"]
        if "." in cid:
            parent = cid.rsplit(".", 1)[0]
            assert (parent, cid) in contains_rels, f"Missing contains: {parent} → {cid}"

def test_all_existing_caps_have_parent():
    """CAP-1 through CAP-15 should be contained by a CAP-0.x parent."""
    model = _load_model()
    contains_rels = {r["to"] for r in model["relationships"]
                     if r["type"] == "contains" and r["from"].startswith("CAP-0.")}
    for i in range(1, 16):
        assert f"CAP-{i}" in contains_rels, f"CAP-{i} not contained by any L1 group"
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_capability_hierarchy.py -v`
Expected: FAIL (CAP-0 doesn't exist yet)

### Step 3: Add capabilities and relationships to `.architecture-model.yaml`

Add the 79 new capability entities to `entities.capabilities` list and the ~100 new `contains` relationships to the `relationships` list. Also add `realizes` relationships from sub-components to sub-capabilities where the mapping is clear.

### Step 4: Run test to verify it passes

Run: `pytest tests/test_capability_hierarchy.py -v`
Expected: PASS

### Step 5: Run full test suite

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: Same baseline (7 failed, ~1670 passed)

### Step 6: Commit

```bash
git add .architecture-model.yaml tests/test_capability_hierarchy.py
git commit -m "feat(model): add 3-level capability hierarchy with 79 new capabilities"
```

---

## Task 2: Add Formal Layer Entities

**Files:**
- Modify: `.architecture-model.yaml` (entities.layers + relationships)
- Create: `tests/test_layer_entities.py`

### Layer entities to add (5):
```yaml
layers:
  - id: LAY-1
    name: Foundation
    status: ACTIVE
    description: Core types, utilities, and shared infrastructure
  - id: LAY-2
    name: Domain
    status: ACTIVE
    description: Domain logic — manifest generation, extraction, pipeline stages
  - id: LAY-3
    name: Application
    status: ACTIVE
    description: Orchestration, enrichment, quality assessment
  - id: LAY-4
    name: Interface
    status: ACTIVE
    description: CLI commands and external-facing APIs
  - id: LAY-5
    name: Infrastructure
    status: ACTIVE
    description: Configuration, profiles, JSON schema, file discovery
```

### Component-to-layer mapping (from existing `layer` field on components):
- LAY-1 (foundation): COMP-CORE and its children
- LAY-2 (domain): COMP-MANIFEST, COMP-EXTRACT, pipeline components
- LAY-3 (application): COMP-ORCHESTRATION, quality components
- LAY-4 (interface): COMP-CLI and its children
- LAY-5 (infrastructure): COMP-CONFIG, COMP-PROFILES, COMP-SPEC, COMP-UTILS

### Relationships to add:
- `contains` from each LAY-X to its components
- `depends-on` between layers (LAY-4 → LAY-3 → LAY-2 → LAY-1, LAY-5 → LAY-1)

### Step 1: Write failing test

```python
# tests/test_layer_entities.py
"""Tests for formal layer entities in the architecture model."""
import yaml
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / ".architecture-model.yaml"

def _load_model():
    with open(MODEL_PATH) as f:
        return yaml.safe_load(f)

def test_five_layers_exist():
    model = _load_model()
    layers = model["entities"].get("layers", [])
    assert len(layers) == 5
    layer_ids = {l["id"] for l in layers}
    assert layer_ids == {"LAY-1", "LAY-2", "LAY-3", "LAY-4", "LAY-5"}

def test_layers_contain_components():
    model = _load_model()
    contains_rels = [(r["from"], r["to"]) for r in model["relationships"]
                     if r["type"] == "contains" and r["from"].startswith("LAY-")]
    assert len(contains_rels) >= 5, "Each layer should contain at least one component"

def test_layer_dependencies():
    model = _load_model()
    deps = {(r["from"], r["to"]) for r in model["relationships"]
            if r["type"] == "depends-on" and r["from"].startswith("LAY-")}
    assert ("LAY-4", "LAY-3") in deps, "Interface layer should depend on Application"
    assert ("LAY-3", "LAY-2") in deps, "Application layer should depend on Domain"
```

### Step 2-6: Same TDD cycle as Task 1

Run: `pytest tests/test_layer_entities.py -v`
Commit: `git commit -m "feat(model): add 5 formal layer entities with component allocation"`

---

## Task 3: Build 4 SE Overview Diagram Generators

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `src/architecture_model/cli/visualize.py` (re-exports)
- Create: `tests/test_se_diagrams.py`

### 3a: `generate_conops_diagram(model)`

Shows actors on the left, system boundary in the middle (subgraph), capabilities inside the boundary grouped by L1, and operational flows as edges.

```
graph LR
  subgraph Actors
    ACT_1([Developer])
    ACT_2([AI Agent])
    ACT_3([CI/CD Pipeline])
  end
  subgraph "Architecture-as-Code Standard"
    subgraph "Understand"
      CAP_2(Extract)
      CAP_3(Pipeline)
      CAP_4(Manifest)
      CAP_7(Slice & Query)
    end
    subgraph "Validate"
      CAP_1(Validate)
      CAP_11(Regen Readiness)
      CAP_12(Dev Gate)
    end
    subgraph "Generate"
      CAP_5(SE Docs)
      CAP_6(Author)
      CAP_10(Enrich)
      CAP_15(Export)
    end
    subgraph "Evolve"
      CAP_8(Diff)
      CAP_9(Decompose)
      CAP_13(Drift)
      CAP_14(Learnings)
    end
  end
  ACT_1 --> CAP_1
  ACT_2 --> CAP_3
  ACT_3 --> CAP_1
```

### 3b: `generate_functional_architecture_diagram(model)`

Shows the full capability hierarchy as a tree using `contains` relationships. L0 → L1 groups → L1 capabilities → L2 sub-capabilities. Use subgraphs for L1 groups.

### 3c: `generate_logical_architecture_diagram(model)`

Shows components grouped by layer (subgraphs), with `depends-on` edges between components. Layer subgraphs are stacked vertically (TB direction).

### 3d: `generate_behavior_overview_diagram(model)`

Shows top-level behaviors (no parent) with `triggers` edges. Pipeline stages as the main flow, CLI commands as entry points.

### Step 1: Write failing tests

```python
# tests/test_se_diagrams.py
"""Tests for SE-quality overview diagrams."""
import pytest
from unittest.mock import MagicMock
from architecture_model.core.visualize import (
    generate_conops_diagram,
    generate_functional_architecture_diagram,
    generate_logical_architecture_diagram,
    generate_behavior_overview_diagram,
)

@pytest.fixture
def model():
    """Load the real architecture model."""
    from architecture_model.core.parser import load_model
    from pathlib import Path
    return load_model(Path(__file__).parent.parent / ".architecture-model.yaml")

class TestConOpsDiagram:
    def test_returns_mermaid(self, model):
        result = generate_conops_diagram(model)
        assert result.startswith("graph") or result.startswith("flowchart")

    def test_contains_actors(self, model):
        result = generate_conops_diagram(model)
        assert "Developer" in result
        assert "AI Agent" in result

    def test_contains_capability_groups(self, model):
        result = generate_conops_diagram(model)
        assert "Understand" in result
        assert "Validate" in result

class TestFunctionalArchitectureDiagram:
    def test_returns_mermaid(self, model):
        result = generate_functional_architecture_diagram(model)
        assert result.startswith("graph") or result.startswith("flowchart")

    def test_contains_root_capability(self, model):
        result = generate_functional_architecture_diagram(model)
        assert "CAP_0" in result or "CAP-0" in result

    def test_contains_sub_capabilities(self, model):
        result = generate_functional_architecture_diagram(model)
        assert "CAP_1_1" in result or "CAP-1.1" in result

class TestLogicalArchitectureDiagram:
    def test_returns_mermaid(self, model):
        result = generate_logical_architecture_diagram(model)
        assert result.startswith("graph") or result.startswith("flowchart")

    def test_contains_layers(self, model):
        result = generate_logical_architecture_diagram(model)
        assert "Foundation" in result
        assert "Interface" in result

class TestBehaviorOverviewDiagram:
    def test_returns_mermaid(self, model):
        result = generate_behavior_overview_diagram(model)
        assert result.startswith("graph") or result.startswith("flowchart")
```

### Step 2: Run tests → FAIL (functions don't exist)
### Step 3: Implement the 4 generators in `visualize.py`
### Step 4: Add re-exports to `cli/visualize.py`
### Step 5: Run full suite
### Step 6: Commit

```bash
git commit -m "feat(viz): add 4 SE-quality overview diagram generators"
```

---

## Task 4: Build Entity Explorer Generator

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Create: `tests/test_entity_explorer.py`

### Function signature:
```python
def generate_entity_explorer(
    model: "ArchitectureModel",
    entity_type: str,  # "component", "capability", "behavior", "interface"
    entity_id: str,
) -> dict[str, str]:
    """Generate facet diagrams for an entity.

    Returns dict mapping facet name to Mermaid diagram content.
    """
```

### Facets by entity type:

**Component facets:**
- "Capabilities" — capabilities this component realizes
- "Interfaces" — interfaces this component exposes
- "Dependencies" — depends-on relationships
- "Behaviors" — behaviors traced to this component
- "Sub-Components" — children (if parent component)

**Capability facets:**
- "Functional Breakdown" — sub-capabilities (children)
- "Components" — components that realize this capability
- "Behaviors" — behaviors related to this capability
- "Interfaces" — interfaces supporting this capability

**Behavior facets:**
- "Sub-Behaviors" — child behaviors
- "Components" — components involved
- "Triggers" — trigger relationships
- "Sequence" — structured_steps as sequence diagram

**Interface facets:**
- "Provider" — component that exposes this interface
- "Consumers" — actors/components that consume this interface

### Step 1: Write failing tests
### Step 2: Run → FAIL
### Step 3: Implement
### Step 4: Run → PASS
### Step 5: Full suite
### Step 6: Commit

```bash
git commit -m "feat(viz): add entity explorer with faceted diagrams"
```

---

## Task 5: Rebuild HTML Viewer v2

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (replace `generate_html_viewer`)
- Modify: `tests/test_html_viewer.py` (update tests)

### HTML Viewer v2 Structure

```
┌─────────────────────────────────────────────┐
│ ☰ Architecture Model Standard              │
├──────┬──────────────────────────────────────┤
│ Nav  │  Content Area                        │
│      │                                      │
│ ◉ ConOps                                    │
│ ○ Functional                                │
│ ○ Logical                                   │
│ ○ Use Cases                                 │
│ ─────                                       │
│ Components                                  │
│   COMP-CORE                                 │
│   COMP-CLI                                  │
│   ...                                       │
│ Capabilities                                │
│   CAP-0                                     │
│   CAP-1                                     │
│   ...                                       │
│ Behaviors                                   │
│   BEH-C1                                    │
│   BEH-P1                                    │
│   ...                                       │
└──────┴──────────────────────────────────────┘
```

**Navigation:**
1. Top 4 items are SE overview diagrams (ConOps, Functional, Logical, Use Cases)
2. Below: entity sections (Components, Capabilities, Behaviors) — each expandable
3. Click any entity → content area shows entity explorer with accordion facets

**Entity Explorer Panel:**
```
┌──────────────────────────────────────┐
│ COMP-CORE: Core Processing          │
│ ▼ Capabilities ──────────────────── │
│   [Mermaid: capabilities realized]  │
│ ▶ Interfaces ─────────────────────  │
│ ▶ Dependencies ───────────────────  │
│ ▶ Behaviors ──────────────────────  │
│ ▶ Sub-Components ─────────────────  │
└──────────────────────────────────────┘
```

**Key implementation details:**
- `securityLevel: 'loose'` in mermaid.initialize()
- All Mermaid rendering done client-side via CDN
- Accordion sections lazy-render Mermaid when expanded
- Mobile: sidebar collapses to hamburger menu
- Dark theme (same as v1)
- Generate ALL diagram content as JSON embedded in `<script>` tag
- JavaScript renders diagrams on demand

### Step 1: Update HTML viewer tests
### Step 2: Run → FAIL
### Step 3: Rewrite `generate_html_viewer` function
### Step 4: Run → PASS
### Step 5: Full suite
### Step 6: Commit

```bash
git commit -m "feat(viz): rebuild HTML viewer v2 with SE navigation and entity explorer"
```

---

## Task 6: Generate, Verify, and Zip

**Files:**
- Output: `.architecture/diagrams/viewer.html`
- Output: `~/Desktop/architecture-viewer.zip`

### Steps:

1. Run Python script to generate the viewer:
```python
from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_html_viewer
from pathlib import Path

model = load_model(Path(".architecture-model.yaml"))
generate_html_viewer(model, Path(".architecture/diagrams/viewer.html"), "Architecture Model Standard")
```

2. Verify file exists and is reasonable size (>50KB)
3. Zip to Desktop:
```bash
cd .architecture/diagrams && zip ~/Desktop/architecture-viewer.zip viewer.html
```

4. Push all changes:
```bash
git add -A
git commit -m "docs: generate SE-quality architecture viewer"
git push  # use the push command from instructions
```

---

---

## Task 7: Fix InferStage — AST-Derived Capability Descriptions

**Goal:** InferStage currently ignores docstrings, signatures, and body hints when inferring capabilities. Fix it to produce semantic descriptions derived from AST data.

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py`
- Modify: `src/architecture_model/pipeline/infer_types.py` (if needed)
- Modify: `tests/test_pipeline_infer.py`

### Current problem:
- `_infer_from_domain_modules()` produces descriptions like `"Domain logic in parser.py"` — purely mechanical
- `_infer_from_routes()` produces `"CRUD operations for users (3 endpoints)"` — slightly better but still mechanical
- Rich AST data (docstrings, function signatures, class info) is available in `ModuleRecord` but **ignored**

### What to change:

Add a helper `_describe_capability(modules: list[ModuleRecord]) -> str` that:
1. Collects module-level docstrings from the modules that belong to this capability
2. Collects function docstrings (first line only) from public functions
3. Collects class names and their docstrings
4. Synthesizes a 1-2 sentence description: `"Parses YAML architecture models, validates entity references, and produces typed ArchitectureModel instances"`

Call this helper in each inference strategy to set `InferredCapability.description` to the semantic description.

### Step 1: Write failing test

```python
# In tests/test_pipeline_infer.py — add new test
def test_infer_description_uses_docstrings(self, tmp_path):
    """Capability descriptions should incorporate module/function docstrings."""
    (tmp_path / "parser.py").write_text('''
"""Parse architecture model files into typed objects."""

def load_model(path: str) -> dict:
    """Load and validate an architecture model from YAML."""
    pass

def validate_refs(model: dict) -> list:
    """Check all entity references for integrity."""
    pass
''')
    result = _run_observe_then_infer(tmp_path)
    caps = result.output.capabilities
    assert len(caps) >= 1
    desc = caps[0].description.lower()
    # Should mention parsing or architecture or model — not just "domain logic in parser.py"
    assert any(word in desc for word in ["parse", "architecture", "model", "validate"]), \
        f"Description should be semantic, got: {caps[0].description}"
```

### Step 2: Run test → FAIL
### Step 3: Implement `_describe_capability()` and wire into inference strategies
### Step 4: Run → PASS
### Step 5: Full suite
### Step 6: Commit

```bash
git commit -m "feat(pipeline): derive semantic capability descriptions from AST docstrings"
```

---

## Task 8: Enrich LLM Refine Prompt — Hierarchy + Richer Context

**Goal:** The LLM refine step for "infer" stage sends extremely lossy data (just function/class names). Enrich the prompt to include docstrings and ask the LLM to organize capabilities into a hierarchy.

**Files:**
- Modify: `src/architecture_model/pipeline/gap_prompts.py`
- Modify: `src/architecture_model/pipeline/llm_refine.py`
- Create: `tests/test_pipeline_llm_hierarchy.py`

### What to change in `gap_prompts.py`:

1. **Enrich `_fmt_modules()`** to include docstrings and key signatures:
```python
def _fmt_modules(modules: list[dict]) -> str:
    lines: list[str] = []
    for m in modules:
        funcs = ", ".join(m.get("functions", []))
        classes = ", ".join(m.get("classes", []))
        doc = m.get("docstring", "")
        doc_str = f'  "{doc}"' if doc else ""
        lines.append(f"- {m['path']}{doc_str}  functions=[{funcs}]  classes=[{classes}]")
    return "\n".join(lines)
```

2. **Update `_TEMPLATES["infer"]`** to request hierarchical capabilities:
```python
"infer": """You are an architecture analyst. Given these source modules, identify the capabilities this codebase provides.

## Modules
{modules}

## Task
Analyze the module names, docstrings, functions, and classes to infer a **hierarchical capability tree**:
1. **Root capability** — one sentence describing the system's overall purpose
2. **L1 capability groups** — 3-5 thematic groups (e.g., "Understand", "Validate", "Generate", "Evolve")
3. **L2 capabilities** — concrete functional blocks within each group
4. **L3 sub-capabilities** — specific functions within each L2 capability

Each capability must have a `name` (verb phrase) and `description` (1 sentence, semantic, not "domain logic in X.py").

Respond with JSON only:
```json
{{"capabilities": [{{"name": "...", "description": "...", "sub_capabilities": [{{"name": "...", "description": "...", "sub_capabilities": [...]}}]}}], "behaviors": [{{"name": "...", "type": "..."}}]}}
```"""
```

3. **Update `llm_refine.py`** — the `_normalize_infer()` function needs to handle hierarchical capability JSON. Flatten the hierarchy into flat capabilities with `sub_capabilities` field populated, and create `contains` relationship data.

### What to change in `llm_refine.py`:

In `_normalize_infer()`, when processing LLM output capabilities:
- Walk the tree recursively
- Assign IDs: root=`CAP-F0`, L1 groups=`CAP-F0.1`..`CAP-F0.4`, L2=`CAP-F1`..`CAP-FN`, L3=`CAP-F1.1`..
- Set `sub_capabilities` field on each parent
- Store `description` from LLM response

Also update `_STAGE_INPUT_KEYS` to include `"docstrings"` for the infer stage, and pass module docstrings to the prompt builder.

### Step 1: Write failing test
```python
# tests/test_pipeline_llm_hierarchy.py
"""Tests for LLM-driven capability hierarchy."""
from architecture_model.pipeline.gap_prompts import build_reinfer_prompt, _fmt_modules

def test_fmt_modules_includes_docstring():
    modules = [{"path": "parser.py", "functions": ["load"], "classes": ["Model"], "docstring": "Parse YAML models"}]
    result = _fmt_modules(modules)
    assert "Parse YAML models" in result

def test_infer_prompt_requests_hierarchy():
    prompt = build_reinfer_prompt("infer", modules=[{"path": "a.py", "functions": ["f"], "classes": []}])
    assert "hierarchical" in prompt.lower() or "hierarchy" in prompt.lower()

def test_normalize_infer_handles_hierarchy():
    from architecture_model.pipeline.llm_refine import _normalize_infer
    raw = {
        "capabilities": [
            {"name": "Root", "description": "The system", "sub_capabilities": [
                {"name": "Parse", "description": "Parse files", "sub_capabilities": [
                    {"name": "Parse YAML", "description": "Parse YAML files"}
                ]}
            ]}
        ],
        "behaviors": []
    }
    result = _normalize_infer(raw)
    caps = result["capabilities"]
    # Should have flattened: Root + Parse + Parse YAML = 3
    assert len(caps) >= 3
    # Root should have sub_capabilities
    root = [c for c in caps if c["name"] == "Root"][0]
    assert len(root.get("sub_capabilities", [])) >= 1
```

### Step 2-6: TDD cycle + commit

```bash
git commit -m "feat(pipeline): LLM-driven capability hierarchy with enriched module context"
```

---

## Task 9: Fix SynthesizeStage — Emit Descriptions + Hierarchy

**Goal:** SynthesizeStage currently drops capability descriptions and hierarchy. Fix it to emit full capability data.

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py` (lines 79-82)
- Modify: `tests/test_pipeline_synthesize.py`

### What to change:

In `_build_system_model_yaml()` around line 79-82:
```python
# BEFORE (drops description):
cap_dict: dict[str, Any] = {"id": cap.id, "name": cap.name}

# AFTER (preserves description + status):
cap_dict: dict[str, Any] = {"id": cap.id, "name": cap.name, "status": "ACTIVE"}
if hasattr(cap, "description") and cap.description:
    cap_dict["description"] = cap.description
```

Similarly update the SoS model builder around line 248-259.

### Step 1: Write failing test
```python
def test_capability_description_preserved(self, tmp_path):
    """Capability descriptions should survive synthesis."""
    # ... set up pipeline context with capabilities that have descriptions
    # ... run synthesize
    # ... check output YAML has descriptions
```

### Step 2-6: TDD cycle + commit

```bash
git commit -m "fix(pipeline): preserve capability descriptions and status in emitted model"
```

---

## Task 10: Add `contains` Relationships for Capability Hierarchy in RelateStage

**Goal:** RelateStage creates `contains` relationships for layers→components but never for capability→sub-capability. Add this.

**Files:**
- Modify: `src/architecture_model/pipeline/relate.py`
- Modify: `tests/test_pipeline_relate.py` (or add tests to existing file)

### What to change:

In RelateStage's `run()` method, after existing relationship derivation, add:
```python
# Capability hierarchy: emit contains relationships for sub_capabilities
for cap in infer_result.capabilities:
    if hasattr(cap, "sub_capabilities") and cap.sub_capabilities:
        for sub_id in cap.sub_capabilities:
            relationships.append(DerivedRelationship(
                from_id=cap.id, to_id=sub_id, rel_type="contains",
                evidence="capability hierarchy"
            ))
```

### Step 1: Write failing test
```python
def test_capability_hierarchy_contains(self, tmp_path):
    """Capabilities with sub_capabilities should get contains relationships."""
    # ... set up context with capabilities that have sub_capabilities populated
    # ... run relate
    # ... check for contains relationships between parent and child caps
```

### Step 2-6: TDD cycle + commit

```bash
git commit -m "feat(pipeline): emit contains relationships for capability hierarchy"
```

---

## Execution Dependencies (Updated)

```
Workstream A (Model + Viewer):
Task 1 (Capabilities) ──┐
Task 2 (Layers) ─────────┤── Task 3 (SE Diagrams) ── Task 4 (Explorer) ── Task 5 (HTML) ── Task 6 (Generate)

Workstream B (Pipeline):
Task 7 (AST Descriptions) ── Task 8 (LLM Hierarchy) ── Task 9 (Emit Fix) ── Task 10 (Relate Contains)
```

Workstreams A and B are **independent** — they can be executed in parallel.
Within each workstream, tasks are sequential.

Tasks 1-2 and Tasks 7-8 can run in parallel.

---

## Test Commands

- Single test file: `pytest tests/test_capability_hierarchy.py -v`
- Full suite: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
- Expected baseline: 7 failed, ~1670 passed, ~100 skipped

## Push Command

```bash
git -c http.proxy="" push https://opn-arch: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@github.com/opn-arch/architecture-model-standard.git feature/model-quality-16wp
```
