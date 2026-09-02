# Hierarchical Pipeline Correctness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make recursive extraction emit validated, atomic, hierarchical models with scoped evidence and collision-safe subsystem viewer navigation.

**Architecture:** Keep synthesis responsible for evidence-preserving self-contained model construction, while emit owns staging, final validation, and atomic canonical promotion. Keep canonical YAML hierarchical; viewer composition loads referenced models into qualified presentation-only data.

**Tech Stack:** Python dataclasses, PyYAML, pytest, existing parser/validator/pipeline/viewer APIs.

---

### Task 1: Scope all observed evidence

**Files:**
- Modify: `src/architecture_model/pipeline/observe.py`
- Test: `tests/test_pipeline_observe.py`

1. Add failing tests with disjoint route, migration/model, test, and documentation files.
2. Run focused tests and confirm unrelated evidence leaks into scoped inventories.
3. Filter every file-derived inventory collection through normalized scope/shared paths.
4. Re-run focused tests.

### Task 2: Serialize complete subsystem and hierarchical top models

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Test: `tests/test_pipeline_synthesize.py`

1. Add failing tests for subsystem metadata, behavior semantics and structured steps, valid relationship directions, and non-dangling references.
2. Add failing tests proving top models contain only full Systems and inline Components without flattened subsystem entities.
3. Run focused tests and confirm failures.
4. Implement evidence-preserving serializers and hierarchical SoS construction.
5. Parse and validate generated models in focused tests.

### Task 3: Validate and atomically promote canonical artifacts

**Files:**
- Modify: `src/architecture_model/pipeline/emit.py`
- Modify: `src/architecture_model/pipeline/emit_types.py`
- Modify: `src/architecture_model/pipeline/report.py`
- Modify: `src/architecture_model/pipeline/history.py`
- Test: `tests/test_pipeline_emit.py`
- Test: `tests/test_pipeline_report.py`
- Test: `tests/test_pipeline_history.py`

1. Add failing success and injected-failure tests for root canonical paths, structural validation, candidate preservation, and unchanged prior canonical models.
2. Add failing assertions for extraction versus final score, issue/path/promotion reporting, and history.
3. Implement staging and all-model validation after enrichment, followed by per-file atomic replacement only after the whole candidate set passes structural checks.
4. Re-run focused tests.

### Task 4: Compose hierarchy in the viewer only

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `src/architecture_model/cli/main.py`
- Test: `tests/test_visualize.py`

1. Add a failing integration test with two referenced subsystem models sharing `COMP-1`.
2. Assert qualified keys, display IDs, system navigation, and qualified comment keys in generated HTML.
3. Load only valid in-repository `sub_model_ref` targets and compose qualified presentation data without mutating the top model.
4. Re-run focused tests.

### Task 5: Recursive integration and verification

**Files:**
- Test: `tests/test_pipeline_recursive.py`

1. Add a temp-repository recursive test covering disjoint scopes, two full systems, one inline component, workflow preservation, canonical refs, validation, viewer collisions, and final reporting.
2. Run all focused pipeline/viewer tests.
3. Run `pytest tests/ -v --ignore=tests/test_config_loader.py` and record known unrelated failures separately.
4. Run architecture representativeness and completion gates.
5. Commit only task-related source, tests, and this plan; preserve unrelated `.architecture` dirt.
