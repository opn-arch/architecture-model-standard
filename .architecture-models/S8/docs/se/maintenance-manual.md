---
document: Maintenance Manual
system: architecture-model-standard/Extract
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: 2241722504ec
edition: 1
---

> **Model Completeness: F (15%)**
> Some sections may be empty due to missing model entities.
> - 1/1 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - No actors defined → conops stakeholder section empty
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: architecture-model-standard/Extract

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Extract (COMP-EXTRACT) | library | LYR-CORE | 6 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Extract | — | — | LOW |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Extract (COMP-EXTRACT)

**Files:**
- `src/architecture_model/extract/__init__.py`
- `src/architecture_model/extract/from_code.py`
- `src/architecture_model/extract/from_artifacts.py`
- `src/architecture_model/extract/route_detector.py`
- `src/architecture_model/extract/constraint_detector.py`
- `src/architecture_model/extract/table_parser.py`

## Known Constraints

*No constraint allocations defined.*
