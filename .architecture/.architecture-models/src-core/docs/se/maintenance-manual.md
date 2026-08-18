---
document: Maintenance Manual
system: Src (core)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:55Z
generator_version: 0.3.0
model_hash: 65254bb02f54
edition: 28
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 16/16 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: Src (core)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Cluster (src-core-COMP-15) | service | — | 1 | 0 | 0 |
| Completeness (src-core-COMP-16) | service | — | 1 | 0 | 0 |
| Compression (src-core-COMP-17) | service | — | 1 | 0 | 0 |
| Confidence (src-core-COMP-18) | service | — | 1 | 0 | 0 |
| Corrections (src-core-COMP-19) | service | — | 1 | 0 | 0 |
| Coverage (src-core-COMP-20) | service | — | 1 | 0 | 0 |
| Decomposer (src-core-COMP-21) | service | — | 1 | 0 | 0 |
| Differ (src-core-COMP-22) | service | — | 1 | 0 | 0 |
| Merger (src-core-COMP-23) | service | — | 1 | 0 | 0 |
| Parser (src-core-COMP-24) | service | — | 1 | 0 | 0 |
| Regen Readiness (src-core-COMP-25) | service | — | 1 | 0 | 0 |
| Representativeness (src-core-COMP-26) | service | — | 1 | 0 | 0 |
| Slicer (src-core-COMP-27) | service | — | 1 | 0 | 0 |
| Source Block Assign (src-core-COMP-28) | service | — | 3 | 0 | 0 |
| Validator (src-core-COMP-30) | service | — | 1 | 0 | 0 |
| Visualize (src-core-COMP-31) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Cluster | — | Confidence, Decomposer, Source Block Assign, Regen Readiness, Representativeness | HIGH |
| Completeness | — | Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign | HIGH |
| Compression | — | Source Block Assign, Regen Readiness, Representativeness, Confidence, Decomposer | HIGH |
| Confidence | Decomposer, Cluster, Merger, Coverage, Slicer, Source Block Assign, Compression, Representativeness, Validator, Visualize, Parser, Completeness, Regen Readiness, Corrections, Differ | Decomposer, Source Block Assign, Regen Readiness, Representativeness | MEDIUM |
| Corrections | — | Source Block Assign, Representativeness, Regen Readiness, Confidence, Decomposer | HIGH |
| Coverage | Source Block Assign | Regen Readiness, Confidence, Decomposer, Source Block Assign, Representativeness | HIGH |
| Decomposer | Differ, Cluster, Coverage, Confidence, Merger, Slicer, Source Block Assign, Compression, Representativeness, Validator, Visualize, Parser, Completeness, Regen Readiness, Corrections | Confidence, Source Block Assign, Representativeness, Regen Readiness | MEDIUM |
| Differ | Source Block Assign | Decomposer, Source Block Assign, Representativeness, Regen Readiness, Confidence | HIGH |
| Merger | Source Block Assign | Confidence, Decomposer, Source Block Assign, Representativeness, Regen Readiness | HIGH |
| Parser | Source Block Assign | Representativeness, Regen Readiness, Confidence, Decomposer, Source Block Assign | HIGH |
| Regen Readiness | Slicer, Coverage, Compression, Validator, Parser, Completeness, Corrections, Source Block Assign, Differ, Representativeness, Visualize, Decomposer, Cluster, Confidence, Merger | Source Block Assign, Representativeness, Confidence, Decomposer | MEDIUM |
| Representativeness | Validator, Parser, Corrections, Slicer, Source Block Assign, Differ, Compression, Visualize, Completeness, Decomposer, Regen Readiness, Cluster, Merger, Coverage, Confidence | Source Block Assign, Regen Readiness, Confidence, Decomposer | MEDIUM |
| Slicer | Source Block Assign | Source Block Assign, Regen Readiness, Representativeness, Confidence, Decomposer | HIGH |
| Source Block Assign | Corrections, Slicer, Differ, Compression, Representativeness, Visualize, Decomposer, Regen Readiness, Cluster, Confidence, Merger, Coverage, Validator, Completeness, Parser | Representativeness, Parser, Regen Readiness, Merger, Differ, Slicer, Confidence, Coverage, Decomposer, Validator | HIGH |
| Validator | Source Block Assign | Representativeness, Regen Readiness, Confidence, Decomposer, Source Block Assign | HIGH |
| Visualize | — | Source Block Assign, Representativeness, Regen Readiness, Confidence, Decomposer | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Cluster (src-core-COMP-15)

