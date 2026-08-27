---
document: Maintenance Manual
system: architecture-model-standard/Core
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: 3f3196a55536
edition: 1
---

# Maintenance Manual: architecture-model-standard/Core

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Core (COMP-CORE) | library | LYR-CORE | 18 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Core | — | — | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Core (COMP-CORE)

**Files:**
- `src/architecture_model/core/types.py`
- `src/architecture_model/core/parser.py`
- `src/architecture_model/core/validator.py`
- `src/architecture_model/core/slicer.py`
- `src/architecture_model/core/differ.py`
- `src/architecture_model/core/merger.py`
- `src/architecture_model/core/coverage.py`
- `src/architecture_model/core/confidence.py`
- `src/architecture_model/core/compression.py`
- `src/architecture_model/core/corrections.py`
- `src/architecture_model/core/cluster.py`
- `src/architecture_model/core/decomposer.py`
- `src/architecture_model/core/representativeness.py`
- `src/architecture_model/core/regen_readiness.py`
- `src/architecture_model/core/source_block_assign.py`
- `src/architecture_model/core/source_block_quality.py`
- `src/architecture_model/core/test_affinity.py`
- `src/architecture_model/core/visualize.py`

## Known Constraints

| Component | Constraint | Type | Detail |
|-----------|-----------|------|--------|
| Core | No LLM in Core | technology | — |
