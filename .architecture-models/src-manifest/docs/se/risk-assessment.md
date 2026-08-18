---
document: Risk Assessment
system: Src (manifest)
system_id: SYS-unknown
generated_at: 2026-08-18T23:36:34Z
generator_version: 0.3.0
model_hash: 43ce18da3e69
edition: 6
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 17/17 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Risk Assessment: Src (manifest)

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-DEP-src-manifest-COMP-16 | Dependency | HIGH | Behavior has 11 dependents — single point of failure | Ensure thorough testing of Behavior; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-17 | Dependency | HIGH | Blocks has 11 dependents — single point of failure | Ensure thorough testing of Blocks; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-18 | Dependency | HIGH | Body Hints has 11 dependents — single point of failure | Ensure thorough testing of Body Hints; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-19 | Dependency | HIGH | Call Graph has 10 dependents — single point of failure | Ensure thorough testing of Call Graph; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-20 | Dependency | HIGH | Chains has 11 dependents — single point of failure | Ensure thorough testing of Chains; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-21 | Dependency | HIGH | Display has 11 dependents — single point of failure | Ensure thorough testing of Display; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-22 | Dependency | HIGH | Generator has 10 dependents — single point of failure | Ensure thorough testing of Generator; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-23 | Dependency | HIGH | Grouping has 10 dependents — single point of failure | Ensure thorough testing of Grouping; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-24 | Dependency | HIGH | Interfaces has 10 dependents — single point of failure | Ensure thorough testing of Interfaces; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-25 | Dependency | HIGH | Kt Scanner has 10 dependents — single point of failure | Ensure thorough testing of Kt Scanner; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-26 | Dependency | HIGH | Metrics has 10 dependents — single point of failure | Ensure thorough testing of Metrics; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-27 | Dependency | HIGH | Multi Scanner has 10 dependents — single point of failure | Ensure thorough testing of Multi Scanner; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-28 | Dependency | HIGH | Protocol has 11 dependents — single point of failure | Ensure thorough testing of Protocol; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-29 | Dependency | HIGH | Recursive has 10 dependents — single point of failure | Ensure thorough testing of Recursive; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-30 | Dependency | HIGH | Scan Cache has 10 dependents — single point of failure | Ensure thorough testing of Scan Cache; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-32 | Dependency | HIGH | Slicers has 10 dependents — single point of failure | Ensure thorough testing of Slicers; consider interface abstraction |
| RISK-DEP-src-manifest-COMP-33 | Dependency | HIGH | Ts Scanner has 11 dependents — single point of failure | Ensure thorough testing of Ts Scanner; consider interface abstraction |
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
| RISK-CAP-CAP-15 | Capability | HIGH | Capability 'gRPC Services' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-31 | Capability | HIGH | Capability 'Scanner' has no realizing component | Allocate to component or remove if not needed |

## Dependency Risks

Components with high dependency count (fragile to upstream changes):

| Component | Dependencies (fan-out) |
|-----------|----------------------|
| Blocks | 16 |
| Call Graph | 16 |
| Generator | 16 |
| Grouping | 16 |
| Interfaces | 16 |
| Kt Scanner | 16 |
| Metrics | 16 |
| Multi Scanner | 16 |
| Recursive | 16 |
| Scan Cache | 16 |
| Slicers | 16 |

## Constraint Risks

*No constraints defined.*
