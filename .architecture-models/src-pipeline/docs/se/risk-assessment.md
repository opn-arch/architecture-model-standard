---
document: Risk Assessment
system: Src (pipeline)
system_id: SYS-unknown
generated_at: 2026-08-19T17:00:04Z
generator_version: 0.3.0
model_hash: ccd998005d8e
edition: 7
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 21/21 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Risk Assessment: Src (pipeline)

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-DEP-src-pipeline-COMP-16 | Dependency | HIGH | Allocate has 11 dependents — single point of failure | Ensure thorough testing of Allocate; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-18 | Dependency | HIGH | Artifacts has 5 dependents — single point of failure | Ensure thorough testing of Artifacts; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-20 | Dependency | HIGH | Context Gen has 5 dependents — single point of failure | Ensure thorough testing of Context Gen; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-21 | Dependency | HIGH | Contract has 6 dependents — single point of failure | Ensure thorough testing of Contract; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-24 | Dependency | HIGH | Corrections has 7 dependents — single point of failure | Ensure thorough testing of Corrections; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-29 | Dependency | HIGH | Global Learning has 5 dependents — single point of failure | Ensure thorough testing of Global Learning; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-30 | Dependency | HIGH | Infer has 10 dependents — single point of failure | Ensure thorough testing of Infer; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-33 | Dependency | HIGH | Lessons has 5 dependents — single point of failure | Ensure thorough testing of Lessons; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-34 | Dependency | HIGH | Observe has 12 dependents — single point of failure | Ensure thorough testing of Observe; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-36 | Dependency | HIGH | Protocol has 18 dependents — single point of failure | Ensure thorough testing of Protocol; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-37 | Dependency | HIGH | Regen Score has 5 dependents — single point of failure | Ensure thorough testing of Regen Score; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-38 | Dependency | HIGH | Relate has 8 dependents — single point of failure | Ensure thorough testing of Relate; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-40 | Dependency | HIGH | Report has 5 dependents — single point of failure | Ensure thorough testing of Report; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-41 | Dependency | HIGH | Requirements Derive has 5 dependents — single point of failure | Ensure thorough testing of Requirements Derive; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-42 | Dependency | HIGH | Specify has 6 dependents — single point of failure | Ensure thorough testing of Specify; consider interface abstraction |
| RISK-DEP-src-pipeline-COMP-46 | Dependency | HIGH | Validate has 7 dependents — single point of failure | Ensure thorough testing of Validate; consider interface abstraction |
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
| RISK-CAP-CAP-17 | Capability | HIGH | Capability 'Allocate Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-22 | Capability | HIGH | Capability 'Contract Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-26 | Capability | HIGH | Capability 'Decompose Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-28 | Capability | HIGH | Capability 'Emit Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-31 | Capability | HIGH | Capability 'Infer Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-32 | Capability | HIGH | Capability 'Learning' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-35 | Capability | HIGH | Capability 'Observe Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-39 | Capability | HIGH | Capability 'Relate Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-43 | Capability | HIGH | Capability 'Specify Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-45 | Capability | HIGH | Capability 'Synthesize Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-47 | Capability | HIGH | Capability 'Validate Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-DEP-src-pipeline-COMP-19 | Dependency | MEDIUM | Cache has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-pipeline-COMP-23 | Dependency | MEDIUM | Coordinator has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-pipeline-COMP-25 | Dependency | MEDIUM | Decompose has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-pipeline-COMP-27 | Dependency | MEDIUM | Emit has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-pipeline-COMP-44 | Dependency | MEDIUM | Synthesize has 4 dependents | Monitor for breaking changes |

## Dependency Risks

Components with high dependency count (fragile to upstream changes):

| Component | Dependencies (fan-out) |
|-----------|----------------------|
| Cache | 20 |
| Coordinator | 20 |
| Decompose | 20 |
| Emit | 20 |
| Synthesize | 20 |
| Artifacts | 8 |
| Context Gen | 6 |
| Allocate | 4 |
| Relate | 4 |
| Validate | 4 |
| Contract | 3 |
| Infer | 3 |
| Specify | 3 |

## Constraint Risks

*No constraints defined.*
