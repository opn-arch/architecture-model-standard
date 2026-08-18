---
document: Risk Assessment
system: Src (src)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:26Z
generator_version: 0.3.0
model_hash: 254bd5a18b33
edition: 3
---

# Risk Assessment: Src (src)

## Risk Register

| Risk ID | Category | Severity | Description | Mitigation |
|---------|----------|----------|-------------|------------|
| RISK-DEP-COMP-3 | Dependency | HIGH | Parser has 20 dependents — single point of failure | Ensure thorough testing of Parser; consider interface abstraction |
| RISK-DEP-COMP-4 | Dependency | HIGH | Main has 41 dependents — single point of failure | Ensure thorough testing of Main; consider interface abstraction |
| RISK-DEP-COMP-7 | Dependency | HIGH | Cluster has 21 dependents — single point of failure | Ensure thorough testing of Cluster; consider interface abstraction |
| RISK-DEP-COMP-8 | Dependency | HIGH | Completeness has 21 dependents — single point of failure | Ensure thorough testing of Completeness; consider interface abstraction |
| RISK-DEP-COMP-9 | Dependency | HIGH | Compression has 21 dependents — single point of failure | Ensure thorough testing of Compression; consider interface abstraction |
| RISK-DEP-COMP-10 | Dependency | HIGH | Confidence has 20 dependents — single point of failure | Ensure thorough testing of Confidence; consider interface abstraction |
| RISK-DEP-COMP-11 | Dependency | HIGH | Corrections has 27 dependents — single point of failure | Ensure thorough testing of Corrections; consider interface abstraction |
| RISK-DEP-COMP-12 | Dependency | HIGH | Coverage has 21 dependents — single point of failure | Ensure thorough testing of Coverage; consider interface abstraction |
| RISK-DEP-COMP-13 | Dependency | HIGH | Decomposer has 20 dependents — single point of failure | Ensure thorough testing of Decomposer; consider interface abstraction |
| RISK-DEP-COMP-14 | Dependency | HIGH | Differ has 21 dependents — single point of failure | Ensure thorough testing of Differ; consider interface abstraction |
| RISK-DEP-COMP-15 | Dependency | HIGH | Merger has 21 dependents — single point of failure | Ensure thorough testing of Merger; consider interface abstraction |
| RISK-DEP-COMP-16 | Dependency | HIGH | Regen Readiness has 24 dependents — single point of failure | Ensure thorough testing of Regen Readiness; consider interface abstraction |
| RISK-DEP-COMP-17 | Dependency | HIGH | Representativeness has 20 dependents — single point of failure | Ensure thorough testing of Representativeness; consider interface abstraction |
| RISK-DEP-COMP-18 | Dependency | HIGH | Slicer has 21 dependents — single point of failure | Ensure thorough testing of Slicer; consider interface abstraction |
| RISK-DEP-COMP-19 | Dependency | HIGH | Source Block Assign has 20 dependents — single point of failure | Ensure thorough testing of Source Block Assign; consider interface abstraction |
| RISK-DEP-COMP-21 | Dependency | HIGH | Validator has 21 dependents — single point of failure | Ensure thorough testing of Validator; consider interface abstraction |
| RISK-DEP-COMP-22 | Dependency | HIGH | Visualize has 21 dependents — single point of failure | Ensure thorough testing of Visualize; consider interface abstraction |
| RISK-DEP-COMP-26 | Dependency | HIGH | From Artifacts has 5 dependents — single point of failure | Ensure thorough testing of From Artifacts; consider interface abstraction |
| RISK-DEP-COMP-30 | Dependency | HIGH | Behavior has 19 dependents — single point of failure | Ensure thorough testing of Behavior; consider interface abstraction |
| RISK-DEP-COMP-31 | Dependency | HIGH | Blocks has 17 dependents — single point of failure | Ensure thorough testing of Blocks; consider interface abstraction |
| RISK-DEP-COMP-32 | Dependency | HIGH | Body Hints has 18 dependents — single point of failure | Ensure thorough testing of Body Hints; consider interface abstraction |
| RISK-DEP-COMP-33 | Dependency | HIGH | Call Graph has 17 dependents — single point of failure | Ensure thorough testing of Call Graph; consider interface abstraction |
| RISK-DEP-COMP-34 | Dependency | HIGH | Chains has 18 dependents — single point of failure | Ensure thorough testing of Chains; consider interface abstraction |
| RISK-DEP-COMP-35 | Dependency | HIGH | Display has 18 dependents — single point of failure | Ensure thorough testing of Display; consider interface abstraction |
| RISK-DEP-COMP-36 | Dependency | HIGH | Generator has 17 dependents — single point of failure | Ensure thorough testing of Generator; consider interface abstraction |
| RISK-DEP-COMP-37 | Dependency | HIGH | Grouping has 17 dependents — single point of failure | Ensure thorough testing of Grouping; consider interface abstraction |
| RISK-DEP-COMP-38 | Dependency | HIGH | Interfaces has 17 dependents — single point of failure | Ensure thorough testing of Interfaces; consider interface abstraction |
| RISK-DEP-COMP-39 | Dependency | HIGH | Kt Scanner has 17 dependents — single point of failure | Ensure thorough testing of Kt Scanner; consider interface abstraction |
| RISK-DEP-COMP-40 | Dependency | HIGH | Metrics has 17 dependents — single point of failure | Ensure thorough testing of Metrics; consider interface abstraction |
| RISK-DEP-COMP-41 | Dependency | HIGH | Multi Scanner has 17 dependents — single point of failure | Ensure thorough testing of Multi Scanner; consider interface abstraction |
| RISK-DEP-COMP-42 | Dependency | HIGH | Protocol has 35 dependents — single point of failure | Ensure thorough testing of Protocol; consider interface abstraction |
| RISK-DEP-COMP-43 | Dependency | HIGH | Recursive has 17 dependents — single point of failure | Ensure thorough testing of Recursive; consider interface abstraction |
| RISK-DEP-COMP-44 | Dependency | HIGH | Scan Cache has 21 dependents — single point of failure | Ensure thorough testing of Scan Cache; consider interface abstraction |
| RISK-DEP-COMP-46 | Dependency | HIGH | Slicers has 17 dependents — single point of failure | Ensure thorough testing of Slicers; consider interface abstraction |
| RISK-DEP-COMP-47 | Dependency | HIGH | Ts Scanner has 18 dependents — single point of failure | Ensure thorough testing of Ts Scanner; consider interface abstraction |
| RISK-DEP-COMP-48 | Dependency | HIGH | Monitoring has 41 dependents — single point of failure | Ensure thorough testing of Monitoring; consider interface abstraction |
| RISK-DEP-COMP-51 | Dependency | HIGH | Behavior Decompose has 7 dependents — single point of failure | Ensure thorough testing of Behavior Decompose; consider interface abstraction |
| RISK-DEP-COMP-58 | Dependency | HIGH | Enrichment Context has 7 dependents — single point of failure | Ensure thorough testing of Enrichment Context; consider interface abstraction |
| RISK-DEP-COMP-60 | Dependency | HIGH | Pipeline has 7 dependents — single point of failure | Ensure thorough testing of Pipeline; consider interface abstraction |
| RISK-DEP-COMP-63 | Dependency | HIGH | Patterns has 41 dependents — single point of failure | Ensure thorough testing of Patterns; consider interface abstraction |
| RISK-DEP-COMP-65 | Dependency | HIGH | Allocate has 11 dependents — single point of failure | Ensure thorough testing of Allocate; consider interface abstraction |
| RISK-DEP-COMP-66 | Dependency | HIGH | Allocate Types has 46 dependents — single point of failure | Ensure thorough testing of Allocate Types; consider interface abstraction |
| RISK-DEP-COMP-70 | Dependency | HIGH | Contract has 6 dependents — single point of failure | Ensure thorough testing of Contract; consider interface abstraction |
| RISK-DEP-COMP-76 | Dependency | HIGH | Global Learning has 5 dependents — single point of failure | Ensure thorough testing of Global Learning; consider interface abstraction |
| RISK-DEP-COMP-77 | Dependency | HIGH | Infer has 10 dependents — single point of failure | Ensure thorough testing of Infer; consider interface abstraction |
| RISK-DEP-COMP-80 | Dependency | HIGH | Lessons has 5 dependents — single point of failure | Ensure thorough testing of Lessons; consider interface abstraction |
| RISK-DEP-COMP-81 | Dependency | HIGH | Observe has 12 dependents — single point of failure | Ensure thorough testing of Observe; consider interface abstraction |
| RISK-DEP-COMP-84 | Dependency | HIGH | Relate has 8 dependents — single point of failure | Ensure thorough testing of Relate; consider interface abstraction |
| RISK-DEP-COMP-86 | Dependency | HIGH | Report has 5 dependents — single point of failure | Ensure thorough testing of Report; consider interface abstraction |
| RISK-DEP-COMP-87 | Dependency | HIGH | Requirements Derive has 5 dependents — single point of failure | Ensure thorough testing of Requirements Derive; consider interface abstraction |
| RISK-DEP-COMP-88 | Dependency | HIGH | Specify has 6 dependents — single point of failure | Ensure thorough testing of Specify; consider interface abstraction |
| RISK-DEP-COMP-92 | Dependency | HIGH | Validate has 7 dependents — single point of failure | Ensure thorough testing of Validate; consider interface abstraction |
| RISK-DEP-COMP-94 | Dependency | HIGH | Discovery has 7 dependents — single point of failure | Ensure thorough testing of Discovery; consider interface abstraction |
| RISK-CAP-CAP-1 | Capability | HIGH | Capability 'Web Routes' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-20 | Capability | HIGH | Capability 'Source Block Quality' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-27 | Capability | HIGH | Capability 'From Code' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-45 | Capability | HIGH | Capability 'Scanner' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-49 | Capability | HIGH | Capability 'Monitoring Checks' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-52 | Capability | HIGH | Capability 'Behavior Flows' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-55 | Capability | HIGH | Capability 'Decompose' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-57 | Capability | HIGH | Capability 'Enrich' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-67 | Capability | HIGH | Capability 'Artifacts' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-68 | Capability | HIGH | Capability 'Cache' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-69 | Capability | HIGH | Capability 'Context Gen' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-71 | Capability | HIGH | Capability 'Contract Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-73 | Capability | HIGH | Capability 'Decompose Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-75 | Capability | HIGH | Capability 'Emit Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-78 | Capability | HIGH | Capability 'Infer Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-79 | Capability | HIGH | Capability 'Learning' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-82 | Capability | HIGH | Capability 'Observe Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-83 | Capability | HIGH | Capability 'Regen Score' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-85 | Capability | HIGH | Capability 'Relate Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-89 | Capability | HIGH | Capability 'Specify Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-91 | Capability | HIGH | Capability 'Synthesize Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-93 | Capability | HIGH | Capability 'Validate Types' has no realizing component | Allocate to component or remove if not needed |
| RISK-CAP-CAP-95 | Capability | HIGH | Capability 'CLI Main' has no realizing component | Allocate to component or remove if not needed |
| RISK-DEP-COMP-5 | Dependency | MEDIUM | Loader has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-6 | Dependency | MEDIUM | Schema has 4 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-50 | Dependency | MEDIUM | Auto Enrich has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-53 | Dependency | MEDIUM | Capability Inference has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-54 | Dependency | MEDIUM | Compaction has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-56 | Dependency | MEDIUM | Deep Decompose has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-61 | Dependency | MEDIUM | Trigger Detection has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-62 | Dependency | MEDIUM | Use Case Inference has 3 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-72 | Dependency | MEDIUM | Coordinator has 4 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-74 | Dependency | MEDIUM | Emit has 4 dependents | Monitor for breaking changes |
| RISK-DEP-COMP-90 | Dependency | MEDIUM | Synthesize has 4 dependents | Monitor for breaking changes |

