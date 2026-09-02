# Hierarchy Semantic Preservation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task.

**Goal:** Preserve scoped and inline architecture semantics in hierarchical models without cross-boundary evidence leakage.

**Architecture:** Add deterministic boundary evidence filtering, reuse scope-aware model projection for inline entities, and enrich emitted entities from valid local graph evidence. Keep subsystem internals exclusively in submodels and inline details exclusively in the top model.

**Tech Stack:** Python dataclasses, PyYAML, pytest, architecture-model parser/validator/viewer.

---

### Task 1: Scoped Correction Provenance

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Test: `tests/test_pipeline_synthesize.py`

1. Write a failing test with two disjoint boundaries, structured behavior corrections, shared evidence, and matching LLM call records.
2. Run the focused test and verify each scoped context currently receives no evidence.
3. Implement normalized file intersection and explicit shared-evidence selection.
4. Copy matching LLM provenance by `resolution_id` while retaining scoped invocation and parent run metadata.
5. Run focused tests and verify no cross-system leakage.

### Task 2: Inline Projection And Semantic Derivation

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Test: `tests/test_pipeline_semantic_propagation.py`

1. Write failing projection tests for inline capabilities, workflows, interfaces, requirements, constraints, and relationships.
2. Implement scope-aware projection from top-stage outputs and deterministic ID/reference remapping.
3. Derive component intent, goals, failure modes, monitoring, responsibilities, requirement references, and interface references from local graph evidence.
4. Populate capability and behavior requirement/interface references when graph or source ownership supports them.
5. Preserve requirement rationale, MoE, value functions, and typed component interfaces.
6. Run focused tests and validate every emitted model.

### Task 3: End-To-End Hierarchy Verification

**Files:**
- Modify: `tests/test_pipeline_recursive.py`
- Modify: `tests/test_pipeline_semantic_propagation.py`

1. Add a five-file full subsystem and two inline components with distinct structured resolutions and numeric requirements/interfaces.
2. Assert the full workflow appears only in its submodel and inline workflows appear only in the top model.
3. Assert semantic references, unique IDs, no dangling relationships, promotion, qualified viewer relationships, and all viewer pages.
4. Run focused pipeline, validator, emit, and viewer tests.
5. Run `pytest tests/ -v --ignore=tests/test_config_loader.py` and record expected unrelated failures separately.
6. Stage only source, tests, and these plan documents; commit once with a concise focused message.
