# Rich SE Model + Enhanced Viewer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the architecture model schema with full SE fields (goals, MoEs, value functions, failure modes, trade-offs, decisions, monitoring) on all entity types, add viewer enhancements (comments, pipeline diagrams, execution history, KaTeX), and integrate into the extraction pipeline.

**Architecture:** Schema-first approach — extend types.py with new fields and a Decision dataclass, update parser/validator/schema.json, then enhance the viewer JS/CSS to display them. Pipeline enrichment adds LLM-assisted population of these fields during extraction.

**Tech Stack:** Python dataclasses, YAML, Mermaid.js, KaTeX (CDN or embedded), localStorage API, JSON Schema.

**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
**Baseline:** 7 failed (pre-existing), 1811 passed, 102 skipped

---

## Phase 1: Schema Additions

### Task 1.1: Add `Decision` dataclass and `decisions` field to BaseEntity

**Files:**
- Modify: `src/architecture_model/core/types.py:289-300` (BaseEntity)
- Test: `tests/test_types_decisions.py` (create)

**Step 1: Write the failing test**

```python
# tests/test_types_decisions.py
"""Tests for Decision dataclass and decisions field on entities."""
from architecture_model.core.types import (
    Decision, Component, Capability, Behavior, Actor, Interface,
    Constraint, Layer, System, Requirement, Status,
)

class TestDecision:
    def test_decision_fields(self):
        d = Decision(date="2026-09-01", choice="Use PostgreSQL",
                     rationale="Better JSON support", alternatives=["MySQL", "SQLite"])
        assert d.date == "2026-09-01"
        assert d.choice == "Use PostgreSQL"
        assert len(d.alternatives) == 2

    def test_decision_defaults(self):
        d = Decision()
        assert d.date == ""
        assert d.choice == ""
        assert d.alternatives == []

class TestDecisionsOnEntities:
    def test_component_has_decisions(self):
        c = Component(id="C-1", name="X", status=Status.ACTIVE,
                      decisions=[Decision(choice="Use FastAPI")])
        assert len(c.decisions) == 1

    def test_capability_has_decisions(self):
        c = Capability(id="CAP-1", name="X", status=Status.ACTIVE,
                       decisions=[Decision(choice="Split into two")])
        assert len(c.decisions) == 1

    def test_behavior_has_decisions(self):
        b = Behavior(id="BEH-1", name="X", status=Status.ACTIVE,
                     decisions=[Decision(choice="Async pattern")])
        assert len(b.decisions) == 1
```

**Step 2:** Run test — expect FAIL (`ImportError: cannot import name 'Decision'`)

**Step 3:** In `types.py`, add before `BaseEntity`:
```python
@dataclass
class Decision:
    """An architecture decision record for an entity."""
    date: str = ""
    choice: str = ""
    rationale: str = ""
    alternatives: list[str] = field(default_factory=list)
    context: str = ""
```
Add to `BaseEntity`: `decisions: list[Decision] = field(default_factory=list)`

**Step 4:** Run test — expect PASS

**Step 5:** Commit: `feat(schema): add Decision dataclass and decisions field to BaseEntity`

---

### Task 1.2: Add goals, moes, trade_offs, failure_modes, monitored to remaining entity types

**Files:**
- Modify: `src/architecture_model/core/types.py` (Capability ~314, Behavior ~351, Requirement ~613, System ~523, Component)
- Test: `tests/test_types_se_fields.py` (create)

**New fields by entity type:**

| Entity | New Fields |
|---|---|
| Capability | `goals`, `trade_offs`, `failure_modes`, `monitored` (all `list[str]`) |
| Behavior | `goals`, `moes`, `failure_modes` (all `list[str]`) |
| Requirement | `value_function: str`, `moes: list[str]`, `failure_modes: list[str]`, `monitored: list[str]` |
| System | `goals`, `trade_offs`, `failure_modes`, `monitored` (all `list[str]`) |
| Component | `monitored: list[str]` (already has goals, moes, trade_offs, failure_modes) |

**Step 1:** Write tests for each new field on each type
**Step 2:** Add fields to dataclasses
**Step 3:** Run tests — all pass
**Step 4:** Commit: `feat(schema): add SE fields across entity types`

---

### Task 1.3: Update parser to handle Decision and new fields in YAML

**Files:**
- Modify: `src/architecture_model/core/parser.py`
- Test: `tests/test_parser_decisions.py` (create)

Test YAML roundtrip: write model with decisions → load → verify Decision objects created.
Parser may need explicit `Decision` dict→dataclass conversion if not auto-handled.

