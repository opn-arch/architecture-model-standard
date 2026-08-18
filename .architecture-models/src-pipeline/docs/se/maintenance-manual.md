---
document: Maintenance Manual
system: Src (pipeline)
system_id: SYS-unknown
generated_at: 2026-08-18T20:06:05Z
generator_version: 0.3.0
model_hash: ccd998005d8e
edition: 4
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
| Allocate | Infer, Protocol, Corrections, Observe | Relate, Contract, Context Gen, Emit, Coordinator, Synthesize, Specify, Validate, Decompose, Artifacts, Cache | HIGH |
| Artifacts | Validate, Specify, Contract, Relate, Infer, Allocate, Observe, Protocol | Decompose, Cache, Emit, Synthesize, Coordinator | HIGH |
| Cache | Lessons, Report, Specify, Validate, Decompose, Requirements Derive, Artifacts, Coordinator, Global Learning, Contract, Context Gen, Emit, Synthesize, Protocol, Relate, Infer, Allocate, Observe, Corrections, Regen Score | Emit, Synthesize, Coordinator, Decompose | MEDIUM |
| Context Gen | Infer, Allocate, Observe, Protocol, Validate, Relate | Coordinator, Decompose, Cache, Emit, Synthesize | HIGH |
| Contract | Allocate, Observe, Protocol | Decompose, Artifacts, Cache, Emit, Coordinator, Synthesize | HIGH |
| Coordinator | Context Gen, Synthesize, Protocol, Relate, Corrections, Allocate, Observe, Validate, Regen Score, Lessons, Cache, Report, Specify, Global Learning, Contract, Decompose, Requirements Derive, Artifacts, Emit, Infer | Decompose, Cache, Emit, Synthesize | MEDIUM |
| Corrections | — | Coordinator, Emit, Synthesize, Allocate, Decompose, Cache, Infer | HIGH |
| Decompose | Lessons, Report, Specify, Global Learning, Contract, Requirements Derive, Artifacts, Coordinator, Context Gen, Emit, Relate, Infer, Synthesize, Protocol, Corrections, Allocate, Observe, Cache, Validate, Regen Score | Cache, Emit, Coordinator, Synthesize | MEDIUM |
| Emit | Allocate, Observe, Lessons, Cache, Corrections, Report, Validate, Regen Score, Artifacts, Specify, Global Learning, Contract, Decompose, Requirements Derive, Coordinator, Context Gen, Synthesize, Relate, Infer, Protocol | Decompose, Cache, Coordinator, Synthesize | MEDIUM |
| Global Learning | Protocol | Decompose, Cache, Emit, Coordinator, Synthesize | HIGH |
| Infer | Observe, Protocol, Corrections | Context Gen, Synthesize, Allocate, Validate, Decompose, Artifacts, Cache, Relate, Emit, Coordinator | HIGH |
| Lessons | Protocol | Decompose, Cache, Emit, Coordinator, Synthesize | HIGH |
| Observe | Protocol | Infer, Relate, Contract, Context Gen, Emit, Coordinator, Synthesize, Specify, Allocate, Decompose, Artifacts, Cache | HIGH |
| Protocol | — | Lessons, Regen Score, Coordinator, Context Gen, Synthesize, Specify, Allocate, Observe, Global Learning, Report, Validate, Decompose, Cache, Artifacts, Infer, Relate, Contract, Emit | HIGH |
| Regen Score | Protocol | Emit, Coordinator, Synthesize, Decompose, Cache | HIGH |
| Relate | Allocate, Observe, Infer, Protocol | Coordinator, Validate, Decompose, Artifacts, Cache, Emit, Context Gen, Synthesize | HIGH |
| Report | Protocol | Decompose, Cache, Emit, Synthesize, Coordinator | HIGH |
| Requirements Derive | — | Decompose, Cache, Emit, Coordinator, Synthesize | HIGH |
| Specify | Protocol, Allocate, Observe | Decompose, Cache, Artifacts, Emit, Coordinator, Synthesize | HIGH |
| Synthesize | Infer, Protocol, Corrections, Allocate, Observe, Cache, Report, Validate, Regen Score, Artifacts, Lessons, Specify, Global Learning, Contract, Decompose, Requirements Derive, Coordinator, Context Gen, Emit, Relate | Coordinator, Decompose, Cache, Emit | MEDIUM |
| Validate | Relate, Infer, Allocate, Protocol | Artifacts, Cache, Emit, Coordinator, Context Gen, Synthesize, Decompose | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Allocate (src-pipeline-COMP-16)

**Files:**
- `src/architecture_model/pipeline/allocate.py`
- `src/architecture_model/pipeline/allocate_types.py`
**Downstream dependents (must re-test):** Relate, Contract, Context Gen, Emit, Coordinator, Synthesize, Specify, Validate, Decompose, Artifacts, Cache