## Dependency Risks

Components with high dependency count (fragile to upstream changes):

| Component | Dependencies (fan-out) |
|-----------|----------------------|
| Pipeline | 46 |
| Behavior Decompose | 41 |
| Scan Cache | 40 |
| Gate | 37 |
| Auto Enrich | 37 |
| Deep Decompose | 37 |
| Trigger Detection | 37 |
| Representativeness | 36 |
| Behavior | 36 |
| Grouping | 36 |
| From Artifacts | 33 |
| Emit | 25 |
| Synthesize | 25 |
| Coordinator | 24 |
| Recursive | 23 |
| Blocks | 21 |
| Generator | 21 |
| Kt Scanner | 21 |
| Metrics | 21 |
| Regen Readiness | 20 |
| Constraint Detector | 20 |
| Body Hints | 20 |
| Call Graph | 20 |
| Interfaces | 20 |
| Multi Scanner | 20 |
| Slicers | 20 |
| Capability Inference | 20 |
| Compaction | 20 |
| Enrichment Context | 20 |
| Use Case Inference | 20 |
| Parser | 19 |
| Confidence | 19 |
| Decomposer | 19 |
| Source Block Assign | 19 |
| Visualize | 16 |
| Naming Context | 13 |
| Merger | 5 |
| Allocate | 5 |
| Relate | 5 |
| Validate | 5 |
| Coverage | 4 |
| Differ | 4 |
| Slicer | 4 |
| Validator | 4 |
| Contract | 4 |
| Infer | 4 |
| Specify | 4 |
| Cluster | 3 |

## Constraint Risks

*No constraints defined.*
