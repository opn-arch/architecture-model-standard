# Hierarchy Reference And Ownership Follow-up Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task.

**Goal:** Correct typed ID validation, full-system file ownership, and nested component interface remapping.

**Architecture:** Promotion validates polymorphic reference fields only when values use their contractual entity prefix. Synthesis computes disjoint full-system boundaries before scoped execution and recursively remaps nested typed component references through the local ID registry.

**Tech Stack:** Python, dataclasses, PyYAML, pytest.

---

### Task 1: Typed Reference Validation

**Files:**
- Modify: `src/architecture_model/pipeline/emit.py`
- Test: `tests/test_pipeline_emit.py`

1. Add failing tests proving hyphenated semantic requirement/interface names promote.
2. Add failing tests proving missing `REQ-*` and `IF-*` references block promotion.
3. Implement field-specific ID recognition.
4. Run emit tests green.

### Task 2: Full Boundary Ownership

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Test: `tests/test_pipeline_synthesize.py`
- Test: `tests/test_pipeline_recursive.py`

1. Add a failing test with overlapping full-system boundaries.
2. Assert scoped contexts and emitted system boundaries have disjoint files.
3. Implement deterministic ownership before scoped execution.
4. Rerun adversarial hierarchy tests.

### Task 3: Nested Target Remapping

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Test: `tests/test_pipeline_synthesize.py`
- Test: `tests/test_pipeline_emit.py`

1. Add a failing normalization-collision test for `interfaces[].target_component`.
2. Remap nested targets through the local ID registry.
3. Validate the resulting model promotes successfully.
4. Run focused and full suites.
5. Commit only focused source, tests, and this plan; exclude `.architecture` dirt.
