---
document: Maintenance Manual
system: Src (pipeline)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:53Z
generator_version: 0.3.0
model_hash: ccd998005d8e
edition: 14
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
| Allocate | Protocol, Observe, Infer, Corrections | Decompose, Emit, Synthesize, Coordinator, Context Gen, Relate, Artifacts, Specify, Validate, Cache, Contract | HIGH |
| Artifacts | Contract, Protocol, Observe, Validate, Specify, Infer, Allocate, Relate | Synthesize, Coordinator, Cache, Decompose, Emit | HIGH |
| Cache | Relate, Synthesize, Report, Protocol, Coordinator, Context Gen, Artifacts, Validate, Regen Score, Observe, Infer, Global Learning, Corrections, Emit, Requirements Derive, Lessons, Specify, Allocate, Contract, Decompose | Decompose, Emit, Synthesize, Coordinator | MEDIUM |
| Context Gen | Protocol, Validate, Observe, Infer, Allocate, Relate | Decompose, Coordinator, Emit, Synthesize, Cache | HIGH |
| Contract | Protocol, Observe, Allocate | Artifacts, Decompose, Emit, Synthesize, Coordinator, Cache | HIGH |
| Coordinator | Synthesize, Context Gen, Artifacts, Report, Regen Score, Observe, Global Learning, Emit, Validate, Specify, Infer, Corrections, Allocate, Decompose, Cache, Requirements Derive, Lessons, Relate, Contract, Protocol | Emit, Synthesize, Cache, Decompose | MEDIUM |
| Corrections | — | Decompose, Emit, Synthesize, Coordinator, Cache, Allocate, Infer | HIGH |
| Decompose | Emit, Context Gen, Validate, Observe, Infer, Global Learning, Corrections, Allocate, Cache, Requirements Derive, Lessons, Relate, Specify, Contract, Protocol, Synthesize, Artifacts, Report, Regen Score, Coordinator | Emit, Coordinator, Synthesize, Cache | MEDIUM |
| Emit | Regen Score, Coordinator, Observe, Context Gen, Validate, Infer, Global Learning, Corrections, Allocate, Decompose, Cache, Requirements Derive, Lessons, Relate, Specify, Contract, Protocol, Synthesize, Artifacts, Report | Decompose, Coordinator, Synthesize, Cache | MEDIUM |
| Global Learning | Protocol | Decompose, Coordinator, Emit, Synthesize, Cache | HIGH |
| Infer | Protocol, Observe, Corrections | Decompose, Emit, Allocate, Synthesize, Validate, Coordinator, Cache, Context Gen, Relate, Artifacts | HIGH |
| Lessons | Protocol | Decompose, Emit, Synthesize, Coordinator, Cache | HIGH |
| Observe | Protocol | Emit, Decompose, Coordinator, Allocate, Relate, Artifacts, Infer, Specify, Cache, Context Gen, Contract, Synthesize | HIGH |
| Protocol | — | Context Gen, Global Learning, Allocate, Regen Score, Observe, Relate, Artifacts, Infer, Specify, Cache, Contract, Lessons, Report, Decompose, Emit, Synthesize, Validate, Coordinator | HIGH |
| Regen Score | Protocol | Emit, Synthesize, Coordinator, Cache, Decompose | HIGH |
| Relate | Protocol, Observe, Infer, Allocate | Cache, Decompose, Emit, Coordinator, Context Gen, Artifacts, Synthesize, Validate | HIGH |
| Report | Protocol | Synthesize, Coordinator, Cache, Decompose, Emit | HIGH |
| Requirements Derive | — | Decompose, Emit, Synthesize, Coordinator, Cache | HIGH |
| Specify | Protocol, Observe, Allocate | Decompose, Coordinator, Emit, Artifacts, Synthesize, Cache | HIGH |
| Synthesize | Artifacts, Report, Regen Score, Coordinator, Context Gen, Validate, Infer, Global Learning, Corrections, Allocate, Cache, Emit, Requirements Derive, Lessons, Specify, Contract, Decompose, Protocol, Relate, Observe | Coordinator, Cache, Decompose, Emit | MEDIUM |
| Validate | Infer, Allocate, Protocol, Relate | Decompose, Emit, Synthesize, Coordinator, Cache, Context Gen, Artifacts | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Allocate (src-pipeline-COMP-16)

**Files:**
- `src/architecture_model/pipeline/allocate.py`
- `src/architecture_model/pipeline/allocate_types.py`
**Downstream dependents (must re-test):** Decompose, Emit, Synthesize, Coordinator, Context Gen, Relate, Artifacts, Specify, Validate, Cache, Contract

### Artifacts (src-pipeline-COMP-18)

**Files:**
- `src/architecture_model/pipeline/artifacts.py`
**Downstream dependents (must re-test):** Synthesize, Coordinator, Cache, Decompose, Emit

