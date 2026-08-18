---
document: Maintenance Manual
system: Src (orchestration)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:58Z
generator_version: 0.3.0
model_hash: 1390e5be5ea9
edition: 14
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 13/13 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: Src (orchestration)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Auto Enrich (src-orchestration-COMP-1) | service | — | 1 | 0 | 0 |
| Behavior Decompose (src-orchestration-COMP-2) | service | — | 1 | 0 | 0 |
| Behavior Flows (src-orchestration-COMP-3) | service | — | 1 | 0 | 0 |
| Capability Inference (src-orchestration-COMP-4) | service | — | 1 | 0 | 0 |
| Compaction (src-orchestration-COMP-5) | service | — | 1 | 0 | 0 |
| Decompose (src-orchestration-COMP-6) | service | — | 1 | 0 | 0 |
| Deep Decompose (src-orchestration-COMP-7) | service | — | 1 | 0 | 0 |
| Enrich (src-orchestration-COMP-8) | service | — | 1 | 0 | 0 |
| Enrichment Context (src-orchestration-COMP-9) | service | — | 1 | 0 | 0 |
| Naming Context (src-orchestration-COMP-10) | service | — | 1 | 0 | 0 |
| Pipeline (src-orchestration-COMP-11) | service | — | 1 | 0 | 0 |
| Trigger Detection (src-orchestration-COMP-12) | service | — | 1 | 0 | 0 |
| Use Case Inference (src-orchestration-COMP-13) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Auto Enrich | — | Enrichment Context, Naming Context, Pipeline | MEDIUM |
| Behavior Decompose | — | Naming Context, Pipeline, Enrichment Context | MEDIUM |
| Behavior Flows | — | Enrichment Context, Naming Context, Pipeline | MEDIUM |
| Capability Inference | — | Pipeline, Enrichment Context, Naming Context | MEDIUM |
| Compaction | — | Enrichment Context, Naming Context, Pipeline | MEDIUM |
| Decompose | — | Enrichment Context, Naming Context, Pipeline | MEDIUM |
| Deep Decompose | — | Enrichment Context, Naming Context, Pipeline | MEDIUM |
| Enrich | — | Enrichment Context, Naming Context, Pipeline | MEDIUM |
| Enrichment Context | Behavior Flows, Enrich, Compaction, Auto Enrich, Pipeline, Deep Decompose, Naming Context, Decompose, Capability Inference, Trigger Detection, Use Case Inference, Behavior Decompose | Pipeline, Naming Context | MEDIUM |
| Naming Context | Behavior Decompose, Behavior Flows, Enrich, Compaction, Auto Enrich, Pipeline, Deep Decompose, Decompose, Enrichment Context, Capability Inference, Trigger Detection, Use Case Inference | Enrichment Context, Pipeline | MEDIUM |
| Pipeline | Enrichment Context, Capability Inference, Trigger Detection, Use Case Inference, Behavior Decompose, Behavior Flows, Enrich, Compaction, Auto Enrich, Deep Decompose, Naming Context, Decompose | Enrichment Context, Naming Context | MEDIUM |
| Trigger Detection | — | Pipeline, Enrichment Context, Naming Context | MEDIUM |
| Use Case Inference | — | Pipeline, Enrichment Context, Naming Context | MEDIUM |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Auto Enrich (src-orchestration-COMP-1)

**Files:**
- `src/architecture_model/orchestration/auto_enrich.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context, Pipeline

### Behavior Decompose (src-orchestration-COMP-2)

**Files:**
- `src/architecture_model/orchestration/behavior_decompose.py`
**Downstream dependents (must re-test):** Naming Context, Pipeline, Enrichment Context

### Behavior Flows (src-orchestration-COMP-3)

**Files:**
- `src/architecture_model/orchestration/behavior_flows.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context, Pipeline

### Capability Inference (src-orchestration-COMP-4)

**Files:**
- `src/architecture_model/orchestration/capability_inference.py`
**Downstream dependents (must re-test):** Pipeline, Enrichment Context, Naming Context

### Compaction (src-orchestration-COMP-5)

**Files:**
- `src/architecture_model/orchestration/compaction.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context, Pipeline

### Decompose (src-orchestration-COMP-6)

**Files:**
- `src/architecture_model/orchestration/decompose.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context, Pipeline

### Deep Decompose (src-orchestration-COMP-7)

**Files:**
- `src/architecture_model/orchestration/deep_decompose.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context, Pipeline

### Enrich (src-orchestration-COMP-8)

**Files:**
- `src/architecture_model/orchestration/enrich.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context, Pipeline

### Enrichment Context (src-orchestration-COMP-9)

**Files:**
- `src/architecture_model/orchestration/enrichment_context.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context

### Naming Context (src-orchestration-COMP-10)

**Files:**
- `src/architecture_model/orchestration/naming_context.py`
**Downstream dependents (must re-test):** Enrichment Context, Pipeline

### Pipeline (src-orchestration-COMP-11)

**Files:**
- `src/architecture_model/orchestration/pipeline.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context

### Trigger Detection (src-orchestration-COMP-12)

**Files:**
- `src/architecture_model/orchestration/trigger_detection.py`
**Downstream dependents (must re-test):** Pipeline, Enrichment Context, Naming Context

### Use Case Inference (src-orchestration-COMP-13)

**Files:**
- `src/architecture_model/orchestration/use_case_inference.py`
**Downstream dependents (must re-test):** Pipeline, Enrichment Context, Naming Context

## Known Constraints

*No constraint allocations defined.*
