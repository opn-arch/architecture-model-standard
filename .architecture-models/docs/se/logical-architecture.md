---
document: Logical Architecture
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T20:06:03Z
generator_version: 0.3.0
model_hash: 41fb0d4bec16
edition: 5
---

> **Model Completeness: F (14%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 92/92 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Logical Architecture: System

## Layer Structure

| Order | Layer | Technologies | Directories |
|-------|-------|-------------|-------------|
| 0 | infra | — | — |
| 0 | data | — | — |

## Component Allocation

### data

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Scripts (core) (COMP-3-1) | service | 6 files | — |
| Scripts (dev_simulation) (COMP-3-2) | service | 10 files | — |

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Checkout (scripts-dev-simulation-COMP-1) | service | 1 files | — |
| Cohesion (scripts-dev-simulation-COMP-2) | service | 1 files | — |
| Drift Tracker (scripts-dev-simulation-COMP-3) | service | 1 files | — |
| Extractor (scripts-dev-simulation-COMP-4) | service | 1 files | — |
| Llm Predictor (scripts-dev-simulation-COMP-5) | service | 1 files | — |
| Regen Scorer (scripts-dev-simulation-COMP-6) | service | 1 files | — |
| Report (scripts-dev-simulation-COMP-7) | service | 1 files | — |
| Runner (scripts-dev-simulation-COMP-8) | service | 1 files | — |
| Slice Evaluator (scripts-dev-simulation-COMP-9) | service | 1 files | — |
| Infrastructure (scripts-dev-simulation-COMP-10) | service | 1 files | — |
| Allocate (src-pipeline-COMP-16) | service | 2 files | — |
| Artifacts (src-pipeline-COMP-18) | service | 1 files | — |
| Cache (src-pipeline-COMP-19) | service | 1 files | — |
| Context Gen (src-pipeline-COMP-20) | service | 1 files | — |
| Contract (src-pipeline-COMP-21) | service | 2 files | — |
| Coordinator (src-pipeline-COMP-23) | service | 1 files | — |
| Corrections (src-pipeline-COMP-24) | service | 1 files | — |
| Decompose (src-pipeline-COMP-25) | service | 3 files | — |
| Emit (src-pipeline-COMP-27) | service | 2 files | — |
| Global Learning (src-pipeline-COMP-29) | service | 2 files | — |
| Infer (src-pipeline-COMP-30) | service | 2 files | — |
| Lessons (src-pipeline-COMP-33) | service | 1 files | — |
| Observe (src-pipeline-COMP-34) | service | 2 files | — |
| Protocol (src-pipeline-COMP-36) | service | 1 files | — |
| Regen Score (src-pipeline-COMP-37) | service | 1 files | — |
| Relate (src-pipeline-COMP-38) | service | 2 files | — |
| Report (src-pipeline-COMP-40) | service | 1 files | — |
| Requirements Derive (src-pipeline-COMP-41) | service | 1 files | — |
| Specify (src-pipeline-COMP-42) | service | 2 files | — |
| Synthesize (src-pipeline-COMP-44) | service | 2 files | — |
| Validate (src-pipeline-COMP-46) | service | 2 files | — |
| Cluster (src-core-COMP-15) | service | 1 files | — |
| Completeness (src-core-COMP-16) | service | 1 files | — |
| Compression (src-core-COMP-17) | service | 1 files | — |
| Confidence (src-core-COMP-18) | service | 1 files | — |
| Corrections (src-core-COMP-19) | service | 1 files | — |
| Coverage (src-core-COMP-20) | service | 1 files | — |
| Decomposer (src-core-COMP-21) | service | 1 files | — |
| Differ (src-core-COMP-22) | service | 1 files | — |
| Merger (src-core-COMP-23) | service | 1 files | — |
| Parser (src-core-COMP-24) | service | 1 files | — |
| Regen Readiness (src-core-COMP-25) | service | 1 files | — |
| Representativeness (src-core-COMP-26) | service | 1 files | — |
| Slicer (src-core-COMP-27) | service | 1 files | — |
| Source Block Assign (src-core-COMP-28) | service | 3 files | — |
| Validator (src-core-COMP-30) | service | 1 files | — |
| Visualize (src-core-COMP-31) | service | 1 files | — |
| Behavior (src-manifest-COMP-16) | service | 1 files | — |
| Blocks (src-manifest-COMP-17) | service | 3 files | — |
| Body Hints (src-manifest-COMP-18) | service | 1 files | — |
| Call Graph (src-manifest-COMP-19) | service | 1 files | — |
| Chains (src-manifest-COMP-20) | service | 1 files | — |
| Display (src-manifest-COMP-21) | service | 1 files | — |
| Generator (src-manifest-COMP-22) | service | 1 files | — |
| Grouping (src-manifest-COMP-23) | service | 1 files | — |
| Interfaces (src-manifest-COMP-24) | service | 1 files | — |
| Kt Scanner (src-manifest-COMP-25) | service | 2 files | — |
| Metrics (src-manifest-COMP-26) | service | 1 files | — |
| Multi Scanner (src-manifest-COMP-27) | service | 1 files | — |
| Protocol (src-manifest-COMP-28) | service | 1 files | — |
| Recursive (src-manifest-COMP-29) | service | 1 files | — |
| Scan Cache (src-manifest-COMP-30) | service | 1 files | — |
| Slicers (src-manifest-COMP-32) | service | 1 files | — |
| Ts Scanner (src-manifest-COMP-33) | service | 1 files | — |
| Auto Enrich (src-orchestration-COMP-1) | service | 1 files | — |
| Behavior Decompose (src-orchestration-COMP-2) | service | 1 files | — |
| Behavior Flows (src-orchestration-COMP-3) | service | 1 files | — |
| Capability Inference (src-orchestration-COMP-4) | service | 1 files | — |
| Compaction (src-orchestration-COMP-5) | service | 1 files | — |
| Decompose (src-orchestration-COMP-6) | service | 1 files | — |
| Deep Decompose (src-orchestration-COMP-7) | service | 1 files | — |
| Enrich (src-orchestration-COMP-8) | service | 1 files | — |
| Enrichment Context (src-orchestration-COMP-9) | service | 1 files | — |
| Naming Context (src-orchestration-COMP-10) | service | 1 files | — |
| Pipeline (src-orchestration-COMP-11) | service | 1 files | — |
| Trigger Detection (src-orchestration-COMP-12) | service | 1 files | — |
| Use Case Inference (src-orchestration-COMP-13) | service | 1 files | — |

### web

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Architecture Model Monitoring (COMP-4-1) | service | 5 files | — |
| Src (pipeline) (COMP-4-2) | service | 33 files | — |
| Core Analysis Engine (COMP-4-3) | service | 18 files | — |
| Src (config) (COMP-4-4) | service | 3 files | — |
| Src (manifest) (COMP-4-5) | service | 20 files | — |
| Src (utils) (COMP-4-6) | service | 1 files | — |
| CLI Interface Layer (COMP-4-7) | service | 2 files | — |
| Src (authoring) (COMP-4-8) | service | 2 files | — |
| Src (persistence) (COMP-4-9) | service | 2 files | — |
| Src (orchestration) (COMP-4-10) | service | 13 files | — |
| Src (extract) (COMP-4-11) | service | 5 files | — |
| Src (profiles) (COMP-4-12) | service | 1 files | — |
| Src (export) (COMP-4-13) | service | 2 files | — |

## Inter-Component Interfaces

| Interface | Type | Protocol | Provider | Consumer |
|-----------|------|----------|----------|----------|
| runner CLI | internal | — | — | — |

## Dependency Graph

```mermaid
graph TD
    scripts-dev-simulation-COMP-10["Infrastructure"]
    scripts-dev-simulation-COMP-8["Runner"]
    scripts-dev-simulation-COMP-10 --> scripts-dev-simulation-COMP-8
    src-pipeline-COMP-20["Context Gen"]
    src-pipeline-COMP-30["Infer"]
    src-pipeline-COMP-20 --> src-pipeline-COMP-30
    src-pipeline-COMP-33["Lessons"]
    src-pipeline-COMP-36["Protocol"]
    src-pipeline-COMP-33 --> src-pipeline-COMP-36
    src-pipeline-COMP-37["Regen Score"]
    src-pipeline-COMP-37 --> src-pipeline-COMP-36
    src-pipeline-COMP-25["Decompose"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-33
    src-pipeline-COMP-38["Relate"]
    src-pipeline-COMP-16["Allocate"]
    src-pipeline-COMP-38 --> src-pipeline-COMP-16
    src-pipeline-COMP-44["Synthesize"]
    src-pipeline-COMP-44 --> src-pipeline-COMP-30
    src-pipeline-COMP-21["Contract"]
    src-pipeline-COMP-21 --> src-pipeline-COMP-16
    src-pipeline-COMP-20 --> src-pipeline-COMP-16
    src-pipeline-COMP-34["Observe"]
    src-pipeline-COMP-30 --> src-pipeline-COMP-34
    src-pipeline-COMP-40["Report"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-40
    src-pipeline-COMP-42["Specify"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-42
    src-pipeline-COMP-19["Cache"]
    src-pipeline-COMP-19 --> src-pipeline-COMP-33
    src-pipeline-COMP-38 --> src-pipeline-COMP-34
    src-pipeline-COMP-29["Global Learning"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-29
    src-pipeline-COMP-21 --> src-pipeline-COMP-34
    src-pipeline-COMP-27["Emit"]
    src-pipeline-COMP-27 --> src-pipeline-COMP-16
    src-pipeline-COMP-20 --> src-pipeline-COMP-34
    src-pipeline-COMP-19 --> src-pipeline-COMP-40
    src-pipeline-COMP-23["Coordinator"]
    src-pipeline-COMP-23 --> src-pipeline-COMP-20
    src-pipeline-COMP-19 --> src-pipeline-COMP-42
    src-pipeline-COMP-25 --> src-pipeline-COMP-21
    src-pipeline-COMP-27 --> src-pipeline-COMP-34
    src-pipeline-COMP-16 --> src-pipeline-COMP-30
    src-pipeline-COMP-23 --> src-pipeline-COMP-44
    src-pipeline-COMP-23 --> src-pipeline-COMP-36
    src-pipeline-COMP-27 --> src-pipeline-COMP-33
    src-pipeline-COMP-23 --> src-pipeline-COMP-38
    src-pipeline-COMP-18["Artifacts"]
    src-pipeline-COMP-46["Validate"]
    src-pipeline-COMP-18 --> src-pipeline-COMP-46
    src-pipeline-COMP-19 --> src-pipeline-COMP-46
    src-pipeline-COMP-24["Corrections"]
    src-pipeline-COMP-23 --> src-pipeline-COMP-24
    src-pipeline-COMP-20 --> src-pipeline-COMP-36
    src-pipeline-COMP-27 --> src-pipeline-COMP-19
    src-pipeline-COMP-27 --> src-pipeline-COMP-24
    src-pipeline-COMP-19 --> src-pipeline-COMP-25
    src-pipeline-COMP-41["Requirements Derive"]
    src-pipeline-COMP-25 --> src-pipeline-COMP-41
    src-pipeline-COMP-27 --> src-pipeline-COMP-40
    src-pipeline-COMP-25 --> src-pipeline-COMP-18
    src-pipeline-COMP-44 --> src-pipeline-COMP-36
    src-pipeline-COMP-42 --> src-pipeline-COMP-36
    src-pipeline-COMP-25 --> src-pipeline-COMP-23
    src-pipeline-COMP-25 --> src-pipeline-COMP-20
    src-pipeline-COMP-44 --> src-pipeline-COMP-24
    src-pipeline-COMP-19 --> src-pipeline-COMP-41
    src-pipeline-COMP-19 --> src-pipeline-COMP-18
    src-pipeline-COMP-19 --> src-pipeline-COMP-23
    src-pipeline-COMP-27 --> src-pipeline-COMP-46
    src-pipeline-COMP-46 --> src-pipeline-COMP-38
    src-pipeline-COMP-25 --> src-pipeline-COMP-27
    src-pipeline-COMP-23 --> src-pipeline-COMP-16
    src-pipeline-COMP-25 --> src-pipeline-COMP-38
    src-pipeline-COMP-16 --> src-pipeline-COMP-36
    src-pipeline-COMP-23 --> src-pipeline-COMP-34
    src-pipeline-COMP-27 --> src-pipeline-COMP-37
    src-pipeline-COMP-27 --> src-pipeline-COMP-18
    src-pipeline-COMP-46 --> src-pipeline-COMP-30
    src-pipeline-COMP-34 --> src-pipeline-COMP-36
    src-pipeline-COMP-16 --> src-pipeline-COMP-24
    src-pipeline-COMP-44 --> src-pipeline-COMP-16
    src-pipeline-COMP-42 --> src-pipeline-COMP-16
    src-pipeline-COMP-25 --> src-pipeline-COMP-30
    src-pipeline-COMP-18 --> src-pipeline-COMP-42
    src-pipeline-COMP-19 --> src-pipeline-COMP-29
    src-pipeline-COMP-44 --> src-pipeline-COMP-34
    src-pipeline-COMP-42 --> src-pipeline-COMP-34
    src-pipeline-COMP-46 --> src-pipeline-COMP-16
    src-pipeline-COMP-18 --> src-pipeline-COMP-21
    src-pipeline-COMP-19 --> src-pipeline-COMP-21
    src-pipeline-COMP-44 --> src-pipeline-COMP-19
    src-pipeline-COMP-29 --> src-pipeline-COMP-36
    src-pipeline-COMP-44 --> src-pipeline-COMP-40
    src-pipeline-COMP-27 --> src-pipeline-COMP-42
    src-pipeline-COMP-23 --> src-pipeline-COMP-46
    src-pipeline-COMP-27 --> src-pipeline-COMP-29
    src-pipeline-COMP-40 --> src-pipeline-COMP-36
    src-pipeline-COMP-20 --> src-pipeline-COMP-46
    src-pipeline-COMP-16 --> src-pipeline-COMP-34
    src-pipeline-COMP-46 --> src-pipeline-COMP-36
    src-pipeline-COMP-44 --> src-pipeline-COMP-46
    src-pipeline-COMP-19 --> src-pipeline-COMP-20
    src-pipeline-COMP-27 --> src-pipeline-COMP-21
    src-pipeline-COMP-23 --> src-pipeline-COMP-37
    src-pipeline-COMP-25 --> src-pipeline-COMP-44
    src-pipeline-COMP-25 --> src-pipeline-COMP-36
    src-pipeline-COMP-27 --> src-pipeline-COMP-25
    src-pipeline-COMP-25 --> src-pipeline-COMP-24
    src-pipeline-COMP-19 --> src-pipeline-COMP-27
    src-pipeline-COMP-19 --> src-pipeline-COMP-44
    src-pipeline-COMP-19 --> src-pipeline-COMP-36
    src-pipeline-COMP-44 --> src-pipeline-COMP-37
    src-pipeline-COMP-27 --> src-pipeline-COMP-41
    src-pipeline-COMP-18 --> src-pipeline-COMP-38
    src-pipeline-COMP-19 --> src-pipeline-COMP-38
    src-pipeline-COMP-44 --> src-pipeline-COMP-18
    src-pipeline-COMP-23 --> src-pipeline-COMP-33
    src-pipeline-COMP-27 --> src-pipeline-COMP-23
    src-pipeline-COMP-27 --> src-pipeline-COMP-20
    src-pipeline-COMP-23 --> src-pipeline-COMP-19
    src-pipeline-COMP-23 --> src-pipeline-COMP-40
    src-pipeline-COMP-23 --> src-pipeline-COMP-42
    src-pipeline-COMP-18 --> src-pipeline-COMP-30
    src-pipeline-COMP-19 --> src-pipeline-COMP-30
    src-pipeline-COMP-23 --> src-pipeline-COMP-29
    src-pipeline-COMP-44 --> src-pipeline-COMP-33
    src-pipeline-COMP-27 --> src-pipeline-COMP-44
    src-pipeline-COMP-25 --> src-pipeline-COMP-16
    src-pipeline-COMP-38 --> src-pipeline-COMP-30
    src-pipeline-COMP-27 --> src-pipeline-COMP-38
    src-pipeline-COMP-44 --> src-pipeline-COMP-42
    src-pipeline-COMP-18 --> src-pipeline-COMP-16
    src-pipeline-COMP-19 --> src-pipeline-COMP-16
    src-pipeline-COMP-23 --> src-pipeline-COMP-21
    src-pipeline-COMP-25 --> src-pipeline-COMP-34
    src-pipeline-COMP-44 --> src-pipeline-COMP-29
    src-pipeline-COMP-23 --> src-pipeline-COMP-25
    src-pipeline-COMP-25 --> src-pipeline-COMP-19
    src-pipeline-COMP-27 --> src-pipeline-COMP-30
    src-pipeline-COMP-18 --> src-pipeline-COMP-34
    src-pipeline-COMP-19 --> src-pipeline-COMP-34
    src-pipeline-COMP-44 --> src-pipeline-COMP-21
    src-pipeline-COMP-23 --> src-pipeline-COMP-41
    src-pipeline-COMP-23 --> src-pipeline-COMP-18
    src-pipeline-COMP-44 --> src-pipeline-COMP-25
    src-pipeline-COMP-18 --> src-pipeline-COMP-36
    src-pipeline-COMP-44 --> src-pipeline-COMP-41
    src-pipeline-COMP-25 --> src-pipeline-COMP-46
    src-pipeline-COMP-30 --> src-pipeline-COMP-36
    src-pipeline-COMP-19 --> src-pipeline-COMP-24
    src-pipeline-COMP-23 --> src-pipeline-COMP-27
    src-pipeline-COMP-38 --> src-pipeline-COMP-36
    src-pipeline-COMP-44 --> src-pipeline-COMP-23
    src-pipeline-COMP-30 --> src-pipeline-COMP-24
    src-pipeline-COMP-44 --> src-pipeline-COMP-20
    src-pipeline-COMP-21 --> src-pipeline-COMP-36
    src-pipeline-COMP-20 --> src-pipeline-COMP-38
    src-pipeline-COMP-25 --> src-pipeline-COMP-37
    src-pipeline-COMP-44 --> src-pipeline-COMP-27
    src-pipeline-COMP-27 --> src-pipeline-COMP-36
    src-pipeline-COMP-44 --> src-pipeline-COMP-38
    src-pipeline-COMP-23 --> src-pipeline-COMP-30
    src-pipeline-COMP-19 --> src-pipeline-COMP-37
    src-core-COMP-21["Decomposer"]
    src-core-COMP-17["Compression"]
    src-core-COMP-21 --> src-core-COMP-17
    src-core-COMP-28["Source Block Assign"]
    src-core-COMP-28 --> src-core-COMP-17
    src-core-COMP-26["Representativeness"]
    src-core-COMP-21 --> src-core-COMP-26
    src-core-COMP-18["Confidence"]
    src-core-COMP-18 --> src-core-COMP-28
    src-core-COMP-15["Cluster"]
    src-core-COMP-28 --> src-core-COMP-15
    src-core-COMP-16["Completeness"]
    src-core-COMP-21 --> src-core-COMP-16
    src-core-COMP-28 --> src-core-COMP-16
    src-core-COMP-19["Corrections"]
    src-core-COMP-18 --> src-core-COMP-19
    src-core-COMP-22["Differ"]
    src-core-COMP-26 --> src-core-COMP-22
    src-core-COMP-26 --> src-core-COMP-28
    src-core-COMP-21 --> src-core-COMP-19
    src-core-COMP-25["Regen Readiness"]
    src-core-COMP-25 --> src-core-COMP-21
    src-core-COMP-18 --> src-core-COMP-25
    src-core-COMP-25 --> src-core-COMP-18
    src-core-COMP-25 --> src-core-COMP-22
    src-core-COMP-23["Merger"]
    src-core-COMP-25 --> src-core-COMP-23
    src-core-COMP-20["Coverage"]
    src-core-COMP-25 --> src-core-COMP-20
    src-core-COMP-31["Visualize"]
    src-core-COMP-28 --> src-core-COMP-31
    src-core-COMP-28 --> src-core-COMP-26
    src-core-COMP-18 --> src-core-COMP-22
    src-core-COMP-26 --> src-core-COMP-21
    src-core-COMP-18 --> src-core-COMP-23
    src-core-COMP-27["Slicer"]
    src-core-COMP-25 --> src-core-COMP-27
    src-core-COMP-30["Validator"]
    src-core-COMP-30 --> src-core-COMP-28
    src-core-COMP-26 --> src-core-COMP-25
    src-core-COMP-21 --> src-core-COMP-22
    src-core-COMP-21 --> src-core-COMP-28
    src-core-COMP-20 --> src-core-COMP-28
    src-core-COMP-26 --> src-core-COMP-18
    src-core-COMP-26 --> src-core-COMP-23
    src-core-COMP-25 --> src-core-COMP-30
    src-core-COMP-26 --> src-core-COMP-20
    src-core-COMP-27 --> src-core-COMP-28
    src-core-COMP-28 --> src-core-COMP-19
    src-core-COMP-26 --> src-core-COMP-27
    src-core-COMP-18 --> src-core-COMP-21
    src-core-COMP-28 --> src-core-COMP-21
    src-core-COMP-21 --> src-core-COMP-25
    src-core-COMP-26 --> src-core-COMP-30
    src-core-COMP-28 --> src-core-COMP-25
    src-core-COMP-18 --> src-core-COMP-20
    src-core-COMP-26 --> src-core-COMP-15
    src-core-COMP-21 --> src-core-COMP-18
    src-core-COMP-28 --> src-core-COMP-18
    src-core-COMP-22 --> src-core-COMP-28
    src-core-COMP-23 --> src-core-COMP-28
    src-core-COMP-24["Parser"]
    src-core-COMP-25 --> src-core-COMP-24
    src-core-COMP-21 --> src-core-COMP-23
    src-core-COMP-28 --> src-core-COMP-22
    src-core-COMP-21 --> src-core-COMP-20
    src-core-COMP-28 --> src-core-COMP-23
    src-core-COMP-18 --> src-core-COMP-27
    src-core-COMP-21 --> src-core-COMP-27
    src-core-COMP-28 --> src-core-COMP-27
    src-core-COMP-25 --> src-core-COMP-17
    src-core-COMP-18 --> src-core-COMP-30
    src-core-COMP-25 --> src-core-COMP-15
    src-core-COMP-25 --> src-core-COMP-16
    src-core-COMP-26 --> src-core-COMP-24
    src-core-COMP-21 --> src-core-COMP-30
    src-core-COMP-18 --> src-core-COMP-15
    src-core-COMP-28 --> src-core-COMP-30
    src-core-COMP-18 --> src-core-COMP-16
    src-core-COMP-24 --> src-core-COMP-28
    src-core-COMP-21 --> src-core-COMP-15
    src-core-COMP-26 --> src-core-COMP-31
    src-core-COMP-25 --> src-core-COMP-19
    src-core-COMP-26 --> src-core-COMP-17
    src-core-COMP-26 --> src-core-COMP-16
    src-core-COMP-28 --> src-core-COMP-20
    src-core-COMP-18 --> src-core-COMP-24
    src-core-COMP-25 --> src-core-COMP-31
    src-core-COMP-26 --> src-core-COMP-19
    src-core-COMP-25 --> src-core-COMP-26
    src-core-COMP-21 --> src-core-COMP-24
    src-core-COMP-28 --> src-core-COMP-24
    src-core-COMP-18 --> src-core-COMP-31
    src-core-COMP-18 --> src-core-COMP-17
    src-core-COMP-18 --> src-core-COMP-26
    src-core-COMP-25 --> src-core-COMP-28
    src-core-COMP-21 --> src-core-COMP-31
    src-manifest-COMP-32["Slicers"]
    src-manifest-COMP-18["Body Hints"]
    src-manifest-COMP-32 --> src-manifest-COMP-18
    src-manifest-COMP-24["Interfaces"]
    src-manifest-COMP-22["Generator"]
    src-manifest-COMP-24 --> src-manifest-COMP-22
    src-manifest-COMP-21["Display"]
    src-manifest-COMP-22 --> src-manifest-COMP-21
    src-manifest-COMP-23["Grouping"]
    src-manifest-COMP-24 --> src-manifest-COMP-23
    src-manifest-COMP-19["Call Graph"]
    src-manifest-COMP-28["Protocol"]
    src-manifest-COMP-19 --> src-manifest-COMP-28
    src-manifest-COMP-17["Blocks"]
    src-manifest-COMP-17 --> src-manifest-COMP-18
    src-manifest-COMP-32 --> src-manifest-COMP-22
    src-manifest-COMP-30["Scan Cache"]
    src-manifest-COMP-16["Behavior"]
    src-manifest-COMP-30 --> src-manifest-COMP-16
    src-manifest-COMP-32 --> src-manifest-COMP-23
    src-manifest-COMP-17 --> src-manifest-COMP-22
    src-manifest-COMP-25["Kt Scanner"]
    src-manifest-COMP-33["Ts Scanner"]
    src-manifest-COMP-25 --> src-manifest-COMP-33
    src-manifest-COMP-17 --> src-manifest-COMP-23
    src-manifest-COMP-29["Recursive"]
    src-manifest-COMP-29 --> src-manifest-COMP-21
    src-manifest-COMP-19 --> src-manifest-COMP-32
    src-manifest-COMP-27["Multi Scanner"]
    src-manifest-COMP-27 --> src-manifest-COMP-17
    src-manifest-COMP-24 --> src-manifest-COMP-27
    src-manifest-COMP-26["Metrics"]
    src-manifest-COMP-27 --> src-manifest-COMP-26
    src-manifest-COMP-29 --> src-manifest-COMP-25
    src-manifest-COMP-30 --> src-manifest-COMP-32
    src-manifest-COMP-19 --> src-manifest-COMP-33
    src-manifest-COMP-25 --> src-manifest-COMP-29
    src-manifest-COMP-30 --> src-manifest-COMP-33
    src-manifest-COMP-30 --> src-manifest-COMP-19
    src-manifest-COMP-26 --> src-manifest-COMP-22
    src-manifest-COMP-20["Chains"]
    src-manifest-COMP-22 --> src-manifest-COMP-20
    src-manifest-COMP-23 --> src-manifest-COMP-20
    src-manifest-COMP-26 --> src-manifest-COMP-28
    src-manifest-COMP-27 --> src-manifest-COMP-16
    src-manifest-COMP-24 --> src-manifest-COMP-29
    src-manifest-COMP-29 --> src-manifest-COMP-18
    src-manifest-COMP-32 --> src-manifest-COMP-29
    src-manifest-COMP-29 --> src-manifest-COMP-23
    src-manifest-COMP-25 --> src-manifest-COMP-21
    src-manifest-COMP-29 --> src-manifest-COMP-20
    src-manifest-COMP-17 --> src-manifest-COMP-29
    src-manifest-COMP-27 --> src-manifest-COMP-32
    src-manifest-COMP-26 --> src-manifest-COMP-33
    src-manifest-COMP-27 --> src-manifest-COMP-33
    src-manifest-COMP-22 --> src-manifest-COMP-24
    src-manifest-COMP-23 --> src-manifest-COMP-24
    src-manifest-COMP-27 --> src-manifest-COMP-19
    src-manifest-COMP-32 --> src-manifest-COMP-21
    src-manifest-COMP-29 --> src-manifest-COMP-27
    src-manifest-COMP-19 --> src-manifest-COMP-25
    src-manifest-COMP-17 --> src-manifest-COMP-21
    src-manifest-COMP-25 --> src-manifest-COMP-18
    src-manifest-COMP-32 --> src-manifest-COMP-25
    src-manifest-COMP-26 --> src-manifest-COMP-29
    src-manifest-COMP-17 --> src-manifest-COMP-25
    src-manifest-COMP-25 --> src-manifest-COMP-22
    src-manifest-COMP-25 --> src-manifest-COMP-23
    src-manifest-COMP-22 --> src-manifest-COMP-30
    src-manifest-COMP-25 --> src-manifest-COMP-20
    src-manifest-COMP-19 --> src-manifest-COMP-18
    src-manifest-COMP-23 --> src-manifest-COMP-17
    src-manifest-COMP-30 --> src-manifest-COMP-18
    src-manifest-COMP-19 --> src-manifest-COMP-22
    src-manifest-COMP-24 --> src-manifest-COMP-20
    src-manifest-COMP-19 --> src-manifest-COMP-23
    src-manifest-COMP-26 --> src-manifest-COMP-21
    src-manifest-COMP-29 --> src-manifest-COMP-30
    src-manifest-COMP-25 --> src-manifest-COMP-27
    src-manifest-COMP-30 --> src-manifest-COMP-22
    src-manifest-COMP-30 --> src-manifest-COMP-28
    src-manifest-COMP-32 --> src-manifest-COMP-20
    src-manifest-COMP-26 --> src-manifest-COMP-25
    src-manifest-COMP-22 --> src-manifest-COMP-16
    src-manifest-COMP-23 --> src-manifest-COMP-16
    src-manifest-COMP-17 --> src-manifest-COMP-20
    src-manifest-COMP-32 --> src-manifest-COMP-27
    src-manifest-COMP-26 --> src-manifest-COMP-18
    src-manifest-COMP-23 --> src-manifest-COMP-32
    src-manifest-COMP-27 --> src-manifest-COMP-18
    src-manifest-COMP-17 --> src-manifest-COMP-27
    src-manifest-COMP-26 --> src-manifest-COMP-23
    src-manifest-COMP-27 --> src-manifest-COMP-22
    src-manifest-COMP-25 --> src-manifest-COMP-30
    src-manifest-COMP-26 --> src-manifest-COMP-20
    src-manifest-COMP-27 --> src-manifest-COMP-28
    src-manifest-COMP-19 --> src-manifest-COMP-29
    src-manifest-COMP-30 --> src-manifest-COMP-29
    src-manifest-COMP-24 --> src-manifest-COMP-30
    src-manifest-COMP-24 --> src-manifest-COMP-17
    src-manifest-COMP-26 --> src-manifest-COMP-27
    src-manifest-COMP-32 --> src-manifest-COMP-30
    src-manifest-COMP-17 --> src-manifest-COMP-30
    src-manifest-COMP-19 --> src-manifest-COMP-21
    src-manifest-COMP-30 --> src-manifest-COMP-21
    src-manifest-COMP-24 --> src-manifest-COMP-16
    src-manifest-COMP-29 --> src-manifest-COMP-24
    src-manifest-COMP-30 --> src-manifest-COMP-25
    src-manifest-COMP-27 --> src-manifest-COMP-29
    src-manifest-COMP-23 --> src-manifest-COMP-30
    src-manifest-COMP-26 --> src-manifest-COMP-30
    src-manifest-COMP-24 --> src-manifest-COMP-32
    src-manifest-COMP-22 --> src-manifest-COMP-17
    src-manifest-COMP-22 --> src-manifest-COMP-26
    src-manifest-COMP-23 --> src-manifest-COMP-26
    src-manifest-COMP-19 --> src-manifest-COMP-20
    src-manifest-COMP-27 --> src-manifest-COMP-21
    src-manifest-COMP-29 --> src-manifest-COMP-17
    src-manifest-COMP-29 --> src-manifest-COMP-26
    src-manifest-COMP-30 --> src-manifest-COMP-23
    src-manifest-COMP-30 --> src-manifest-COMP-20
    src-manifest-COMP-27 --> src-manifest-COMP-25
    src-manifest-COMP-22 --> src-manifest-COMP-28
    src-manifest-COMP-23 --> src-manifest-COMP-28
    src-manifest-COMP-25 --> src-manifest-COMP-24
    src-manifest-COMP-19 --> src-manifest-COMP-27
    src-manifest-COMP-29 --> src-manifest-COMP-16
    src-manifest-COMP-30 --> src-manifest-COMP-27
    src-manifest-COMP-22 --> src-manifest-COMP-32
    src-manifest-COMP-32 --> src-manifest-COMP-24
    src-manifest-COMP-22 --> src-manifest-COMP-33
    src-manifest-COMP-23 --> src-manifest-COMP-33
    src-manifest-COMP-27 --> src-manifest-COMP-23
    src-manifest-COMP-17 --> src-manifest-COMP-24
    src-manifest-COMP-22 --> src-manifest-COMP-19
    src-manifest-COMP-23 --> src-manifest-COMP-19
    src-manifest-COMP-25 --> src-manifest-COMP-17
    src-manifest-COMP-27 --> src-manifest-COMP-20
    src-manifest-COMP-29 --> src-manifest-COMP-32
    src-manifest-COMP-19 --> src-manifest-COMP-30
    src-manifest-COMP-29 --> src-manifest-COMP-19
    src-manifest-COMP-23 --> src-manifest-COMP-29
    src-manifest-COMP-24 --> src-manifest-COMP-26
    src-manifest-COMP-25 --> src-manifest-COMP-16
    src-manifest-COMP-32 --> src-manifest-COMP-17
    src-manifest-COMP-32 --> src-manifest-COMP-26
    src-manifest-COMP-26 --> src-manifest-COMP-24
    src-manifest-COMP-17 --> src-manifest-COMP-26
    src-manifest-COMP-19 --> src-manifest-COMP-16
    src-manifest-COMP-24 --> src-manifest-COMP-28
    src-manifest-COMP-23 --> src-manifest-COMP-21
    src-manifest-COMP-25 --> src-manifest-COMP-32
    src-manifest-COMP-32 --> src-manifest-COMP-16
    src-manifest-COMP-32 --> src-manifest-COMP-28
    src-manifest-COMP-17 --> src-manifest-COMP-16
    src-manifest-COMP-22 --> src-manifest-COMP-25
    src-manifest-COMP-23 --> src-manifest-COMP-25
    src-manifest-COMP-17 --> src-manifest-COMP-28
    src-manifest-COMP-25 --> src-manifest-COMP-19
    src-manifest-COMP-27 --> src-manifest-COMP-30
    src-manifest-COMP-26 --> src-manifest-COMP-17
    src-manifest-COMP-24 --> src-manifest-COMP-33
    src-manifest-COMP-17 --> src-manifest-COMP-32
    src-manifest-COMP-22 --> src-manifest-COMP-18
    src-manifest-COMP-23 --> src-manifest-COMP-18
    src-manifest-COMP-24 --> src-manifest-COMP-19
    src-manifest-COMP-32 --> src-manifest-COMP-33
    src-manifest-COMP-32 --> src-manifest-COMP-19
    src-manifest-COMP-17 --> src-manifest-COMP-33
    src-manifest-COMP-23 --> src-manifest-COMP-22
    src-manifest-COMP-22 --> src-manifest-COMP-23
    src-manifest-COMP-26 --> src-manifest-COMP-16
    src-manifest-COMP-17 --> src-manifest-COMP-19
    src-manifest-COMP-29 --> src-manifest-COMP-22
    src-manifest-COMP-29 --> src-manifest-COMP-28
    src-manifest-COMP-26 --> src-manifest-COMP-32
    src-manifest-COMP-19 --> src-manifest-COMP-24
    src-manifest-COMP-22 --> src-manifest-COMP-27
    src-manifest-COMP-23 --> src-manifest-COMP-27
    src-manifest-COMP-30 --> src-manifest-COMP-17
    src-manifest-COMP-30 --> src-manifest-COMP-24
    src-manifest-COMP-24 --> src-manifest-COMP-21
    src-manifest-COMP-26 --> src-manifest-COMP-19
    src-manifest-COMP-25 --> src-manifest-COMP-26
    src-manifest-COMP-24 --> src-manifest-COMP-25
    src-manifest-COMP-29 --> src-manifest-COMP-33
    src-manifest-COMP-22 --> src-manifest-COMP-29
    src-manifest-COMP-18 --> src-manifest-COMP-17
    src-manifest-COMP-19 --> src-manifest-COMP-17
    src-manifest-COMP-19 --> src-manifest-COMP-26
    src-manifest-COMP-25 --> src-manifest-COMP-28
    src-manifest-COMP-30 --> src-manifest-COMP-26
    src-manifest-COMP-24 --> src-manifest-COMP-18
    src-manifest-COMP-27 --> src-manifest-COMP-24
    src-orchestration-COMP-9["Enrichment Context"]
    src-orchestration-COMP-4["Capability Inference"]
    src-orchestration-COMP-9 --> src-orchestration-COMP-4
    src-orchestration-COMP-12["Trigger Detection"]
    src-orchestration-COMP-9 --> src-orchestration-COMP-12
    src-orchestration-COMP-10["Naming Context"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-9
    src-orchestration-COMP-3["Behavior Flows"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-3
    src-orchestration-COMP-11["Pipeline"]
    src-orchestration-COMP-11 --> src-orchestration-COMP-9
    src-orchestration-COMP-8["Enrich"]
    src-orchestration-COMP-11 --> src-orchestration-COMP-8
    src-orchestration-COMP-11 --> src-orchestration-COMP-3
    src-orchestration-COMP-10 --> src-orchestration-COMP-8
    src-orchestration-COMP-7["Deep Decompose"]
    src-orchestration-COMP-9 --> src-orchestration-COMP-7
    src-orchestration-COMP-2["Behavior Decompose"]
    src-orchestration-COMP-9 --> src-orchestration-COMP-2
    src-orchestration-COMP-9 --> src-orchestration-COMP-8
    src-orchestration-COMP-9 --> src-orchestration-COMP-3
    src-orchestration-COMP-5["Compaction"]
    src-orchestration-COMP-11 --> src-orchestration-COMP-5
    src-orchestration-COMP-10 --> src-orchestration-COMP-5
    src-orchestration-COMP-1["Auto Enrich"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-1
    src-orchestration-COMP-6["Decompose"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-6
    src-orchestration-COMP-11 --> src-orchestration-COMP-1
    src-orchestration-COMP-11 --> src-orchestration-COMP-6
    src-orchestration-COMP-13["Use Case Inference"]
    src-orchestration-COMP-10 --> src-orchestration-COMP-13
    src-orchestration-COMP-11 --> src-orchestration-COMP-10
    src-orchestration-COMP-9 --> src-orchestration-COMP-5
    src-orchestration-COMP-11 --> src-orchestration-COMP-13
    src-orchestration-COMP-10 --> src-orchestration-COMP-11
    src-orchestration-COMP-10 --> src-orchestration-COMP-4
    src-orchestration-COMP-9 --> src-orchestration-COMP-1
    src-orchestration-COMP-10 --> src-orchestration-COMP-12
    src-orchestration-COMP-9 --> src-orchestration-COMP-6
    src-orchestration-COMP-11 --> src-orchestration-COMP-4
    src-orchestration-COMP-11 --> src-orchestration-COMP-2
    src-orchestration-COMP-11 --> src-orchestration-COMP-12
    src-orchestration-COMP-11 --> src-orchestration-COMP-7
    src-orchestration-COMP-10 --> src-orchestration-COMP-7
    src-orchestration-COMP-9 --> src-orchestration-COMP-11
    src-orchestration-COMP-9 --> src-orchestration-COMP-13
    src-orchestration-COMP-10 --> src-orchestration-COMP-2
    src-orchestration-COMP-9 --> src-orchestration-COMP-10
```
