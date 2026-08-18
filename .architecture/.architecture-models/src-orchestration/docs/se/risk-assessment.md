---
document: Risk Assessment
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

# Risk Assessment: Src (orchestration)

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-CAP-CAP-1 | Capability | HIGH | Capability 'Root Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-2 | Capability | HIGH | Capability 'Bookmarklet Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-3 | Capability | HIGH | Capability 'Tag Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-4 | Capability | HIGH | Capability 'Filter Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-5 | Capability | HIGH | Capability 'View Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-6 | Capability | HIGH | Capability 'Model Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-7 | Capability | HIGH | Capability '^Model Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-8 | Capability | HIGH | Capability 'Template Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-9 | Capability | HIGH | Capability 'Login Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-10 | Capability | HIGH | Capability 'Logout Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-11 | Capability | HIGH | Capability 'Password Change Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-12 | Capability | HIGH | Capability 'Password Reset Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-13 | Capability | HIGH | Capability 'Reset Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-14 | Capability | HIGH | Capability '<Path:Url> Management' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-20 | Capability | HIGH | Capability 'Decompose' has no realizing component | Allocate to component or remove if not needed |
| RISK-DEP-src-orchestration-COMP-1 | Dependency | MEDIUM | Auto Enrich has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-2 | Dependency | MEDIUM | Behavior Decompose has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-3 | Dependency | MEDIUM | Behavior Flows has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-4 | Dependency | MEDIUM | Capability Inference has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-5 | Dependency | MEDIUM | Compaction has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-6 | Dependency | MEDIUM | Decompose has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-7 | Dependency | MEDIUM | Deep Decompose has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-8 | Dependency | MEDIUM | Enrich has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-12 | Dependency | MEDIUM | Trigger Detection has 3 dependents | Monitor for breaking changes |
| RISK-DEP-src-orchestration-COMP-13 | Dependency | MEDIUM | Use Case Inference has 3 dependents | Monitor for breaking changes |

## Dependency Risks

Components with high dependency count (fragile to upstream changes):

| Component | Dependencies (fan-out) |
|-----------|----------------------|
| Enrichment Context | 12 |
| Naming Context | 12 |
| Pipeline | 12 |

## Constraint Risks

*No constraints defined.*