**Commit:** `feat(parser): handle Decision dataclass and new SE fields in YAML roundtrip`

---

### Task 1.4: Update JSON Schema (spec/schema.json)

**Files:**
- Modify: `src/architecture_model/spec/schema.json`

Add Decision definition, decisions array to base entity, new fields to each entity type.

**Commit:** `feat(spec): update JSON Schema with Decision, value_function, and SE fields`

---

### Task 1.5: Update validator and depth scoring

**Files:**
- Modify: `src/architecture_model/core/validator.py`
- Modify: `src/architecture_model/core/visualize.py` (`_depth_fields` dict)

Add new fields to depth scoring so entities with goals/failure_modes/decisions score higher.

**Commit:** `feat(validator): add SE field validation and depth scoring`

---

## Phase 2: Viewer — Comments System

### Task 2.1: Add comment textarea to property cards

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (propCardHtml JS, CSS)
- Test: `tests/test_viewer_comments.py` (create)

**Implementation:**
- Add `<textarea class="comment-textarea">` to every property card
- `oninput` → `localStorage.setItem(project + ':comment:' + eid, value)`
- On card render → load from localStorage
- Toolbar buttons: "Export Comments" (downloads YAML), "Import Comments" (file input)

Export format:
```yaml
# Comments for project-name
COMP-1:
  comment: |
    This needs refactoring
```

**Commit:** `feat(viewer): add comment textarea with localStorage + export/import`

---

## Phase 3: Viewer — Behavior Pipeline Diagrams

### Task 3.1: Generate sequence and flow diagrams for behaviors

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Test: `tests/test_viewer_pipeline_diagrams.py` (create)

**New functions:**

`generate_behavior_sequence_diagram(model, behavior_id)` — For behaviors with `structured_steps`:
- Participants = unique component_refs → component names
- Messages = ordered steps between participants
- Trigger shown as note

`generate_behavior_flow_diagram(model, behavior_id)` — Fallback for step-only behaviors:
- Top-down flowchart, steps as nodes, sequential edges

**Commit:** `feat(viewer): add sequence and flow diagram generators for behaviors`

### Task 3.2: Embed pipeline diagrams in behavior property cards

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (propCardHtml, data serialization)

Pre-render diagrams for each behavior, serialize into data JSON, render via Mermaid in card.

**Commit:** `feat(viewer): embed pipeline diagrams in behavior property cards`

---

## Phase 4: Viewer — Pipeline Execution History

### Task 4.1: Parse and display pipeline-report.md

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Test: `tests/test_viewer_history.py` (create)

`_load_pipeline_history(repo_path)`:
- Read `.architecture-models/pipeline-report.md`
- Parse timestamp, duration, per-stage scores
- Return structured dict

Display in component cards + top-level "Pipeline History" panel.

**Commit:** `feat(viewer): display pipeline execution history per component`

---

## Phase 5: Extraction Pipeline — Auto-populate SE fields

### Task 5.1: Enhance infer stage for intent, goals, failure_modes

**Files:**
- Modify: `src/architecture_model/pipeline/infer.py`
- Test: `tests/test_pipeline_infer_se.py` (create)

Heuristics:
- Module docstrings → `intent`
- Function names + docstrings → `goals`
- Error handling patterns (try/except, raise) → `failure_modes`
- Logging/metrics calls → `monitored`
- LLM callback for richer inference when available

**Commit:** `feat(pipeline): auto-populate intent, goals, failure_modes in infer stage`

### Task 5.2: Requirements derivation with rationale and MoEs

**Files:**
- Modify: `src/architecture_model/pipeline/specify.py`
- Test: `tests/test_pipeline_requirements.py` (create)

Derive from constants, config, test assertions, docstring constraints.

**Commit:** `feat(pipeline): derive requirements with rationale, MoEs, value functions`

---

## Phase 6: Value Function Rendering (KaTeX)

### Task 6.1: Embed KaTeX and render value_function

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Test: `tests/test_viewer_katex.py` (create)

Embed KaTeX min.js (~28KB gzipped) inline for self-contained viewer.
Render `value_function` fields in requirement property cards.

**Commit:** `feat(viewer): render LaTeX value functions with KaTeX`

---

## Phase 7: Integration

### Task 7.1: Full suite, regenerate logs-db viewer, push

- Run full test suite (expect same 7 pre-existing failures)
- Re-run extraction pipeline on logs-db with enriched stages
- Generate viewer with all new features
- Commit and push both repos