### Cache (src-pipeline-COMP-19)

**Files:**
- `src/architecture_model/pipeline/cache.py`
**Downstream dependents (must re-test):** Decompose, Emit, Synthesize, Coordinator

### Context Gen (src-pipeline-COMP-20)

**Files:**
- `src/architecture_model/pipeline/context_gen.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Emit, Synthesize, Cache

### Contract (src-pipeline-COMP-21)

**Files:**
- `src/architecture_model/pipeline/contract.py`
- `src/architecture_model/pipeline/contract_types.py`
**Downstream dependents (must re-test):** Artifacts, Decompose, Emit, Synthesize, Coordinator, Cache

### Coordinator (src-pipeline-COMP-23)

**Files:**
- `src/architecture_model/pipeline/coordinator.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Cache, Decompose

### Corrections (src-pipeline-COMP-24)

**Files:**
- `src/architecture_model/pipeline/corrections.py`
**Downstream dependents (must re-test):** Decompose, Emit, Synthesize, Coordinator, Cache, Allocate, Infer

### Decompose (src-pipeline-COMP-25)

**Files:**
- `src/architecture_model/pipeline/__init__.py`
- `src/architecture_model/pipeline/decompose.py`
- `src/architecture_model/pipeline/decompose_types.py`
**Downstream dependents (must re-test):** Emit, Coordinator, Synthesize, Cache

### Emit (src-pipeline-COMP-27)

**Files:**
- `src/architecture_model/pipeline/emit.py`
- `src/architecture_model/pipeline/emit_types.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Synthesize, Cache

### Global Learning (src-pipeline-COMP-29)

**Files:**
- `src/architecture_model/pipeline/global_learning.py`
- `src/architecture_model/pipeline/learning.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Emit, Synthesize, Cache

### Infer (src-pipeline-COMP-30)

**Files:**
- `src/architecture_model/pipeline/infer.py`
- `src/architecture_model/pipeline/infer_types.py`
**Downstream dependents (must re-test):** Decompose, Emit, Allocate, Synthesize, Validate, Coordinator, Cache, Context Gen, Relate, Artifacts

### Lessons (src-pipeline-COMP-33)

**Files:**
- `src/architecture_model/pipeline/lessons.py`
**Downstream dependents (must re-test):** Decompose, Emit, Synthesize, Coordinator, Cache

### Observe (src-pipeline-COMP-34)

**Files:**
- `src/architecture_model/pipeline/observe.py`
- `src/architecture_model/pipeline/observe_types.py`
**Downstream dependents (must re-test):** Emit, Decompose, Coordinator, Allocate, Relate, Artifacts, Infer, Specify, Cache, Context Gen, Contract, Synthesize

### Protocol (src-pipeline-COMP-36)

**Files:**
- `src/architecture_model/pipeline/protocol.py`
**Downstream dependents (must re-test):** Context Gen, Global Learning, Allocate, Regen Score, Observe, Relate, Artifacts, Infer, Specify, Cache, Contract, Lessons, Report, Decompose, Emit, Synthesize, Validate, Coordinator

### Regen Score (src-pipeline-COMP-37)

**Files:**
- `src/architecture_model/pipeline/regen_score.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Coordinator, Cache, Decompose

### Relate (src-pipeline-COMP-38)

**Files:**
- `src/architecture_model/pipeline/relate.py`
- `src/architecture_model/pipeline/relate_types.py`
**Downstream dependents (must re-test):** Cache, Decompose, Emit, Coordinator, Context Gen, Artifacts, Synthesize, Validate

### Report (src-pipeline-COMP-40)

**Files:**
- `src/architecture_model/pipeline/report.py`
**Downstream dependents (must re-test):** Synthesize, Coordinator, Cache, Decompose, Emit

### Requirements Derive (src-pipeline-COMP-41)

**Files:**
- `src/architecture_model/pipeline/requirements_derive.py`
**Downstream dependents (must re-test):** Decompose, Emit, Synthesize, Coordinator, Cache

### Specify (src-pipeline-COMP-42)

**Files:**
- `src/architecture_model/pipeline/specify.py`
- `src/architecture_model/pipeline/specify_types.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Emit, Artifacts, Synthesize, Cache

### Synthesize (src-pipeline-COMP-44)

**Files:**
- `src/architecture_model/pipeline/synthesize.py`
- `src/architecture_model/pipeline/synthesize_types.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Decompose, Emit

### Validate (src-pipeline-COMP-46)

**Files:**
- `src/architecture_model/pipeline/validate.py`
- `src/architecture_model/pipeline/validate_types.py`
**Downstream dependents (must re-test):** Decompose, Emit, Synthesize, Coordinator, Cache, Context Gen, Artifacts

## Known Constraints

*No constraint allocations defined.*
