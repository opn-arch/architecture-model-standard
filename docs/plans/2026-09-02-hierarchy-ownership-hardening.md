# Hierarchy Ownership Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task.

**Goal:** Eliminate ownership leakage, ambiguous provenance, and invalid embedded references from hierarchical synthesis.

**Architecture:** Build deterministic ownership indexes before projection, attach semantics only through direct evidence, and validate every embedded reference before promotion. Reject duplicate resolution IDs at the bridge and decline ambiguous provenance in the library.

**Tech Stack:** Python dataclasses, PyYAML, pytest, architecture-model pipeline and MCP bridge.

---

### Task 1: Correction And Workflow Compatibility

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Modify: `src/architecture_model/pipeline/infer.py`
- Test: `tests/test_pipeline_synthesize.py`
- Test: `tests/test_pipeline_infer.py`

1. Add failing tests for target-to-files allocation maps, list records, `files_sent` workflows, and duplicate resolution IDs.
2. Verify each failure.
3. Implement scoped allocation trimming, source fallback, and ambiguous provenance rejection.
4. Run focused tests green.

### Task 2: Exclusive Projection And Direct References

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Test: `tests/test_pipeline_synthesize.py`
- Test: `tests/test_pipeline_recursive.py`

1. Add failing tests for overlapping boundaries and shared files.
2. Add failing tests preventing component-wide requirement/interface propagation.
3. Implement stable file/component/boundary ownership and direct entity selection.
4. Implement deterministic primary capability intent selection.
5. Run projection and adversarial integration tests green.

### Task 3: Embedded Reference Validation

**Files:**
- Modify: `src/architecture_model/pipeline/synthesize.py`
- Modify: `src/architecture_model/pipeline/emit.py`
- Test: `tests/test_pipeline_synthesize.py`
- Test: `tests/test_pipeline_emit.py`

1. Add failing collision/remap tests for structured steps.
2. Add failing promotion tests for unknown component, capability, provider, and reference-list IDs.
3. Implement recursive reference remapping and structural validation.
4. Run focused validation, promotion, and viewer tests green.

### Task 4: Bridge Duplicate Validation

**Files:**
- Modify: `../opencode-arch/src/opencode_arch/mcp/tools/pipeline.py`
- Test: `../opencode-arch/tests/test_pipeline_tool.py`

1. Add a failing duplicate-resolution test.
2. Reject duplicate non-empty IDs with a clear structured error.
3. Run bridge tests and full opencode-arch suite.
4. Commit bridge changes separately.

### Task 5: Final Verification And Commits

1. Run focused architecture-model-standard tests.
2. Run `pytest tests/ -v --ignore=tests/test_config_loader.py`.
3. Run architecture checks and gate, recording pre-existing limitations.
4. Commit only focused standard files, excluding `.architecture` dirt.
5. Verify both commit SHAs and worktree states.
