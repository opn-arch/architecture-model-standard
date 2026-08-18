---
document: Risk Assessment
system: Src (core)
system_id: SYS-unknown
generated_at: 2026-08-18T20:06:06Z
generator_version: 0.3.0
model_hash: 65254bb02f54
edition: 8
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 16/16 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Risk Assessment: Src (core)

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-DEP-src-core-COMP-15 | Dependency | HIGH | Cluster has 5 dependents — single point of failure | Ensure thorough testing of Cluster; consider interface abstraction |
| RISK-DEP-src-core-COMP-16 | Dependency | HIGH | Completeness has 5 dependents — single point of failure | Ensure thorough testing of Completeness; consider interface abstraction |
| RISK-DEP-src-core-COMP-17 | Dependency | HIGH | Compression has 5 dependents — single point of failure | Ensure thorough testing of Compression; consider interface abstraction |
| RISK-DEP-src-core-COMP-19 | Dependency | HIGH | Corrections has 5 dependents — single point of failure | Ensure thorough testing of Corrections; consider interface abstraction |
| RISK-DEP-src-core-COMP-20 | Dependency | HIGH | Coverage has 5 dependents — single point of failure | Ensure thorough testing of Coverage; consider interface abstraction |
| RISK-DEP-src-core-COMP-22 | Dependency | HIGH | Differ has 5 dependents — single point of failure | Ensure thorough testing of Differ; consider interface abstraction |
| RISK-DEP-src-core-COMP-23 | Dependency | HIGH | Merger has 5 dependents — single point of failure | Ensure thorough testing of Merger; consider interface abstraction |
| RISK-DEP-src-core-COMP-24 | Dependency | HIGH | Parser has 5 dependents — single point of failure | Ensure thorough testing of Parser; consider interface abstraction |
| RISK-DEP-src-core-COMP-27 | Dependency | HIGH | Slicer has 5 dependents — single point of failure | Ensure thorough testing of Slicer; consider interface abstraction |
| RISK-DEP-src-core-COMP-28 | Dependency | HIGH | Source Block Assign has 10 dependents — single point of failure | Ensure thorough testing of Source Block Assign; consider interface abstraction |
| RISK-DEP-src-core-COMP-30 | Dependency | HIGH | Validator has 5 dependents — single point of failure | Ensure thorough testing of Validator; consider interface abstraction |
| RISK-DEP-src-core-COMP-31 | Dependency | HIGH | Visualize has 5 dependents — single point of failure | Ensure thorough testing of Visualize; consider interface abstraction |
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
| RISK-CAP-CAP-29 | Capability | HIGH | Capability 'Source Block Quality' has no realizing component | Allocate to component or remove if not needed |
| RISK-DEP-src-core-COMP-18 | Dependency | MEDIUM | Confidence has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-core-COMP-21 | Dependency | MEDIUM | Decomposer has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-core-COMP-25 | Dependency | MEDIUM | Regen Readiness has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-core-COMP-26 | Dependency | MEDIUM | Representativeness has 4 dependents | Monitor for breaking changes |

## Dependency Risks

Components with high dependency count (fragile to upstream changes):

| Component | Dependencies (fan-out) |
|-----------|----------------------|
| Confidence | 15 |
| Decomposer | 15 |
| Regen Readiness | 15 |
| Representativeness | 15 |
| Source Block Assign | 15 |

## Constraint Risks

*No constraints defined.*
