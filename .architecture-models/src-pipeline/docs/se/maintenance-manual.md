---
document: Maintenance Manual
system: Src (pipeline)
system_id: SYS-unknown
generated_at: 2026-08-18T23:36:32Z
generator_version: 0.3.0
model_hash: ccd998005d8e
edition: 6
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 21/21 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: Src (pipeline)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Allocate (src-pipeline-COMP-16) | service | — | 2 | 0 | 0 |
| Artifacts (src-pipeline-COMP-18) | service | — | 1 | 0 | 0 |
| Cache (src-pipeline-COMP-19) | service | — | 1 | 0 | 0 |
| Context Gen (src-pipeline-COMP-20) | service | — | 1 | 0 | 0 |
| Contract (src-pipeline-COMP-21) | service | — | 2 | 0 | 0 |
| Coordinator (src-pipeline-COMP-23) | service | — | 1 | 0 | 0 |
| Corrections (src-pipeline-COMP-24) | service | — | 1 | 0 | 0 |
| Decompose (src-pipeline-COMP-25) | service | — | 3 | 0 | 0 |
| Emit (src-pipeline-COMP-27) | service | — | 2 | 0 | 0 |
| Global Learning (src-pipeline-COMP-29) | service | — | 2 | 0 | 0 |
| Infer (src-pipeline-COMP-30) | service | — | 2 | 0 | 0 |
| Lessons (src-pipeline-COMP-33) | service | — | 1 | 0 | 0 |
| Observe (src-pipeline-COMP-34) | service | — | 2 | 0 | 0 |
| Protocol (src-pipeline-COMP-36) | service | — | 1 | 0 | 0 |
| Regen Score (src-pipeline-COMP-37) | service | — | 1 | 0 | 0 |
| Relate (src-pipeline-COMP-38) | service | — | 2 | 0 | 0 |
| Report (src-pipeline-COMP-40) | service | — | 1 | 0 | 0 |
| Requirements Derive (src-pipeline-COMP-41) | service | — | 1 | 0 | 0 |
| Specify (src-pipeline-COMP-42) | service | — | 2 | 0 | 0 |
| Synthesize (src-pipeline-COMP-44) | service | — | 2 | 0 | 0 |
| Validate (src-pipeline-COMP-46) | service | — | 2 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Allocate | Infer, Protocol, Observe, Corrections | Relate, Cache, Synthesize, Contract, Artifacts, Context Gen, Specify, Validate, Decompose, Coordinator, Emit | HIGH |
| Artifacts | Validate, Infer, Contract, Allocate, Observe, Specify, Protocol, Relate | Coordinator, Cache, Emit, Synthesize, Decompose | HIGH |
| Cache | Infer, Regen Score, Protocol, Allocate, Synthesize, Artifacts, Observe, Relate, Context Gen, Specify, Coordinator, Global Learning, Report, Validate, Corrections, Decompose, Emit, Requirements Derive, Contract, Lessons | Coordinator, Emit, Synthesize, Decompose | MEDIUM |
| Context Gen | Infer, Protocol, Allocate, Observe, Relate, Validate | Emit, Synthesize, Cache, Decompose, Coordinator | HIGH |
| Contract | Protocol, Allocate, Observe | Decompose, Artifacts, Coordinator, Cache, Emit, Synthesize | HIGH |
| Coordinator | Synthesize, Artifacts, Cache, Observe, Relate, Global Learning, Report, Validate, Corrections, Decompose, Emit, Requirements Derive, Contract, Lessons, Infer, Regen Score, Context Gen, Specify, Protocol, Allocate | Decompose, Cache, Emit, Synthesize | MEDIUM |
| Corrections | — | Coordinator, Cache, Emit, Synthesize, Infer, Decompose, Allocate | HIGH |
| Decompose | Emit, Coordinator, Requirements Derive, Contract, Lessons, Infer, Regen Score, Protocol, Allocate, Synthesize, Artifacts, Observe, Relate, Context Gen, Specify, Global Learning, Report, Validate, Corrections, Cache | Coordinator, Emit, Cache, Synthesize | MEDIUM |
| Emit | Observe, Regen Score, Context Gen, Specify, Global Learning, Synthesize, Artifacts, Cache, Relate, Decompose, Coordinator, Report, Validate, Corrections, Infer, Requirements Derive, Contract, Protocol, Allocate, Lessons | Decompose, Coordinator, Cache, Synthesize | MEDIUM |
| Global Learning | Protocol | Coordinator, Emit, Cache, Synthesize, Decompose | HIGH |
| Infer | Protocol, Observe, Corrections | Cache, Synthesize, Allocate, Artifacts, Context Gen, Validate, Decompose, Coordinator, Emit, Relate | HIGH |
| Lessons | Protocol | Decompose, Coordinator, Cache, Emit, Synthesize | HIGH |
| Observe | Protocol | Coordinator, Emit, Relate, Cache, Synthesize, Infer, Allocate, Contract, Artifacts, Context Gen, Specify, Decompose | HIGH |
| Protocol | — | Cache, Synthesize, Infer, Allocate, Contract, Context Gen, Specify, Validate, Decompose, Artifacts, Regen Score, Observe, Lessons, Global Learning, Coordinator, Emit, Report, Relate | HIGH |
| Regen Score | Protocol | Cache, Emit, Synthesize, Decompose, Coordinator | HIGH |
| Relate | Allocate, Observe, Infer, Protocol | Coordinator, Cache, Emit, Synthesize, Context Gen, Decompose, Artifacts, Validate | HIGH |
| Report | Protocol | Coordinator, Cache, Emit, Synthesize, Decompose | HIGH |
| Requirements Derive | — | Decompose, Coordinator, Cache, Emit, Synthesize | HIGH |
| Specify | Protocol, Allocate, Observe | Emit, Synthesize, Cache, Artifacts, Decompose, Coordinator | HIGH |
| Synthesize | Infer, Regen Score, Context Gen, Specify, Protocol, Allocate, Artifacts, Cache, Observe, Relate, Coordinator, Global Learning, Report, Validate, Corrections, Decompose, Emit, Requirements Derive, Contract, Lessons | Coordinator, Cache, Emit, Decompose | MEDIUM |
| Validate | Infer, Protocol, Allocate, Relate | Artifacts, Coordinator, Cache, Emit, Synthesize, Context Gen, Decompose | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Allocate (src-pipeline-COMP-16)

