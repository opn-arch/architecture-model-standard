# Perfect Hierarchical Model Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the architecture-model-standard schema support explicit component hierarchy, produce a perfect model of the a-m-s codebase with capabilities + relationships, triage all open logs, and generate live SE artifacts.

**Architecture:** Add `parent_id`/`children` fields to Component dataclass, build a ~20-component hierarchical model grouped by complexity, define 15 capabilities realized by components, populate 30+ relationships from import analysis, then generate functional/logical/usecase/requirements docs.

**Tech Stack:** Python dataclasses, YAML, pytest

---

## Package 1: Schema Enhancement

### Task 1.1: Add hierarchy fields to Component

**Files:**
- Modify: `src/architecture_model/core/types.py:478-499`
- Modify: `src/architecture_model/core/validator.py` (add hierarchy consistency check)
- Test: `tests/test_hierarchy.py`

Add to Component:
```python
parent_id: str | None = None
children: list[str] = field(default_factory=list)
```

Add validator check: if parent_id set, parent must exist and list this component in children (bidirectional consistency).

### Task 1.2: Update parser serialization

Ensure parent_id/children round-trip through YAML parse/dump.

### Task 1.3: Update JSON schema spec

Add parent_id/children to spec/schema.json.

---

## Package 2: Triage 50 Open Logs

Close resolved/completed/obsolete. Group remaining into work packages.

---

## Package 3: Build Perfect Hierarchical Model

### Task 3.1: Component hierarchy (by complexity)

Top-level components with sub-components:
- Core → Types, Validation, Persistence, Coverage, Confidence
- Pipeline → Observe, Transform, Emit, Coordination, Learning
- Manifest → Scanners, Graph, Grouping
- Documentation → SE Generators, Templates, Rendering
- Extract → From-Code
- Authoring → Parser, Gate
- CLI & Config
- Orchestration → Enrich, Decompose

### Task 3.2: Capabilities (functional breakdown)

15 capabilities mapped to realizing components.

### Task 3.3: Relationships from imports

30+ relationships derived from actual import edges.

---

## Package 4: Live SE Artifacts

Generate: functional_analysis, logical_architecture, use_cases, requirements_analysis
Keep in `.architecture/docs/` and regenerate on model changes.

---
