---
document: Logical Architecture
system: architecture-model-standard
system_id: SYS-unknown
generated_at: 2026-08-19T16:59:51Z
generator_version: 0.3.0
model_hash: 435262313fec
edition: 8
---

# Logical Architecture: architecture-model-standard
## Layer Structure
*No layers defined.*
## Component Allocation
### application

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Documentation (COMP-4) | library | 1 files | — |
| Core Doc Generators (COMP-4.1) | library | 11 files | — |
| SE Document Suite (COMP-4.2) | library | 21 files | — |
| Orchestration (COMP-5) | service | 1 files | — |
| Enrichment (COMP-5.1) | service | 7 files | — |
| Decomposition (COMP-5.2) | service | 6 files | — |
| Authoring (COMP-7) | library | 3 files | — |
| Export (COMP-10) | library | 3 files | — |

### domain

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Pipeline (COMP-2) | service | 1 files | — |
| Pipeline Coordination (COMP-2.1) | service | 7 files | — |
| Observation Stages (COMP-2.2) | service | 4 files | — |
| Allocation & Relation Stages (COMP-2.3) | service | 4 files | — |
| Specification & Contract Stages (COMP-2.4) | service | 6 files | — |
| Synthesis & Emit Stages (COMP-2.5) | service | 7 files | — |
| Manifest (COMP-3) | library | 2 files | — |
| Scanners (COMP-3.1) | library | 8 files | — |
| Graph & Analysis (COMP-3.2) | library | 5 files | — |
| Grouping & Generation (COMP-3.3) | library | 6 files | — |
| Extract (COMP-6) | library | 5 files | — |
| Pipeline Learning (COMP-11) | library | 3 files | — |

### foundation

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Core (COMP-1) | library | 1 files | — |
| Type System (COMP-1.1) | library | 1 files | — |
| Validation (COMP-1.2) | library | 2 files | — |
| Parser & Persistence (COMP-1.3) | library | 5 files | — |
| Model Operations (COMP-1.4) | library | 8 files | — |
| Quality Metrics (COMP-1.5) | library | 5 files | — |

### infrastructure

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Configuration (COMP-9) | library | 6 files | — |
| Utilities (COMP-12) | library | 6 files | — |