**Files:**
- `src/architecture_model/core/cluster.py`
**Downstream dependents (must re-test):** Confidence, Decomposer, Source Block Assign, Regen Readiness, Representativeness

### Completeness (src-core-COMP-16)

**Files:**
- `src/architecture_model/core/completeness.py`
**Downstream dependents (must re-test):** Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign

### Compression (src-core-COMP-17)

**Files:**
- `src/architecture_model/core/compression.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Representativeness, Confidence, Decomposer

### Confidence (src-core-COMP-18)

**Files:**
- `src/architecture_model/core/confidence.py`
**Downstream dependents (must re-test):** Decomposer, Source Block Assign, Regen Readiness, Representativeness

### Corrections (src-core-COMP-19)

**Files:**
- `src/architecture_model/core/corrections.py`
**Downstream dependents (must re-test):** Source Block Assign, Representativeness, Regen Readiness, Confidence, Decomposer

### Coverage (src-core-COMP-20)

**Files:**
- `src/architecture_model/core/coverage.py`
**Downstream dependents (must re-test):** Regen Readiness, Confidence, Decomposer, Source Block Assign, Representativeness

### Decomposer (src-core-COMP-21)

**Files:**
- `src/architecture_model/core/decomposer.py`
**Downstream dependents (must re-test):** Confidence, Source Block Assign, Representativeness, Regen Readiness

### Differ (src-core-COMP-22)

**Files:**
- `src/architecture_model/core/differ.py`
**Downstream dependents (must re-test):** Decomposer, Source Block Assign, Representativeness, Regen Readiness, Confidence

### Merger (src-core-COMP-23)

**Files:**
- `src/architecture_model/core/merger.py`
**Downstream dependents (must re-test):** Confidence, Decomposer, Source Block Assign, Representativeness, Regen Readiness

### Parser (src-core-COMP-24)

**Files:**
- `src/architecture_model/core/parser.py`
**Downstream dependents (must re-test):** Representativeness, Regen Readiness, Confidence, Decomposer, Source Block Assign

### Regen Readiness (src-core-COMP-25)

**Files:**
- `src/architecture_model/core/regen_readiness.py`
**Downstream dependents (must re-test):** Source Block Assign, Representativeness, Confidence, Decomposer

### Representativeness (src-core-COMP-26)

**Files:**
- `src/architecture_model/core/representativeness.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Confidence, Decomposer

### Slicer (src-core-COMP-27)

**Files:**
- `src/architecture_model/core/slicer.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Representativeness, Confidence, Decomposer

### Source Block Assign (src-core-COMP-28)

**Files:**
- `src/architecture_model/core/source_block_assign.py`
- `src/architecture_model/core/source_block_quality.py`
- `src/architecture_model/core/types.py`
**Downstream dependents (must re-test):** Representativeness, Parser, Regen Readiness, Merger, Differ, Slicer, Confidence, Coverage, Decomposer, Validator

### Validator (src-core-COMP-30)

**Files:**
- `src/architecture_model/core/validator.py`
**Downstream dependents (must re-test):** Representativeness, Regen Readiness, Confidence, Decomposer, Source Block Assign

### Visualize (src-core-COMP-31)

**Files:**
- `src/architecture_model/core/visualize.py`
**Downstream dependents (must re-test):** Source Block Assign, Representativeness, Regen Readiness, Confidence, Decomposer

## Known Constraints

*No constraint allocations defined.*
