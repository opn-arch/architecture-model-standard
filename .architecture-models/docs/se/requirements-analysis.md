---
document: Requirements Analysis
system: architecture-model-standard
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:21Z
generator_version: 0.3.0
model_hash: 08abc716587d
edition: 9
---

# Requirements Analysis: architecture-model-standard

## Constraint Inventory

| ID | Constraint | Type | Metric | Threshold | Rationale |
|----|-----------|------|--------|-----------|-----------|
| CON-1 | Python >=3.11 | technology | — | — | — |
| CON-2 | CI/CD: GitHub Actions | technology | — | — | — |

## Capability-Derived Requirements

*No explicit requirements on capabilities.*

## Requirements Traceability

| From | Relationship | To | Description |
|------|-------------|-----|-------------|
| Validation | satisfies | REQ-1 | Validator enforces score >= 80 |
| Validation | satisfies | REQ-2 | Validator checks produce zero errors on valid models |
| Validation | satisfies | REQ-3 | Hierarchy validator checks bidirectional consistency |
| Observation Stages | satisfies | REQ-4 | Infer stage produces all entity types |
| Allocation & Relation Stages | satisfies | REQ-5 | Relate stage produces typed relationships |
| Pipeline Coordination | satisfies | REQ-6 | Pipeline coordinator runs deterministically |
| Pipeline Coordination | satisfies | REQ-7 | Stage caching enables independent runs |
| Scanners | satisfies | REQ-8 | Scanners cover all Python files |
| Graph & Analysis | satisfies | REQ-9 | Graph analysis resolves imports to edges |
| Scanners | satisfies | REQ-10 | Multi-scanner supports Python/TS/Kotlin |
| Core Doc Generators | satisfies | REQ-11 | Template-based generators run in <1s |
| SE Document Suite | satisfies | REQ-12 | SE suite generates all required doc types |
| SE Document Suite | satisfies | REQ-13 | SE generator preserves user edits on regen |
| Authoring | satisfies | REQ-14 | Authoring parser handles markdown requirements |
| Quality Metrics | satisfies | REQ-15 | Regen readiness scoring |
| Quality Metrics | satisfies | REQ-16 | Per-component readiness with blockers |
| Specification & Contract Stages | satisfies | REQ-17 | Validate stage ensures test preservation |
| Enrichment | satisfies | REQ-18 | Enrichment applies behavior cap at 40 |
| Grouping & Generation | satisfies | REQ-19 | Grouping optimizes boundary coherence |
| Model Operations | satisfies | REQ-20 | Slicer enforces token budget |
| Documentation | satisfies | REQ-21 | All docs are self-documenting markdown |
| Type System | satisfies | REQ-22 | Type system supports parent_id/children |
| Pipeline Coordination | satisfies | REQ-23 | Coordinator catches stage failures gracefully |
| Observation Stages | satisfies | REQ-24 | Infer stage surfaces uncertainties |
| Pipeline | satisfies | REQ-25 | Pipeline completes large repos without LLM |
| CLI | satisfies | REQ-26 | CLI exposes all operations for MCP wrapping |
| Parser & Persistence | satisfies | REQ-27 | Parser ensures round-trip fidelity |
| Parser & Persistence | satisfies | REQ-28 | Parser handles old schema versions |
| Export | satisfies | REQ-29 | Export includes all artifact types |
| Export | satisfies | REQ-30 | Export is self-contained for AI |
| Documentation | satisfies | REQ-O1 | — |
| Documentation | satisfies | REQ-Q1 | — |
| Documentation | satisfies | REQ-O10 | — |
| Documentation | satisfies | REQ-O11 | — |
| Documentation | satisfies | REQ-O12 | — |
| Documentation | satisfies | REQ-O13 | — |
| Documentation | satisfies | REQ-O14 | — |
| Documentation | satisfies | REQ-O15 | — |
| Documentation | satisfies | REQ-O16 | — |
| Documentation | satisfies | REQ-O17 | — |
| Documentation | satisfies | REQ-O18 | — |
| Documentation | satisfies | REQ-O19 | — |
| Documentation | satisfies | REQ-O2 | — |
| Core | satisfies | REQ-O14 | — |
| Core | satisfies | REQ-O15 | — |
| Core | satisfies | REQ-O16 | — |
| Core | satisfies | REQ-O17 | — |
| Extract | satisfies | REQ-O18 | — |
| Extract | satisfies | REQ-O19 | — |

## Constraint Allocation


## Coverage Gaps

- Constraint **Python >=3.11** (CON-1) is not allocated to any component
- Constraint **CI/CD: GitHub Actions** (CON-2) is not allocated to any component
