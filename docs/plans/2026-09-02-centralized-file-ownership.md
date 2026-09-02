# Centralized File Ownership Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task.

**Goal:** Use one deterministic file ownership map throughout hierarchical synthesis.

**Architecture:** Build one immutable ownership object from allocation and decomposition before scoped synthesis. Component precedence is stable component ID. Boundary precedence is explicit allocated-component membership, then smaller boundary file count (specificity), then stable boundary ID. Projection, scoped evidence, semantic derivation, inline assembly, and full-system scoping consume this object rather than recomputing ownership.

**Tech Stack:** Python dataclasses, pytest, PyYAML.

---

### Task 1: Reproduce Cross-System Leakage

**Files:**
- Test: `tests/test_pipeline_synthesize.py`

1. Add overlapping full boundaries where `shared.py` belongs to `SYS-1` and component `COMP-1`.
2. Assert `SYS-2` scoped context excludes `shared.py` and its emitted model excludes `COMP-1`.
3. Run the test and verify failure.

### Task 2: Centralize Ownership

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Test: `tests/test_pipeline_synthesize.py`

1. Add a frozen ownership dataclass and one builder.
2. Pass it to full-boundary normalization, scoped correction filtering, model projection, semantic ownership, and SoS inline assembly.
3. Remove local owner map recomputation.
4. Run focused tests green.

### Task 3: Verify And Commit

1. Run focused hierarchy/promotion/viewer tests.
2. Run `pytest tests/ -v --ignore=tests/test_config_loader.py`.
3. Run diff checks and architecture gate.
4. Commit source, tests, and this plan only; preserve `.architecture` dirt.