### interface

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| CLI (COMP-8) | service | 5 files | — |
## Inter-Component Interfaces
| Interface | Type | Protocol | Provider | Consumer |
|-----------|------|----------|----------|----------|
| main CLI | internal | — | — | — |
| runner CLI | internal | — | — | — |
| COMP-4-7 Library API | internal | — | — | — |
| COMP-3-1 Library API | internal | — | — | — |
| COMP-4-1 Library API | internal | — | — | — |
| COMP-4-2 Library API | internal | — | — | — |
| COMP-4-3 Library API | internal | — | — | — |
| COMP-4-4 Library API | internal | — | — | — |
| COMP-4-5 Library API | internal | — | — | — |
| COMP-4-6 Library API | internal | — | — | — |
| COMP-4-8 Library API | internal | — | — | — |
| COMP-4-9 Library API | internal | — | — | — |
| COMP-4-10 Library API | internal | — | — | — |
| COMP-4-11 Library API | internal | — | — | — |
| COMP-4-12 Library API | internal | — | — | — |
| COMP-4-13 Library API | internal | — | — | — |
| Core API | internal | — | — | — |
| Type System API | internal | — | — | — |
| Validation API | internal | — | — | — |
| Parser & Persistence API | internal | — | — | — |
| Model Operations API | internal | — | — | — |
| Quality Metrics API | internal | — | — | — |
| Pipeline API | internal | — | — | — |
| Pipeline Coordination API | internal | — | — | — |
| Observation Stages API | internal | — | — | — |
| Allocation & Relation Stages API | internal | — | — | — |
| Specification & Contract Stages API | internal | — | — | — |
| Synthesis & Emit Stages API | internal | — | — | — |
| Scanners API | internal | — | — | — |
| Graph & Analysis API | internal | — | — | — |
| Grouping & Generation API | internal | — | — | — |
| Core Doc Generators API | internal | — | — | — |
| SE Document Suite API | internal | — | — | — |
| Orchestration API | internal | — | — | — |
| Enrichment API | internal | — | — | — |
| Decomposition API | internal | — | — | — |
| Extract API | internal | — | — | — |
| Authoring API | internal | — | — | — |
| CLI API | internal | — | — | — |
| Configuration API | internal | — | — | — |
| Export API | internal | — | — | — |
| Pipeline Learning API | internal | — | — | — |
| Utilities API | internal | — | — | — |
## Dependency Graph
```mermaid
graph TD
    scripts-dev-simulation-COMP-10["Infrastructure"]
    scripts-dev-simulation-COMP-8["Runner"]
    scripts-dev-simulation-COMP-10 --> scripts-dev-simulation-COMP-8
    src-pipeline-COMP-19["Cache"]
    src-pipeline-COMP-30["Infer"]
    src-pipeline-COMP-19 --> src-pipeline-COMP-30
    src-pipeline-COMP-38["Relate"]
    src-pipeline-COMP-16["Allocate"]
    src-pipeline-COMP-38 --> src-pipeline-COMP-16
    src-pipeline-COMP-23["Coordinator"]
    src-pipeline-COMP-44["Synthesize"]
    src-pipeline-COMP-23 --> src-pipeline-COMP-44
    src-pipeline-COMP-18["Artifacts"]
    src-pipeline-COMP-23 --> src-pipeline-COMP-18
    src-pipeline-COMP-44 --> src-pipeline-COMP-30
    src-pipeline-COMP-25["Decompose"]
    src-pipeline-COMP-27["Emit"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-27
    src-pipeline-COMP-23 --> src-pipeline-COMP-19
    src-pipeline-COMP-34["Observe"]
    src-pipeline-COMP-23 --> src-pipeline-COMP-34
    src-pipeline-COMP-46["Validate"]
    src-pipeline-COMP-18 --> src-pipeline-COMP-46
    src-pipeline-COMP-23 --> src-pipeline-COMP-38
    src-pipeline-COMP-25 --> src-pipeline-COMP-23
    src-pipeline-COMP-27 --> src-pipeline-COMP-34
    src-pipeline-COMP-37["Regen Score"]
    src-pipeline-COMP-19 --> src-pipeline-COMP-37
    src-pipeline-COMP-16 --> src-pipeline-COMP-30
    src-pipeline-COMP-38 --> src-pipeline-COMP-34
    src-pipeline-COMP-27 --> src-pipeline-COMP-37
    src-pipeline-COMP-44 --> src-pipeline-COMP-37
    src-pipeline-COMP-41["Requirements Derive"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-41
    src-pipeline-COMP-20["Context Gen"]
    src-pipeline-COMP-27 --> src-pipeline-COMP-20
    src-pipeline-COMP-44 --> src-pipeline-COMP-20
    src-pipeline-COMP-36["Protocol"]
    src-pipeline-COMP-19 --> src-pipeline-COMP-36
    src-pipeline-COMP-19 --> src-pipeline-COMP-16
    src-pipeline-COMP-42["Specify"]
    src-pipeline-COMP-27 --> src-pipeline-COMP-42
    src-pipeline-COMP-44 --> src-pipeline-COMP-42
    src-pipeline-COMP-29["Global Learning"]
    src-pipeline-COMP-23 --> src-pipeline-COMP-29
    src-pipeline-COMP-44 --> src-pipeline-COMP-36
    src-pipeline-COMP-44 --> src-pipeline-COMP-16
    src-pipeline-COMP-27 --> src-pipeline-COMP-29
    src-pipeline-COMP-21["Contract"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-21
    src-pipeline-COMP-18 --> src-pipeline-COMP-30
    src-pipeline-COMP-40["Report"]
    src-pipeline-COMP-23 --> src-pipeline-COMP-40
    src-pipeline-COMP-20 --> src-pipeline-COMP-30
    src-pipeline-COMP-19 --> src-pipeline-COMP-44
    src-pipeline-COMP-19 --> src-pipeline-COMP-18
    src-pipeline-COMP-23 --> src-pipeline-COMP-46
    src-pipeline-COMP-30 --> src-pipeline-COMP-36
    src-pipeline-COMP-24["Corrections"]
    src-pipeline-COMP-23 --> src-pipeline-COMP-24
    src-pipeline-COMP-16 --> src-pipeline-COMP-36
    src-pipeline-COMP-33["Lessons"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-33
    src-pipeline-COMP-19 --> src-pipeline-COMP-34
    src-pipeline-COMP-27 --> src-pipeline-COMP-44
    src-pipeline-COMP-27 --> src-pipeline-COMP-18
    src-pipeline-COMP-44 --> src-pipeline-COMP-18
    src-pipeline-COMP-46 --> src-pipeline-COMP-30
    src-pipeline-COMP-19 --> src-pipeline-COMP-38
    src-pipeline-COMP-27 --> src-pipeline-COMP-19
    src-pipeline-COMP-44 --> src-pipeline-COMP-19
    src-pipeline-COMP-18 --> src-pipeline-COMP-21
    src-pipeline-COMP-44 --> src-pipeline-COMP-34
    src-pipeline-COMP-21 --> src-pipeline-COMP-36
    src-pipeline-COMP-21 --> src-pipeline-COMP-16
    src-pipeline-COMP-23 --> src-pipeline-COMP-25
    src-pipeline-COMP-25 --> src-pipeline-COMP-30
    src-pipeline-COMP-27 --> src-pipeline-COMP-38
    src-pipeline-COMP-44 --> src-pipeline-COMP-38
    src-pipeline-COMP-19 --> src-pipeline-COMP-20
    src-pipeline-COMP-23 --> src-pipeline-COMP-27
    src-pipeline-COMP-27 --> src-pipeline-COMP-25
    src-pipeline-COMP-19 --> src-pipeline-COMP-42
    src-pipeline-COMP-18 --> src-pipeline-COMP-16
    src-pipeline-COMP-20 --> src-pipeline-COMP-36
    src-pipeline-COMP-19 --> src-pipeline-COMP-23
    src-pipeline-COMP-30 --> src-pipeline-COMP-34
    src-pipeline-COMP-20 --> src-pipeline-COMP-16
    src-pipeline-COMP-16 --> src-pipeline-COMP-34
    src-pipeline-COMP-19 --> src-pipeline-COMP-29
    src-pipeline-COMP-27 --> src-pipeline-COMP-23
    src-pipeline-COMP-44 --> src-pipeline-COMP-23
    src-pipeline-COMP-42 --> src-pipeline-COMP-36
    src-pipeline-COMP-25 --> src-pipeline-COMP-37
    src-pipeline-COMP-44 --> src-pipeline-COMP-29
    src-pipeline-COMP-42 --> src-pipeline-COMP-16
    src-pipeline-COMP-23 --> src-pipeline-COMP-41
    src-pipeline-COMP-46 --> src-pipeline-COMP-36
    src-pipeline-COMP-19 --> src-pipeline-COMP-40
    src-pipeline-COMP-21 --> src-pipeline-COMP-34
    src-pipeline-COMP-46 --> src-pipeline-COMP-16
    src-pipeline-COMP-19 --> src-pipeline-COMP-46
    src-pipeline-COMP-27 --> src-pipeline-COMP-40
    src-pipeline-COMP-19 --> src-pipeline-COMP-24
    src-pipeline-COMP-44 --> src-pipeline-COMP-40
    src-pipeline-COMP-25 --> src-pipeline-COMP-36
    src-pipeline-COMP-25 --> src-pipeline-COMP-16
    src-pipeline-COMP-18 --> src-pipeline-COMP-34
    src-pipeline-COMP-23 --> src-pipeline-COMP-21
    src-pipeline-COMP-20 --> src-pipeline-COMP-34
    src-pipeline-COMP-27 --> src-pipeline-COMP-46
    src-pipeline-COMP-44 --> src-pipeline-COMP-46
    src-pipeline-COMP-27 --> src-pipeline-COMP-24
    src-pipeline-COMP-44 --> src-pipeline-COMP-24
    src-pipeline-COMP-20 --> src-pipeline-COMP-38
    src-pipeline-COMP-42 --> src-pipeline-COMP-34
    src-pipeline-COMP-19 --> src-pipeline-COMP-25
    src-pipeline-COMP-19 --> src-pipeline-COMP-27
    src-pipeline-COMP-23 --> src-pipeline-COMP-33
    src-pipeline-COMP-18 --> src-pipeline-COMP-42
    src-pipeline-COMP-25 --> src-pipeline-COMP-44
    src-pipeline-COMP-25 --> src-pipeline-COMP-18
    src-pipeline-COMP-44 --> src-pipeline-COMP-25
    src-pipeline-COMP-18 --> src-pipeline-COMP-36
    src-pipeline-COMP-44 --> src-pipeline-COMP-27
    src-pipeline-COMP-25 --> src-pipeline-COMP-34
    src-pipeline-COMP-37 --> src-pipeline-COMP-36
    src-pipeline-COMP-23 --> src-pipeline-COMP-30
    src-pipeline-COMP-25 --> src-pipeline-COMP-38
    src-pipeline-COMP-19 --> src-pipeline-COMP-41
    src-pipeline-COMP-27 --> src-pipeline-COMP-30
    src-pipeline-COMP-34 --> src-pipeline-COMP-36
    src-pipeline-COMP-25 --> src-pipeline-COMP-20
    src-pipeline-COMP-27 --> src-pipeline-COMP-41
    src-pipeline-COMP-44 --> src-pipeline-COMP-41
    src-pipeline-COMP-25 --> src-pipeline-COMP-42
    src-pipeline-COMP-38 --> src-pipeline-COMP-30
    src-pipeline-COMP-33 --> src-pipeline-COMP-36
    src-pipeline-COMP-20 --> src-pipeline-COMP-46
    src-pipeline-COMP-25 --> src-pipeline-COMP-29
    src-pipeline-COMP-23 --> src-pipeline-COMP-37
    src-pipeline-COMP-29 --> src-pipeline-COMP-36
    src-pipeline-COMP-19 --> src-pipeline-COMP-21
    src-pipeline-COMP-18 --> src-pipeline-COMP-38
    src-pipeline-COMP-23 --> src-pipeline-COMP-20
    src-pipeline-COMP-27 --> src-pipeline-COMP-21
    src-pipeline-COMP-44 --> src-pipeline-COMP-21
    src-pipeline-COMP-23 --> src-pipeline-COMP-42
    src-pipeline-COMP-25 --> src-pipeline-COMP-40
    src-pipeline-COMP-23 --> src-pipeline-COMP-36
    src-pipeline-COMP-19 --> src-pipeline-COMP-33
    src-pipeline-COMP-23 --> src-pipeline-COMP-16
    src-pipeline-COMP-25 --> src-pipeline-COMP-46
    src-pipeline-COMP-30 --> src-pipeline-COMP-24
    src-pipeline-COMP-25 --> src-pipeline-COMP-24
    src-pipeline-COMP-27 --> src-pipeline-COMP-36
    src-pipeline-COMP-16 --> src-pipeline-COMP-24
    src-pipeline-COMP-40 --> src-pipeline-COMP-36
    src-pipeline-COMP-46 --> src-pipeline-COMP-38
    src-pipeline-COMP-27 --> src-pipeline-COMP-16
    src-pipeline-COMP-27 --> src-pipeline-COMP-33
    src-pipeline-COMP-44 --> src-pipeline-COMP-33
    src-pipeline-COMP-25 --> src-pipeline-COMP-19
    src-pipeline-COMP-38 --> src-pipeline-COMP-36
    src-core-COMP-26["Representativeness"]
    src-core-COMP-28["Source Block Assign"]
    src-core-COMP-26 --> src-core-COMP-28
    src-core-COMP-21["Decomposer"]
    src-core-COMP-24["Parser"]
    src-core-COMP-21 --> src-core-COMP-24
    src-core-COMP-25["Regen Readiness"]
    src-core-COMP-28 --> src-core-COMP-25
    src-core-COMP-27["Slicer"]
    src-core-COMP-28 --> src-core-COMP-27
    src-core-COMP-25 --> src-core-COMP-27
    src-core-COMP-18["Confidence"]
    src-core-COMP-18 --> src-core-COMP-24
    src-core-COMP-26 --> src-core-COMP-18
    src-core-COMP-23["Merger"]
    src-core-COMP-28 --> src-core-COMP-23
    src-core-COMP-25 --> src-core-COMP-23
    src-core-COMP-22["Differ"]
    src-core-COMP-21 --> src-core-COMP-22
    src-core-COMP-18 --> src-core-COMP-25
    src-core-COMP-18 --> src-core-COMP-27
    src-core-COMP-20["Coverage"]
    src-core-COMP-26 --> src-core-COMP-20
    src-core-COMP-30["Validator"]
    src-core-COMP-21 --> src-core-COMP-30
    src-core-COMP-15["Cluster"]
    src-core-COMP-26 --> src-core-COMP-15
    src-core-COMP-20 --> src-core-COMP-28
    src-core-COMP-28 --> src-core-COMP-24
    src-core-COMP-28 --> src-core-COMP-21
    src-core-COMP-25 --> src-core-COMP-21
    src-core-COMP-18 --> src-core-COMP-30
    src-core-COMP-31["Visualize"]
    src-core-COMP-28 --> src-core-COMP-31
    src-core-COMP-25 --> src-core-COMP-31
    src-core-COMP-17["Compression"]
    src-core-COMP-21 --> src-core-COMP-17
    src-core-COMP-28 --> src-core-COMP-22
    src-core-COMP-25 --> src-core-COMP-22
    src-core-COMP-30 --> src-core-COMP-28
    src-core-COMP-18 --> src-core-COMP-21
    src-core-COMP-21 --> src-core-COMP-31
    src-core-COMP-19["Corrections"]
    src-core-COMP-26 --> src-core-COMP-19
    src-core-COMP-18 --> src-core-COMP-17
    src-core-COMP-16["Completeness"]
    src-core-COMP-21 --> src-core-COMP-16
    src-core-COMP-28 --> src-core-COMP-30
    src-core-COMP-25 --> src-core-COMP-30
    src-core-COMP-21 --> src-core-COMP-28
    src-core-COMP-18 --> src-core-COMP-31
    src-core-COMP-26 --> src-core-COMP-25
    src-core-COMP-18 --> src-core-COMP-16
    src-core-COMP-26 --> src-core-COMP-27
    src-core-COMP-18 --> src-core-COMP-22
    src-core-COMP-18 --> src-core-COMP-28
    src-core-COMP-22 --> src-core-COMP-28
    src-core-COMP-26 --> src-core-COMP-23
    src-core-COMP-28 --> src-core-COMP-17
    src-core-COMP-25 --> src-core-COMP-17
    src-core-COMP-28 --> src-core-COMP-16
    src-core-COMP-25 --> src-core-COMP-16
    src-core-COMP-21 --> src-core-COMP-20
    src-core-COMP-25 --> src-core-COMP-28
    src-core-COMP-21 --> src-core-COMP-15
    src-core-COMP-26 --> src-core-COMP-24
    src-core-COMP-21 --> src-core-COMP-26
    src-core-COMP-26 --> src-core-COMP-21
    src-core-COMP-18 --> src-core-COMP-20
    src-core-COMP-18 --> src-core-COMP-26
    src-core-COMP-25 --> src-core-COMP-18
    src-core-COMP-28 --> src-core-COMP-18
    src-core-COMP-23 --> src-core-COMP-28
    src-core-COMP-26 --> src-core-COMP-31
    src-core-COMP-26 --> src-core-COMP-22
    src-core-COMP-21 --> src-core-COMP-18
    src-core-COMP-24 --> src-core-COMP-28
    src-core-COMP-21 --> src-core-COMP-19
    src-core-COMP-28 --> src-core-COMP-20
    src-core-COMP-25 --> src-core-COMP-20
    src-core-COMP-26 --> src-core-COMP-30
    src-core-COMP-28 --> src-core-COMP-15
    src-core-COMP-25 --> src-core-COMP-15
    src-core-COMP-28 --> src-core-COMP-26
    src-core-COMP-25 --> src-core-COMP-26
    src-core-COMP-18 --> src-core-COMP-19
    src-core-COMP-21 --> src-core-COMP-25
    src-core-COMP-21 --> src-core-COMP-27
    src-core-COMP-21 --> src-core-COMP-23
    src-core-COMP-18 --> src-core-COMP-15
    src-core-COMP-26 --> src-core-COMP-17
    src-core-COMP-25 --> src-core-COMP-24
    src-core-COMP-18 --> src-core-COMP-23
    src-core-COMP-28 --> src-core-COMP-19
    src-core-COMP-25 --> src-core-COMP-19
    src-core-COMP-26 --> src-core-COMP-16
    src-core-COMP-27 --> src-core-COMP-28
    src-manifest-COMP-19["Call Graph"]
    src-manifest-COMP-30["Scan Cache"]
    src-manifest-COMP-19 --> src-manifest-COMP-30
    src-manifest-COMP-32["Slicers"]
    src-manifest-COMP-27["Multi Scanner"]
    src-manifest-COMP-32 --> src-manifest-COMP-27
    src-manifest-COMP-26["Metrics"]
    src-manifest-COMP-28["Protocol"]
    src-manifest-COMP-26 --> src-manifest-COMP-28
    src-manifest-COMP-22["Generator"]
    src-manifest-COMP-23["Grouping"]
    src-manifest-COMP-22 --> src-manifest-COMP-23
    src-manifest-COMP-17["Blocks"]
    src-manifest-COMP-21["Display"]
    src-manifest-COMP-17 --> src-manifest-COMP-21
    src-manifest-COMP-24["Interfaces"]
    src-manifest-COMP-29["Recursive"]
    src-manifest-COMP-24 --> src-manifest-COMP-29
    src-manifest-COMP-27 --> src-manifest-COMP-32
    src-manifest-COMP-18["Body Hints"]
    src-manifest-COMP-23 --> src-manifest-COMP-18
    src-manifest-COMP-25["Kt Scanner"]
    src-manifest-COMP-25 --> src-manifest-COMP-27
    src-manifest-COMP-32 --> src-manifest-COMP-23
    src-manifest-COMP-23 --> src-manifest-COMP-19
    src-manifest-COMP-20["Chains"]
    src-manifest-COMP-29 --> src-manifest-COMP-20
    src-manifest-COMP-30 --> src-manifest-COMP-22
    src-manifest-COMP-16["Behavior"]
    src-manifest-COMP-17 --> src-manifest-COMP-16
    src-manifest-COMP-33["Ts Scanner"]
    src-manifest-COMP-17 --> src-manifest-COMP-33
    src-manifest-COMP-26 --> src-manifest-COMP-18
    src-manifest-COMP-29 --> src-manifest-COMP-26
    src-manifest-COMP-17 --> src-manifest-COMP-22
    src-manifest-COMP-25 --> src-manifest-COMP-23
    src-manifest-COMP-17 --> src-manifest-COMP-28
    src-manifest-COMP-24 --> src-manifest-COMP-18
    src-manifest-COMP-30 --> src-manifest-COMP-32
    src-manifest-COMP-22 --> src-manifest-COMP-24
    src-manifest-COMP-19 --> src-manifest-COMP-17
    src-manifest-COMP-24 --> src-manifest-COMP-19
    src-manifest-COMP-17 --> src-manifest-COMP-32
    src-manifest-COMP-19 --> src-manifest-COMP-26
    src-manifest-COMP-32 --> src-manifest-COMP-24
    src-manifest-COMP-27 --> src-manifest-COMP-20
    src-manifest-COMP-19 --> src-manifest-COMP-16
    src-manifest-COMP-26 --> src-manifest-COMP-20
    src-manifest-COMP-23 --> src-manifest-COMP-29
    src-manifest-COMP-22 --> src-manifest-COMP-25
    src-manifest-COMP-24 --> src-manifest-COMP-25
    src-manifest-COMP-27 --> src-manifest-COMP-26
    src-manifest-COMP-19 --> src-manifest-COMP-28
    src-manifest-COMP-22 --> src-manifest-COMP-27
    src-manifest-COMP-24 --> src-manifest-COMP-27
    src-manifest-COMP-27 --> src-manifest-COMP-29
    src-manifest-COMP-29 --> src-manifest-COMP-24
    src-manifest-COMP-25 --> src-manifest-COMP-21
    src-manifest-COMP-26 --> src-manifest-COMP-29
    src-manifest-COMP-29 --> src-manifest-COMP-19
    src-manifest-COMP-30 --> src-manifest-COMP-17
    src-manifest-COMP-24 --> src-manifest-COMP-23
    src-manifest-COMP-32 --> src-manifest-COMP-22
    src-manifest-COMP-17 --> src-manifest-COMP-20
    src-manifest-COMP-19 --> src-manifest-COMP-18
    src-manifest-COMP-23 --> src-manifest-COMP-24
    src-manifest-COMP-29 --> src-manifest-COMP-25
    src-manifest-COMP-30 --> src-manifest-COMP-16
    src-manifest-COMP-30 --> src-manifest-COMP-33
    src-manifest-COMP-25 --> src-manifest-COMP-33
    src-manifest-COMP-17 --> src-manifest-COMP-26
    src-manifest-COMP-29 --> src-manifest-COMP-27
    src-manifest-COMP-25 --> src-manifest-COMP-22
    src-manifest-COMP-27 --> src-manifest-COMP-18
    src-manifest-COMP-30 --> src-manifest-COMP-28
    src-manifest-COMP-32 --> src-manifest-COMP-30
    src-manifest-COMP-17 --> src-manifest-COMP-29
    src-manifest-COMP-27 --> src-manifest-COMP-19
    src-manifest-COMP-26 --> src-manifest-COMP-19
    src-manifest-COMP-29 --> src-manifest-COMP-23
    src-manifest-COMP-18 --> src-manifest-COMP-17
    src-manifest-COMP-23 --> src-manifest-COMP-25
    src-manifest-COMP-25 --> src-manifest-COMP-32
    src-manifest-COMP-25 --> src-manifest-COMP-30
    src-manifest-COMP-19 --> src-manifest-COMP-20
    src-manifest-COMP-23 --> src-manifest-COMP-27
    src-manifest-COMP-22 --> src-manifest-COMP-21
    src-manifest-COMP-27 --> src-manifest-COMP-25
    src-manifest-COMP-30 --> src-manifest-COMP-18
    src-manifest-COMP-22 --> src-manifest-COMP-17
    src-manifest-COMP-26 --> src-manifest-COMP-25
    src-manifest-COMP-19 --> src-manifest-COMP-23
    src-manifest-COMP-17 --> src-manifest-COMP-18
    src-manifest-COMP-26 --> src-manifest-COMP-27
    src-manifest-COMP-19 --> src-manifest-COMP-29
    src-manifest-COMP-32 --> src-manifest-COMP-21
    src-manifest-COMP-32 --> src-manifest-COMP-17
    src-manifest-COMP-17 --> src-manifest-COMP-19
    src-manifest-COMP-22 --> src-manifest-COMP-16
    src-manifest-COMP-22 --> src-manifest-COMP-33
    src-manifest-COMP-27 --> src-manifest-COMP-23
    src-manifest-COMP-24 --> src-manifest-COMP-22
    src-manifest-COMP-22 --> src-manifest-COMP-28
    src-manifest-COMP-26 --> src-manifest-COMP-23
    src-manifest-COMP-29 --> src-manifest-COMP-21
    src-manifest-COMP-25 --> src-manifest-COMP-17
    src-manifest-COMP-30 --> src-manifest-COMP-20
    src-manifest-COMP-32 --> src-manifest-COMP-16
    src-manifest-COMP-32 --> src-manifest-COMP-33
    src-manifest-COMP-17 --> src-manifest-COMP-25
    src-manifest-COMP-22 --> src-manifest-COMP-32
    src-manifest-COMP-30 --> src-manifest-COMP-26
    src-manifest-COMP-22 --> src-manifest-COMP-30
    src-manifest-COMP-24 --> src-manifest-COMP-30
    src-manifest-COMP-32 --> src-manifest-COMP-28
    src-manifest-COMP-19 --> src-manifest-COMP-24
    src-manifest-COMP-25 --> src-manifest-COMP-16
    src-manifest-COMP-30 --> src-manifest-COMP-29
    src-manifest-COMP-23 --> src-manifest-COMP-21
    src-manifest-COMP-29 --> src-manifest-COMP-33
    src-manifest-COMP-25 --> src-manifest-COMP-28
    src-manifest-COMP-27 --> src-manifest-COMP-24
    src-manifest-COMP-17 --> src-manifest-COMP-23
    src-manifest-COMP-29 --> src-manifest-COMP-22
    src-manifest-COMP-26 --> src-manifest-COMP-24
    src-manifest-COMP-19 --> src-manifest-COMP-25
    src-manifest-COMP-26 --> src-manifest-COMP-21
    src-manifest-COMP-19 --> src-manifest-COMP-27
    src-manifest-COMP-29 --> src-manifest-COMP-32
    src-manifest-COMP-29 --> src-manifest-COMP-30
    src-manifest-COMP-23 --> src-manifest-COMP-33
    src-manifest-COMP-24 --> src-manifest-COMP-21
    src-manifest-COMP-23 --> src-manifest-COMP-22
    src-manifest-COMP-25 --> src-manifest-COMP-18
    src-manifest-COMP-23 --> src-manifest-COMP-28
    src-manifest-COMP-24 --> src-manifest-COMP-17
    src-manifest-COMP-22 --> src-manifest-COMP-20
    src-manifest-COMP-30 --> src-manifest-COMP-19
    src-manifest-COMP-27 --> src-manifest-COMP-22
    src-manifest-COMP-17 --> src-manifest-COMP-24
    src-manifest-COMP-22 --> src-manifest-COMP-26
    src-manifest-COMP-23 --> src-manifest-COMP-32
    src-manifest-COMP-26 --> src-manifest-COMP-22
    src-manifest-COMP-23 --> src-manifest-COMP-30
    src-manifest-COMP-27 --> src-manifest-COMP-28
    src-manifest-COMP-32 --> src-manifest-COMP-20
    src-manifest-COMP-24 --> src-manifest-COMP-16
    src-manifest-COMP-22 --> src-manifest-COMP-29
    src-manifest-COMP-24 --> src-manifest-COMP-33
    src-manifest-COMP-30 --> src-manifest-COMP-25
    src-manifest-COMP-24 --> src-manifest-COMP-28
    src-manifest-COMP-27 --> src-manifest-COMP-30
    src-manifest-COMP-32 --> src-manifest-COMP-26
    src-manifest-COMP-30 --> src-manifest-COMP-27
    src-manifest-COMP-25 --> src-manifest-COMP-20
    src-manifest-COMP-26 --> src-manifest-COMP-32
    src-manifest-COMP-26 --> src-manifest-COMP-30
    src-manifest-COMP-29 --> src-manifest-COMP-17
    src-manifest-COMP-32 --> src-manifest-COMP-29
    src-manifest-COMP-17 --> src-manifest-COMP-27
    src-manifest-COMP-24 --> src-manifest-COMP-32
    src-manifest-COMP-25 --> src-manifest-COMP-26
    src-manifest-COMP-30 --> src-manifest-COMP-23
    src-manifest-COMP-25 --> src-manifest-COMP-29
    src-manifest-COMP-19 --> src-manifest-COMP-21
    src-manifest-COMP-22 --> src-manifest-COMP-18
    src-manifest-COMP-29 --> src-manifest-COMP-16
    src-manifest-COMP-23 --> src-manifest-COMP-17
    src-manifest-COMP-23 --> src-manifest-COMP-20
    src-manifest-COMP-22 --> src-manifest-COMP-19
    src-manifest-COMP-29 --> src-manifest-COMP-28
    src-manifest-COMP-27 --> src-manifest-COMP-21
    src-manifest-COMP-17 --> src-manifest-COMP-30
    src-manifest-COMP-32 --> src-manifest-COMP-18
    src-manifest-COMP-27 --> src-manifest-COMP-17
    src-manifest-COMP-23 --> src-manifest-COMP-26
    src-manifest-COMP-26 --> src-manifest-COMP-17
    src-manifest-COMP-32 --> src-manifest-COMP-19
    src-manifest-COMP-19 --> src-manifest-COMP-33
    src-manifest-COMP-23 --> src-manifest-COMP-16
    src-manifest-COMP-19 --> src-manifest-COMP-22
    src-manifest-COMP-30 --> src-manifest-COMP-24
    src-manifest-COMP-25 --> src-manifest-COMP-24
    src-manifest-COMP-24 --> src-manifest-COMP-20
    src-manifest-COMP-29 --> src-manifest-COMP-18
    src-manifest-COMP-27 --> src-manifest-COMP-16
    src-manifest-COMP-27 --> src-manifest-COMP-33
    src-manifest-COMP-25 --> src-manifest-COMP-19
    src-manifest-COMP-30 --> src-manifest-COMP-21
    src-manifest-COMP-26 --> src-manifest-COMP-16
    src-manifest-COMP-26 --> src-manifest-COMP-33
    src-manifest-COMP-32 --> src-manifest-COMP-25
    src-manifest-COMP-24 --> src-manifest-COMP-26
    src-manifest-COMP-19 --> src-manifest-COMP-32
    src-orchestration-COMP-11["Pipeline"]
    src-orchestration-COMP-8["Enrich"]
    src-orchestration-COMP-11 --> src-orchestration-COMP-8
    src-orchestration-COMP-4["Capability Inference"]
    src-orchestration-COMP-11 --> src-orchestration-COMP-4
    src-orchestration-COMP-10["Naming Context"]
    src-orchestration-COMP-12["Trigger Detection"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-12
    src-orchestration-COMP-6["Decompose"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-6
    src-orchestration-COMP-1["Auto Enrich"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-1
    src-orchestration-COMP-9["Enrichment Context"]
    src-orchestration-COMP-9 --> src-orchestration-COMP-1
    src-orchestration-COMP-9 --> src-orchestration-COMP-12
    src-orchestration-COMP-9 --> src-orchestration-COMP-6
    src-orchestration-COMP-3["Behavior Flows"]
    src-orchestration-COMP-11 --> src-orchestration-COMP-3
    src-orchestration-COMP-11 --> src-orchestration-COMP-9
    src-orchestration-COMP-11 --> src-orchestration-COMP-10
    src-orchestration-COMP-13["Use Case Inference"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-13
    src-orchestration-COMP-2["Behavior Decompose"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-2
    src-orchestration-COMP-5["Compaction"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-5
    src-orchestration-COMP-9 --> src-orchestration-COMP-13
    src-orchestration-COMP-10 --> src-orchestration-COMP-11
    src-orchestration-COMP-9 --> src-orchestration-COMP-5
    src-orchestration-COMP-9 --> src-orchestration-COMP-2
    src-orchestration-COMP-9 --> src-orchestration-COMP-11
    src-orchestration-COMP-7["Deep Decompose"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-7
    src-orchestration-COMP-9 --> src-orchestration-COMP-7
    src-orchestration-COMP-11 --> src-orchestration-COMP-12
    src-orchestration-COMP-11 --> src-orchestration-COMP-1
    src-orchestration-COMP-11 --> src-orchestration-COMP-6
    src-orchestration-COMP-10 --> src-orchestration-COMP-8
    src-orchestration-COMP-10 --> src-orchestration-COMP-4
    src-orchestration-COMP-10 --> src-orchestration-COMP-3
    src-orchestration-COMP-9 --> src-orchestration-COMP-8
    src-orchestration-COMP-9 --> src-orchestration-COMP-4
    src-orchestration-COMP-11 --> src-orchestration-COMP-13
    src-orchestration-COMP-10 --> src-orchestration-COMP-9
    src-orchestration-COMP-9 --> src-orchestration-COMP-3
    src-orchestration-COMP-11 --> src-orchestration-COMP-5
    src-orchestration-COMP-11 --> src-orchestration-COMP-2
    src-orchestration-COMP-9 --> src-orchestration-COMP-10
    src-orchestration-COMP-11 --> src-orchestration-COMP-7
```

---

---