### Artifacts (src-pipeline-COMP-18)

**Files:**
- `src/architecture_model/pipeline/artifacts.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Synthesize, Coordinator

### Cache (src-pipeline-COMP-19)

**Files:**
- `src/architecture_model/pipeline/cache.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Coordinator, Decompose

### Context Gen (src-pipeline-COMP-20)

**Files:**
- `src/architecture_model/pipeline/context_gen.py`
**Downstream dependents (must re-test):** Coordinator, Decompose, Cache, Emit, Synthesize

### Contract (src-pipeline-COMP-21)

**Files:**
- `src/architecture_model/pipeline/contract.py`
- `src/architecture_model/pipeline/contract_types.py`
**Downstream dependents (must re-test):** Decompose, Artifacts, Cache, Emit, Coordinator, Synthesize

### Coordinator (src-pipeline-COMP-23)

**Files:**
- `src/architecture_model/pipeline/coordinator.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Synthesize

### Corrections (src-pipeline-COMP-24)

**Files:**
- `src/architecture_model/pipeline/corrections.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Synthesize, Allocate, Decompose, Cache, Infer

### Decompose (src-pipeline-COMP-25)

**Files:**
- `src/architecture_model/pipeline/__init__.py`
- `src/architecture_model/pipeline/decompose.py`
- `src/architecture_model/pipeline/decompose_types.py`
**Downstream dependents (must re-test):** Cache, Emit, Coordinator, Synthesize

### Emit (src-pipeline-COMP-27)

**Files:**
- `src/architecture_model/pipeline/emit.py`
- `src/architecture_model/pipeline/emit_types.py`
**Downstream dependents (must re-test):** Decompose, Cache, Coordinator, Synthesize

### Global Learning (src-pipeline-COMP-29)

**Files:**
- `src/architecture_model/pipeline/global_learning.py`
- `src/architecture_model/pipeline/learning.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Coordinator, Synthesize

### Infer (src-pipeline-COMP-30)

**Files:**
- `src/architecture_model/pipeline/infer.py`
- `src/architecture_model/pipeline/infer_types.py`
**Downstream dependents (must re-test):** Context Gen, Synthesize, Allocate, Validate, Decompose, Artifacts, Cache, Relate, Emit, Coordinator

### Lessons (src-pipeline-COMP-33)

**Files:**
- `src/architecture_model/pipeline/lessons.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Coordinator, Synthesize

### Observe (src-pipeline-COMP-34)

**Files:**
- `src/architecture_model/pipeline/observe.py`
- `src/architecture_model/pipeline/observe_types.py`
**Downstream dependents (must re-test):** Infer, Relate, Contract, Context Gen, Emit, Coordinator, Synthesize, Specify, Allocate, Decompose, Artifacts, Cache

### Protocol (src-pipeline-COMP-36)

**Files:**
- `src/architecture_model/pipeline/protocol.py`
**Downstream dependents (must re-test):** Lessons, Regen Score, Coordinator, Context Gen, Synthesize, Specify, Allocate, Observe, Global Learning, Report, Validate, Decompose, Cache, Artifacts, Infer, Relate, Contract, Emit

### Regen Score (src-pipeline-COMP-37)

**Files:**
- `src/architecture_model/pipeline/regen_score.py`
**Downstream dependents (must re-test):** Emit, Coordinator, Synthesize, Decompose, Cache

### Relate (src-pipeline-COMP-38)

**Files:**
- `src/architecture_model/pipeline/relate.py`
- `src/architecture_model/pipeline/relate_types.py`
**Downstream dependents (must re-test):** Coordinator, Validate, Decompose, Artifacts, Cache, Emit, Context Gen, Synthesize

### Report (src-pipeline-COMP-40)

**Files:**
- `src/architecture_model/pipeline/report.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Synthesize, Coordinator

### Requirements Derive (src-pipeline-COMP-41)

**Files:**
- `src/architecture_model/pipeline/requirements_derive.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Coordinator, Synthesize

### Specify (src-pipeline-COMP-42)

**Files:**
- `src/architecture_model/pipeline/specify.py`
- `src/architecture_model/pipeline/specify_types.py`
**Downstream dependents (must re-test):** Decompose, Cache, Artifacts, Emit, Coordinator, Synthesize

### Synthesize (src-pipeline-COMP-44)

**Files:**
- `src/architecture_model/pipeline/synthesize.py`
- `src/architecture_model/pipeline/synthesize_types.py`
**Downstream dependents (must re-test):** Coordinator, Decompose, Cache, Emit

### Validate (src-pipeline-COMP-46)

**Files:**
- `src/architecture_model/pipeline/validate.py`
- `src/architecture_model/pipeline/validate_types.py`
**Downstream dependents (must re-test):** Artifacts, Cache, Emit, Coordinator, Context Gen, Synthesize, Decompose

## Known Constraints

*No constraint allocations defined.*
