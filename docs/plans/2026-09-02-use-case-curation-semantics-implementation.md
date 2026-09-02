# Use-Case Curation Semantics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add strict use-case curation semantics and project all explicitly featured logs-db workflows.

**Architecture:** Extend typed curation records and fail-closed parsing in `view_curation.py`, then consume them canonically-first in `se_view_projectors.py`. Keep all inferred semantics presentation-only with explicit evidence provenance.

**Tech Stack:** Python dataclasses, PyYAML, pytest, DiagramSpec.

---

### Task 1: Strict Use-Case Curation Records

**Files:**
- Modify: `src/architecture_model/core/view_curation.py`
- Test: `tests/test_view_curation.py`

1. Write failing parser tests for valid actors, associations, and annotations.
2. Write failing tests for unsupported views, unknown keys, missing evidence, unsafe text, unresolved selectors, wrong entity types, and duplicate IDs.
3. Run focused tests and confirm expected failures.
4. Add minimal typed records and fail-closed parsing.
5. Run focused tests and confirm they pass.

### Task 2: Featured Budget and Inferred Semantics

**Files:**
- Modify: `src/architecture_model/core/se_view_projectors.py`
- Test: `tests/test_use_case_projector.py`

1. Write failing tests proving ten featured cases survive the 15-node budget.
2. Write failing tests for inferred actor nodes, dashed evidence edges, canonical-first annotation fallback, inferred badges/provenance, nonmutation, and canonical triggers/contains.
3. Run focused tests and confirm expected failures.
4. Implement featured-first budgeting and typed curation projection.
5. Run focused projector regressions and confirm they pass.

### Task 3: Logs-DB Compatibility and Verification

**Files:**
- Test: `tests/test_use_case_projector.py`

1. Add a compatibility test against `/Users/baigm2/Documents/Projects/logs_db` without editing its profile.
2. Verify the existing profile renders all ten featured use cases.
3. Build a temporary augmented profile using real repository evidence and verify inferred associations/annotations load and project.
4. Run focused and full tests with `PYTHONPATH=src` and the documented config-loader ignore.
5. Self-review, run architecture gate, and commit the implementation.
