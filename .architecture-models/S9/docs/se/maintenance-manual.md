---
document: Maintenance Manual
system: architecture-model-standard/Manifest
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: 9cd52927cc1c
edition: 1
---

> **Model Completeness: D (45%)**
> Some sections may be empty due to missing model entities.
> - 1/1 components have no behavioral specification
> - No requirements defined
> - No actors defined → conops stakeholder section empty
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: architecture-model-standard/Manifest

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Manifest (COMP-MANIFEST) | library | LYR-MANIFEST | 21 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Manifest | — | — | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Manifest (COMP-MANIFEST)

**Files:**
- `src/architecture_model/manifest/__init__.py`
- `src/architecture_model/manifest/types.py`
- `src/architecture_model/manifest/protocol.py`
- `src/architecture_model/manifest/scanner.py`
- `src/architecture_model/manifest/generator.py`
- `src/architecture_model/manifest/blocks.py`
- `src/architecture_model/manifest/body_hints.py`
- `src/architecture_model/manifest/interfaces.py`
- `src/architecture_model/manifest/grouping.py`
- `src/architecture_model/manifest/metrics.py`
- `src/architecture_model/manifest/recursive.py`
- `src/architecture_model/manifest/behavior.py`
- `src/architecture_model/manifest/call_graph.py`
- `src/architecture_model/manifest/chains.py`
- `src/architecture_model/manifest/display.py`
- `src/architecture_model/manifest/slicers.py`
- `src/architecture_model/manifest/test_analyzer.py`
- `src/architecture_model/manifest/scan_cache.py`
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/ts_scanner.py`
- *...and 1 more files*

## Known Constraints

| Component | Constraint | Type | Detail |
|-----------|-----------|------|--------|
| Manifest | No LLM in Core | technology | — |