**Files:**
- `src/architecture_model/pipeline/allocate.py`
- `src/architecture_model/pipeline/allocate_types.py`
**Downstream dependents (must re-test):** Relate, Cache, Synthesize, Contract, Artifacts, Context Gen, Specify, Validate, Decompose, Coordinator, Emit

### Artifacts (src-pipeline-COMP-18)

**Files:**
- `src/architecture_model/pipeline/artifacts.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Synthesize, Decompose

### Cache (src-pipeline-COMP-19)

**Files:**
- `src/architecture_model/pipeline/cache.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Synthesize, Decompose

### Context Gen (src-pipeline-COMP-20)

**Files:**
- `src/architecture_model/pipeline/context_gen.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Cache, Decompose, Coordinator

### Contract (src-pipeline-COMP-21)

**Files:**
- `src/architecture_model/pipeline/contract.py`
- `src/architecture_model/pipeline/contract_types.py`
**Downstream dependents (must re-test):** Decompose, Artifacts, Coordinator, Cache, Emit, Synthesize

### Coordinator (src-pipeline-COMP-23)

**Files:**
- `src/architecture_model/pipeline/coordinator.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Synthesize

### Corrections (src-pipeline-COMP-24)

**Files:**
- `src/architecture_model/pipeline/corrections.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Synthesize, Infer, Decompose, Allocate

### Decompose (src-pipeline-COMP-25)

**Files:**
- `src/architecture_model/pipeline/__init__.py`
- `src/architecture_model/pipeline/decompose.py`
- `src/architecture_model/pipeline/decompose_types.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Cache, Synthesize

### Emit (src-pipeline-COMP-27)

**Files:**
- `src/architecture_model/pipeline/emit.py`
- `src/architecture_model/pipeline/emit_types.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Cache, Synthesize

### Global Learning (src-pipeline-COMP-29)

**Files:**
- `src/architecture_model/pipeline/global_learning.py`
- `src/architecture_model/pipeline/learning.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Cache, Synthesize, Decompose

### Infer (src-pipeline-COMP-30)

**Files:**
- `src/architecture_model/pipeline/infer.py`
- `src/architecture_model/pipeline/infer_types.py`
**Downstream dependents (must re-test):** Cache, Synthesize, Allocate, Artifacts, Context Gen, Validate, Decompose, Coordinator, Emit, Relate

### Lessons (src-pipeline-COMP-33)

**Files:**
- `src/architecture_model/pipeline/lessons.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Cache, Emit, Synthesize

### Observe (src-pipeline-COMP-34)

**Files:**
- `src/architecture_model/pipeline/observe.py`
- `src/architecture_model/pipeline/observe_types.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Relate, Cache, Synthesize, Infer, Allocate, Contract, Artifacts, Context Gen, Specify, Decompose

### Protocol (src-pipeline-COMP-36)

**Files:**
- `src/architecture_model/pipeline/protocol.py`
**Downstream dependents (must re-test):** Cache, Synthesize, Infer, Allocate, Contract, Context Gen, Specify, Validate, Decompose, Artifacts, Regen Score, Observe, Lessons, Global Learning, Coordinator, Emit, Report, Relate

### Regen Score (src-pipeline-COMP-37)

**Files:**
- `src/architecture_model/pipeline/regen_score.py`
**Downstream dependents (must re-test):** Cache, Emit, Synthesize, Decompose, Coordinator

### Relate (src-pipeline-COMP-38)

**Files:**
- `src/architecture_model/pipeline/relate.py`
- `src/architecture_model/pipeline/relate_types.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Synthesize, Context Gen, Decompose, Artifacts, Validate

### Report (src-pipeline-COMP-40)

**Files:**
- `src/architecture_model/pipeline/report.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Synthesize, Decompose

### Requirements Derive (src-pipeline-COMP-41)

**Files:**
- `src/architecture_model/pipeline/requirements_derive.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Cache, Emit, Synthesize

### Specify (src-pipeline-COMP-42)

**Files:**
- `src/architecture_model/pipeline/specify.py`
- `src/architecture_model/pipeline/specify_types.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Cache, Artifacts, Decompose, Coordinator

### Synthesize (src-pipeline-COMP-44)

**Files:**
- `src/architecture_model/pipeline/synthesize.py`
- `src/architecture_model/pipeline/synthesize_types.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Decompose

### Validate (src-pipeline-COMP-46)

**Files:**
- `src/architecture_model/pipeline/validate.py`
- `src/architecture_model/pipeline/validate_types.py`
**Downstream dependents (must re-test):** Artifacts, Coordinator, Cache, Emit, Synthesize, Context Gen, Decompose

## Known Constraints

*No constraint allocations defined.*
