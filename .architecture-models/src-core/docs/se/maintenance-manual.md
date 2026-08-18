---
document: Maintenance Manual
system: Src (core)
system_id: SYS-unknown
generated_at: 2026-08-18T23:36:33Z
generator_version: 0.3.0
model_hash: 65254bb02f54
edition: 12
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
| Cluster | — | Representativeness, Decomposer, Source Block Assign, Regen Readiness, Confidence | HIGH |
| Completeness | — | Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness | HIGH |
| Compression | — | Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness | HIGH |
| Confidence | Parser, Regen Readiness, Slicer, Validator, Decomposer, Compression, Visualize, Completeness, Differ, Source Block Assign, Coverage, Representativeness, Corrections, Cluster, Merger | Representativeness, Regen Readiness, Source Block Assign, Decomposer | MEDIUM |
| Corrections | — | Representativeness, Decomposer, Confidence, Source Block Assign, Regen Readiness | HIGH |
| Coverage | Source Block Assign | Representativeness, Decomposer, Confidence, Source Block Assign, Regen Readiness | HIGH |
| Decomposer | Parser, Differ, Validator, Compression, Visualize, Completeness, Source Block Assign, Coverage, Cluster, Representativeness, Confidence, Corrections, Regen Readiness, Slicer, Merger | Source Block Assign, Regen Readiness, Confidence, Representativeness | MEDIUM |
| Differ | Source Block Assign | Decomposer, Source Block Assign, Regen Readiness, Confidence, Representativeness | HIGH |
| Merger | Source Block Assign | Source Block Assign, Regen Readiness, Representativeness, Decomposer, Confidence | HIGH |
| Parser | Source Block Assign | Decomposer, Confidence, Source Block Assign, Representativeness, Regen Readiness | HIGH |
| Regen Readiness | Slicer, Merger, Decomposer, Visualize, Differ, Validator, Compression, Completeness, Source Block Assign, Confidence, Coverage, Cluster, Representativeness, Parser, Corrections | Source Block Assign, Confidence, Representativeness, Decomposer | MEDIUM |
| Representativeness | Source Block Assign, Confidence, Coverage, Cluster, Corrections, Regen Readiness, Slicer, Merger, Parser, Decomposer, Visualize, Differ, Validator, Compression, Completeness | Decomposer, Confidence, Source Block Assign, Regen Readiness | MEDIUM |
| Slicer | Source Block Assign | Source Block Assign, Regen Readiness, Confidence, Representativeness, Decomposer | HIGH |
| Source Block Assign | Regen Readiness, Slicer, Merger, Parser, Decomposer, Visualize, Differ, Validator, Compression, Completeness, Confidence, Coverage, Cluster, Representativeness, Corrections | Representativeness, Coverage, Validator, Decomposer, Confidence, Differ, Regen Readiness, Merger, Parser, Slicer | HIGH |
| Validator | Source Block Assign | Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness | HIGH |
| Visualize | — | Source Block Assign, Regen Readiness, Decomposer, Confidence, Representativeness | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Cluster (src-core-COMP-15)

**Files:**
- `src/architecture_model/core/cluster.py`
**Downstream dependents (must re-test):** Representativeness, Decomposer, Source Block Assign, Regen Readiness, Confidence

### Completeness (src-core-COMP-16)

**Files:**
- `src/architecture_model/core/completeness.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness

### Compression (src-core-COMP-17)

**Files:**
- `src/architecture_model/core/compression.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness

### Confidence (src-core-COMP-18)

**Files:**
- `src/architecture_model/core/confidence.py`
**Downstream dependents (must re-test):** Representativeness, Regen Readiness, Source Block Assign, Decomposer

### Corrections (src-core-COMP-19)

**Files:**
- `src/architecture_model/core/corrections.py`
**Downstream dependents (must re-test):** Representativeness, Decomposer, Confidence, Source Block Assign, Regen Readiness

### Coverage (src-core-COMP-20)

**Files:**
- `src/architecture_model/core/coverage.py`
**Downstream dependents (must re-test):** Representativeness, Decomposer, Confidence, Source Block Assign, Regen Readiness

### Decomposer (src-core-COMP-21)

**Files:**
- `src/architecture_model/core/decomposer.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Confidence, Representativeness

### Differ (src-core-COMP-22)

**Files:**
- `src/architecture_model/core/differ.py`
**Downstream dependents (must re-test):** Decomposer, Source Block Assign, Regen Readiness, Confidence, Representativeness

### Merger (src-core-COMP-23)

**Files:**
- `src/architecture_model/core/merger.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Representativeness, Decomposer, Confidence

### Parser (src-core-COMP-24)

**Files:**
- `src/architecture_model/core/parser.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Representativeness, Regen Readiness

### Regen Readiness (src-core-COMP-25)

**Files:**
- `src/architecture_model/core/regen_readiness.py`
**Downstream dependents (must re-test):** Source Block Assign, Confidence, Representativeness, Decomposer

### Representativeness (src-core-COMP-26)

**Files:**
- `src/architecture_model/core/representativeness.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Regen Readiness

### Slicer (src-core-COMP-27)

**Files:**
- `src/architecture_model/core/slicer.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Confidence, Representativeness, Decomposer

### Source Block Assign (src-core-COMP-28)

**Files:**
- `src/architecture_model/core/source_block_assign.py`
- `src/architecture_model/core/source_block_quality.py`
- `src/architecture_model/core/types.py`
**Downstream dependents (must re-test):** Representativeness, Coverage, Validator, Decomposer, Confidence, Differ, Regen Readiness, Merger, Parser, Slicer

### Validator (src-core-COMP-30)

**Files:**
- `src/architecture_model/core/validator.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness

### Visualize (src-core-COMP-31)

**Files:**
- `src/architecture_model/core/visualize.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Decomposer, Confidence, Representativeness

## Known Constraints

*No constraint allocations defined.*
