---
document: Risk Assessment
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T23:36:29Z
generator_version: 0.3.0
model_hash: 41fb0d4bec16
edition: 7
---

> **Model Completeness: F (14%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 92/92 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Risk Assessment: System
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
| RISK-CAP-CAP-1 | Capability | HIGH | Capability 'HTTP Route Definitions' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-2 | Capability | HIGH | Capability 'gRPC Services' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-5 | Capability | HIGH | Capability 'Command Line Interface Entry Point' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-6 | Capability | HIGH | Capability 'Command Line Executor' has no realizing component | Allocate to component or remove if not needed |
| RISK-DEP-src-pipeline-COMP-19 | Dependency | MEDIUM | Cache has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-pipeline-COMP-23 | Dependency | MEDIUM | Coordinator has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-pipeline-COMP-25 | Dependency | MEDIUM | Decompose has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-pipeline-COMP-27 | Dependency | MEDIUM | Emit has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-pipeline-COMP-44 | Dependency | MEDIUM | Synthesize has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-core-COMP-18 | Dependency | MEDIUM | Confidence has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-core-COMP-21 | Dependency | MEDIUM | Decomposer has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-core-COMP-25 | Dependency | MEDIUM | Regen Readiness has 4 dependents | Monitor for breaking changes |
| RISK-DEP-src-core-COMP-26 | Dependency | MEDIUM | Representativeness has 4 dependents | Monitor for breaking changes |
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
| Cache | 20 |
| Coordinator | 20 |
| Decompose | 20 |
| Emit | 20 |
| Synthesize | 20 |
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
| Confidence | 15 |
| Decomposer | 15 |
| Regen Readiness | 15 |
| Representativeness | 15 |
| Source Block Assign | 15 |
| Enrichment Context | 12 |
| Naming Context | 12 |
| Pipeline | 12 |
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

---

---

## LLM Review

*Reviewed: 2026-08-18T23:37:46.525850+00:00 | Duration: 8018ms*

**Summary:** This risk assessment is almost entirely auto-generated with extremely low model completeness (14%), producing a monotonous register of 40+ identical "dependency/single point of failure" risks with copy-paste mitigations, offering negligible actionable insight for engineering decisions.

- Every risk entry uses the same templated mitigation ("ensure thorough testing; consider interface abstraction") regardless of the component's role, criticality, or blast radius — this fails to prioritize or differentiate response strategies.
- The assessment only covers dependency fan-in risks and completely ignores other critical categories such as security, performance, data integrity, operational/deployment risks, and failure propagation across subsystem boundaries.
- With 92/92 components missing descriptions and no requirements or interfaces defined, this document cannot meaningfully inform architectural decisions and should be regenerated after the extraction pipeline populates the model.

<details>
<summary>Review details</summary>

**Prompt sent (truncated):**
```
Review the following architecture artifact 'docs/se/risk-assessment.md'.
Respond ONLY in this format:
SUMMARY: <one paragraph overall assessment>
COMMENT: <specific observation>
COMMENT: <another observation>

---
---
document: Risk Assessment
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T23:36:29Z
generator_version: 0.3.0
model_hash: 41fb0d4bec16
edition: 7
---

> **Model Completeness: F (14%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defin
```

**Full LLM response:**
```
SUMMARY: This risk assessment is almost entirely auto-generated with extremely low model completeness (14%), producing a monotonous register of 40+ identical "dependency/single point of failure" risks with copy-paste mitigations, offering negligible actionable insight for engineering decisions.

COMMENT: Every risk entry uses the same templated mitigation ("ensure thorough testing; consider interface abstraction") regardless of the component's role, criticality, or blast radius — this fails to prioritize or differentiate response strategies.

COMMENT: The assessment only covers dependency fan-in risks and completely ignores other critical categories such as security, performance, data integrity, operational/deployment risks, and failure propagation across subsystem boundaries.

COMMENT: With 92/92 components missing descriptions and no requirements or interfaces defined, this document cannot meaningfully inform architectural decisions and should be regenerated after the extraction pipeline populates the model.
```

</details>
