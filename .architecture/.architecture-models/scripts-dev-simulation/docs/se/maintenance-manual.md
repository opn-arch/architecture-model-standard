---
document: Maintenance Manual
system: Scripts (dev_simulation)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:49Z
generator_version: 0.3.0
model_hash: c5cfd43f42c6
edition: 14
---

> **Model Completeness: F (27%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 10/10 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: Scripts (dev_simulation)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Checkout (scripts-dev-simulation-COMP-1) | service | — | 1 | 0 | 0 |
| Cohesion (scripts-dev-simulation-COMP-2) | service | — | 1 | 0 | 0 |
| Drift Tracker (scripts-dev-simulation-COMP-3) | service | — | 1 | 0 | 0 |
| Extractor (scripts-dev-simulation-COMP-4) | service | — | 1 | 0 | 0 |
| Llm Predictor (scripts-dev-simulation-COMP-5) | service | — | 1 | 0 | 0 |
| Regen Scorer (scripts-dev-simulation-COMP-6) | service | — | 1 | 0 | 0 |
| Report (scripts-dev-simulation-COMP-7) | service | — | 1 | 0 | 0 |
| Runner (scripts-dev-simulation-COMP-8) | service | — | 1 | 0 | 0 |
| Slice Evaluator (scripts-dev-simulation-COMP-9) | service | — | 1 | 0 | 0 |
| Infrastructure (scripts-dev-simulation-COMP-10) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Checkout | — | — | LOW |
| Cohesion | — | — | LOW |
| Drift Tracker | — | — | LOW |
| Extractor | — | — | LOW |
| Llm Predictor | — | — | LOW |
| Regen Scorer | — | — | LOW |
| Report | — | — | LOW |
| Runner | — | Infrastructure | LOW |
| Slice Evaluator | — | — | LOW |
| Infrastructure | Runner | — | LOW |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Checkout (scripts-dev-simulation-COMP-1)

**Files:**
- `scripts/dev_simulation/checkout.py`

### Cohesion (scripts-dev-simulation-COMP-2)

**Files:**
- `scripts/dev_simulation/cohesion.py`

### Drift Tracker (scripts-dev-simulation-COMP-3)

**Files:**
- `scripts/dev_simulation/drift_tracker.py`

### Extractor (scripts-dev-simulation-COMP-4)

**Files:**
- `scripts/dev_simulation/extractor.py`

### Llm Predictor (scripts-dev-simulation-COMP-5)

**Files:**
- `scripts/dev_simulation/llm_predictor.py`

### Regen Scorer (scripts-dev-simulation-COMP-6)

**Files:**
- `scripts/dev_simulation/regen_scorer.py`

### Report (scripts-dev-simulation-COMP-7)

**Files:**
- `scripts/dev_simulation/report.py`

### Runner (scripts-dev-simulation-COMP-8)

**Files:**
- `scripts/dev_simulation/runner.py`
**Downstream dependents (must re-test):** Infrastructure

### Slice Evaluator (scripts-dev-simulation-COMP-9)

**Files:**
- `scripts/dev_simulation/slice_evaluator.py`

### Infrastructure (scripts-dev-simulation-COMP-10)

**Files:**
- `scripts/dev_simulation/cli.py`

## Known Constraints

*No constraint allocations defined.*
