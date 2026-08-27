---
document: Functional Analysis
system: architecture-model-standard/Pipeline
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: 18454899275b
edition: 1
---

# Functional Analysis: architecture-model-standard/Pipeline

## Capability Inventory

| ID | Capability | Priority | Status | Description | Intent |
|----|-----------|----------|--------|-------------|--------|
| CAP-PIPELINE | Modular Extraction Pipeline | medium | ACTIVE | 7-stage deterministic pipeline (observe, infer, allocate, relate, specify, contract, validate) | Enable fully automated architecture model extraction from arbitrary codebases without manual configuration or LLM calls in the core path. |
| CAP-REGEN | Regen Readiness Scoring | medium | ACTIVE | Predict regeneration success from enriched model data | Provide a quantitative signal indicating whether an enriched model contains enough detail (signatures, body_hints, constants, test_contracts) to regenerate passing code. |

## Measures of Effectiveness

| Capability | MOE |
|---|---|
| Modular Extraction Pipeline (CAP-PIPELINE) | All 7 stages complete without error on repos up to 500 files |
| Modular Extraction Pipeline (CAP-PIPELINE) | Extracted models score >= 90/100 on structural validation |
| Modular Extraction Pipeline (CAP-PIPELINE) | Full pipeline completes in <5s for repos under 100 files |
| Regen Readiness Scoring (CAP-REGEN) | Regen score correlates with actual blind-regeneration fidelity (r > 0.7) |
| Regen Readiness Scoring (CAP-REGEN) | Scores distinguish A-grade (>90% fidelity) from D-grade (<60%) subsystems |
| Regen Readiness Scoring (CAP-REGEN) | Score computation completes in <100ms per subsystem |

## Functional Decomposition

```mermaid
graph TD
    CAP-PIPELINE["Modular Extraction Pipeline"]
    CAP-REGEN["Regen Readiness Scoring"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Modular Extraction Pipeline | Pipeline (COMP-PIPELINE) | library |
| Regen Readiness Scoring | Pipeline (COMP-PIPELINE) | library |

### Design Trade-offs

**Pipeline** (COMP-PIPELINE):
- Determinism vs. accuracy — no LLM calls means heuristic-based inference may miss nuanced patterns
- Monolithic component vs. per-stage components — all 22 files in one component simplifies dependency tracking but reduces granularity
- Threshold-based splitting/merging — fixed constants (MAX_COMPONENT_FILES=12, MIN_COMPONENT_FILES=2) work for most repos but may misfit extreme cases

## Behavioral Coverage

Total behaviors: 3

**Untraced behaviors:** 2
- write_artifacts (BEH-1)
- generate_context (BEH-2)
