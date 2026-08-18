---
document: Maintenance Manual
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

# Maintenance Manual: System

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Checkout (scripts-dev-simulation-COMP-1) | service | — | 1 | 0 | 0 |
| Cohesion (scripts-dev-simulation-COMP-2) | service | — | 1 | 0 | 0 |
| Drift Tracker (scripts-dev-simulation-COMP-3) | service | — | 1 | 0 | 0 |
| Extractor (scripts-dev-simulation-COMP-4) | service | — | 1 | 0 | 0 |
| Llm Predictor (scripts-dev-simulation-COMP-5) | service | — | 1 | 0 | 0 |
| Regen Scorer (scripts-dev-simulation-COMP-6) | service | — | 1 | 0 | 0 |
| Report (scripts-dev-simulation-COMP-7) | service | — | 1 | 0 | 0 |
| Runner (scripts-dev-simulation-COMP-8) | service | — | 1 | 0 | 0 |
| Slice Evaluator (scripts-dev-simulation-COMP-9) | service | — | 1 | 0 | 0 |
| Infrastructure (scripts-dev-simulation-COMP-10) | service | — | 1 | 0 | 0 |
| Allocate (src-pipeline-COMP-16) | service | — | 2 | 0 | 0 |
| Artifacts (src-pipeline-COMP-18) | service | — | 1 | 0 | 0 |
| Cache (src-pipeline-COMP-19) | service | — | 1 | 0 | 0 |
| Context Gen (src-pipeline-COMP-20) | service | — | 1 | 0 | 0 |
| Contract (src-pipeline-COMP-21) | service | — | 2 | 0 | 0 |
| Coordinator (src-pipeline-COMP-23) | service | — | 1 | 0 | 0 |
| Corrections (src-pipeline-COMP-24) | service | — | 1 | 0 | 0 |
| Decompose (src-pipeline-COMP-25) | service | — | 3 | 0 | 0 |
| Emit (src-pipeline-COMP-27) | service | — | 2 | 0 | 0 |
| Global Learning (src-pipeline-COMP-29) | service | — | 2 | 0 | 0 |
| Infer (src-pipeline-COMP-30) | service | — | 2 | 0 | 0 |
| Lessons (src-pipeline-COMP-33) | service | — | 1 | 0 | 0 |
| Observe (src-pipeline-COMP-34) | service | — | 2 | 0 | 0 |
| Protocol (src-pipeline-COMP-36) | service | — | 1 | 0 | 0 |
| Regen Score (src-pipeline-COMP-37) | service | — | 1 | 0 | 0 |
| Relate (src-pipeline-COMP-38) | service | — | 2 | 0 | 0 |
| Report (src-pipeline-COMP-40) | service | — | 1 | 0 | 0 |
| Requirements Derive (src-pipeline-COMP-41) | service | — | 1 | 0 | 0 |
| Specify (src-pipeline-COMP-42) | service | — | 2 | 0 | 0 |
| Synthesize (src-pipeline-COMP-44) | service | — | 2 | 0 | 0 |
| Validate (src-pipeline-COMP-46) | service | — | 2 | 0 | 0 |
| Cluster (src-core-COMP-15) | service | — | 1 | 0 | 0 |
| Completeness (src-core-COMP-16) | service | — | 1 | 0 | 0 |
| Compression (src-core-COMP-17) | service | — | 1 | 0 | 0 |
| Confidence (src-core-COMP-18) | service | — | 1 | 0 | 0 |
| Corrections (src-core-COMP-19) | service | — | 1 | 0 | 0 |
| Coverage (src-core-COMP-20) | service | — | 1 | 0 | 0 |
| Decomposer (src-core-COMP-21) | service | — | 1 | 0 | 0 |
| Differ (src-core-COMP-22) | service | — | 1 | 0 | 0 |
| Merger (src-core-COMP-23) | service | — | 1 | 0 | 0 |
| Parser (src-core-COMP-24) | service | — | 1 | 0 | 0 |
| Regen Readiness (src-core-COMP-25) | service | — | 1 | 0 | 0 |
| Representativeness (src-core-COMP-26) | service | — | 1 | 0 | 0 |
| Slicer (src-core-COMP-27) | service | — | 1 | 0 | 0 |
| Source Block Assign (src-core-COMP-28) | service | — | 3 | 0 | 0 |
| Validator (src-core-COMP-30) | service | — | 1 | 0 | 0 |
| Visualize (src-core-COMP-31) | service | — | 1 | 0 | 0 |
| Behavior (src-manifest-COMP-16) | service | — | 1 | 0 | 0 |
| Blocks (src-manifest-COMP-17) | service | — | 3 | 0 | 0 |
| Body Hints (src-manifest-COMP-18) | service | — | 1 | 0 | 0 |
| Call Graph (src-manifest-COMP-19) | service | — | 1 | 0 | 0 |
| Chains (src-manifest-COMP-20) | service | — | 1 | 0 | 0 |
| Display (src-manifest-COMP-21) | service | — | 1 | 0 | 0 |
| Generator (src-manifest-COMP-22) | service | — | 1 | 0 | 0 |
| Grouping (src-manifest-COMP-23) | service | — | 1 | 0 | 0 |
| Interfaces (src-manifest-COMP-24) | service | — | 1 | 0 | 0 |
| Kt Scanner (src-manifest-COMP-25) | service | — | 2 | 0 | 0 |
| Metrics (src-manifest-COMP-26) | service | — | 1 | 0 | 0 |
| Multi Scanner (src-manifest-COMP-27) | service | — | 1 | 0 | 0 |
| Protocol (src-manifest-COMP-28) | service | — | 1 | 0 | 0 |
| Recursive (src-manifest-COMP-29) | service | — | 1 | 0 | 0 |
| Scan Cache (src-manifest-COMP-30) | service | — | 1 | 0 | 0 |
| Slicers (src-manifest-COMP-32) | service | — | 1 | 0 | 0 |
| Ts Scanner (src-manifest-COMP-33) | service | — | 1 | 0 | 0 |
| Auto Enrich (src-orchestration-COMP-1) | service | — | 1 | 0 | 0 |
| Behavior Decompose (src-orchestration-COMP-2) | service | — | 1 | 0 | 0 |
| Behavior Flows (src-orchestration-COMP-3) | service | — | 1 | 0 | 0 |
| Capability Inference (src-orchestration-COMP-4) | service | — | 1 | 0 | 0 |
| Compaction (src-orchestration-COMP-5) | service | — | 1 | 0 | 0 |
| Decompose (src-orchestration-COMP-6) | service | — | 1 | 0 | 0 |
| Deep Decompose (src-orchestration-COMP-7) | service | — | 1 | 0 | 0 |
| Enrich (src-orchestration-COMP-8) | service | — | 1 | 0 | 0 |
| Enrichment Context (src-orchestration-COMP-9) | service | — | 1 | 0 | 0 |
| Naming Context (src-orchestration-COMP-10) | service | — | 1 | 0 | 0 |
| Pipeline (src-orchestration-COMP-11) | service | — | 1 | 0 | 0 |
| Trigger Detection (src-orchestration-COMP-12) | service | — | 1 | 0 | 0 |
| Use Case Inference (src-orchestration-COMP-13) | service | — | 1 | 0 | 0 |
| Scripts (core) (COMP-3-1) | service | data | 6 | 0 | 0 |
| Scripts (dev_simulation) (COMP-3-2) | service | data | 10 | 0 | 0 |
| Architecture Model Monitoring (COMP-4-1) | service | web | 5 | 0 | 0 |
| Src (pipeline) (COMP-4-2) | service | web | 33 | 0 | 0 |
| Core Analysis Engine (COMP-4-3) | service | web | 18 | 0 | 0 |
| Src (config) (COMP-4-4) | service | web | 3 | 0 | 0 |
| Src (manifest) (COMP-4-5) | service | web | 20 | 0 | 0 |
| Src (utils) (COMP-4-6) | service | web | 1 | 0 | 0 |
| CLI Interface Layer (COMP-4-7) | service | web | 2 | 0 | 0 |
| Src (authoring) (COMP-4-8) | service | web | 2 | 0 | 0 |
| Src (persistence) (COMP-4-9) | service | web | 2 | 0 | 0 |
| Src (orchestration) (COMP-4-10) | service | web | 13 | 0 | 0 |
| Src (extract) (COMP-4-11) | service | web | 5 | 0 | 0 |
| Src (profiles) (COMP-4-12) | service | web | 1 | 0 | 0 |
| Src (export) (COMP-4-13) | service | web | 2 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Checkout | — | — | LOW |
| Cohesion | — | — | LOW |
| Drift Tracker | — | — | LOW |
| Extractor | — | — | LOW |
| Llm Predictor | — | — | LOW |
| Regen Scorer | — | — | LOW |
| Report | — | — | LOW |
| Runner | — | Infrastructure | LOW |
| Slice Evaluator | — | — | LOW |
| Infrastructure | Runner | — | LOW |
| Allocate | Infer, Protocol, Corrections, Observe | Relate, Contract, Context Gen, Emit, Coordinator, Synthesize, Specify, Validate, Decompose, Artifacts, Cache | HIGH |
| Artifacts | Validate, Specify, Contract, Relate, Infer, Allocate, Observe, Protocol | Decompose, Cache, Emit, Synthesize, Coordinator | HIGH |
| Cache | Lessons, Report, Specify, Validate, Decompose, Requirements Derive, Artifacts, Coordinator, Global Learning, Contract, Context Gen, Emit, Synthesize, Protocol, Relate, Infer, Allocate, Observe, Corrections, Regen Score | Emit, Synthesize, Coordinator, Decompose | MEDIUM |
| Context Gen | Infer, Allocate, Observe, Protocol, Validate, Relate | Coordinator, Decompose, Cache, Emit, Synthesize | HIGH |
| Contract | Allocate, Observe, Protocol | Decompose, Artifacts, Cache, Emit, Coordinator, Synthesize | HIGH |
| Coordinator | Context Gen, Synthesize, Protocol, Relate, Corrections, Allocate, Observe, Validate, Regen Score, Lessons, Cache, Report, Specify, Global Learning, Contract, Decompose, Requirements Derive, Artifacts, Emit, Infer | Decompose, Cache, Emit, Synthesize | MEDIUM |
| Corrections | — | Coordinator, Emit, Synthesize, Allocate, Decompose, Cache, Infer | HIGH |
| Decompose | Lessons, Report, Specify, Global Learning, Contract, Requirements Derive, Artifacts, Coordinator, Context Gen, Emit, Relate, Infer, Synthesize, Protocol, Corrections, Allocate, Observe, Cache, Validate, Regen Score | Cache, Emit, Coordinator, Synthesize | MEDIUM |
| Emit | Allocate, Observe, Lessons, Cache, Corrections, Report, Validate, Regen Score, Artifacts, Specify, Global Learning, Contract, Decompose, Requirements Derive, Coordinator, Context Gen, Synthesize, Relate, Infer, Protocol | Decompose, Cache, Coordinator, Synthesize | MEDIUM |
| Global Learning | Protocol | Decompose, Cache, Emit, Coordinator, Synthesize | HIGH |
| Infer | Observe, Protocol, Corrections | Context Gen, Synthesize, Allocate, Validate, Decompose, Artifacts, Cache, Relate, Emit, Coordinator | HIGH |
| Lessons | Protocol | Decompose, Cache, Emit, Coordinator, Synthesize | HIGH |
| Observe | Protocol | Infer, Relate, Contract, Context Gen, Emit, Coordinator, Synthesize, Specify, Allocate, Decompose, Artifacts, Cache | HIGH |
| Protocol | — | Lessons, Regen Score, Coordinator, Context Gen, Synthesize, Specify, Allocate, Observe, Global Learning, Report, Validate, Decompose, Cache, Artifacts, Infer, Relate, Contract, Emit | HIGH |
| Regen Score | Protocol | Emit, Coordinator, Synthesize, Decompose, Cache | HIGH |
| Relate | Allocate, Observe, Infer, Protocol | Coordinator, Validate, Decompose, Artifacts, Cache, Emit, Context Gen, Synthesize | HIGH |
| Report | Protocol | Decompose, Cache, Emit, Synthesize, Coordinator | HIGH |
| Requirements Derive | — | Decompose, Cache, Emit, Coordinator, Synthesize | HIGH |
| Specify | Protocol, Allocate, Observe | Decompose, Cache, Artifacts, Emit, Coordinator, Synthesize | HIGH |
| Synthesize | Infer, Protocol, Corrections, Allocate, Observe, Cache, Report, Validate, Regen Score, Artifacts, Lessons, Specify, Global Learning, Contract, Decompose, Requirements Derive, Coordinator, Context Gen, Emit, Relate | Coordinator, Decompose, Cache, Emit | MEDIUM |
| Validate | Relate, Infer, Allocate, Protocol | Artifacts, Cache, Emit, Coordinator, Context Gen, Synthesize, Decompose | HIGH |
| Cluster | — | Source Block Assign, Representativeness, Regen Readiness, Confidence, Decomposer | HIGH |
| Completeness | — | Decomposer, Source Block Assign, Regen Readiness, Confidence, Representativeness | HIGH |
| Compression | — | Decomposer, Source Block Assign, Regen Readiness, Representativeness, Confidence | HIGH |
| Confidence | Source Block Assign, Corrections, Regen Readiness, Differ, Merger, Decomposer, Coverage, Slicer, Validator, Cluster, Completeness, Parser, Visualize, Compression, Representativeness | Regen Readiness, Representativeness, Decomposer, Source Block Assign | MEDIUM |
| Corrections | — | Confidence, Decomposer, Source Block Assign, Regen Readiness, Representativeness | HIGH |
| Coverage | Source Block Assign | Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign | HIGH |
| Decomposer | Compression, Representativeness, Completeness, Corrections, Differ, Source Block Assign, Regen Readiness, Confidence, Merger, Coverage, Slicer, Validator, Cluster, Parser, Visualize | Regen Readiness, Representativeness, Confidence, Source Block Assign | MEDIUM |
| Differ | Source Block Assign | Representativeness, Regen Readiness, Confidence, Decomposer, Source Block Assign | HIGH |
| Merger | Source Block Assign | Regen Readiness, Confidence, Representativeness, Decomposer, Source Block Assign | HIGH |
| Parser | Source Block Assign | Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign | HIGH |
| Regen Readiness | Decomposer, Confidence, Differ, Merger, Coverage, Slicer, Validator, Parser, Compression, Cluster, Completeness, Corrections, Visualize, Representativeness, Source Block Assign | Confidence, Representativeness, Decomposer, Source Block Assign | MEDIUM |
| Representativeness | Differ, Source Block Assign, Decomposer, Regen Readiness, Confidence, Merger, Coverage, Slicer, Validator, Cluster, Parser, Visualize, Compression, Completeness, Corrections | Decomposer, Source Block Assign, Regen Readiness, Confidence | MEDIUM |
| Slicer | Source Block Assign | Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign | HIGH |
| Source Block Assign | Compression, Cluster, Completeness, Visualize, Representativeness, Corrections, Decomposer, Regen Readiness, Confidence, Differ, Merger, Slicer, Validator, Coverage, Parser | Confidence, Representativeness, Validator, Decomposer, Coverage, Slicer, Differ, Merger, Parser, Regen Readiness | HIGH |
| Validator | Source Block Assign | Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign | HIGH |
| Visualize | — | Source Block Assign, Representativeness, Regen Readiness, Confidence, Decomposer | HIGH |
| Behavior | — | Scan Cache, Multi Scanner, Generator, Grouping, Interfaces, Recursive, Kt Scanner, Call Graph, Slicers, Blocks, Metrics | HIGH |
| Blocks | Body Hints, Generator, Grouping, Recursive, Display, Kt Scanner, Chains, Multi Scanner, Scan Cache, Interfaces, Metrics, Behavior, Protocol, Slicers, Ts Scanner, Call Graph | Multi Scanner, Grouping, Interfaces, Generator, Recursive, Kt Scanner, Slicers, Metrics, Scan Cache, Body Hints, Call Graph | HIGH |
| Body Hints | Blocks | Slicers, Blocks, Recursive, Kt Scanner, Call Graph, Scan Cache, Metrics, Multi Scanner, Generator, Grouping, Interfaces | HIGH |
| Call Graph | Protocol, Slicers, Ts Scanner, Kt Scanner, Body Hints, Generator, Grouping, Recursive, Display, Chains, Multi Scanner, Scan Cache, Behavior, Interfaces, Blocks, Metrics | Scan Cache, Multi Scanner, Generator, Grouping, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Metrics | HIGH |
| Chains | — | Generator, Grouping, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner | HIGH |
| Display | — | Generator, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner, Grouping, Interfaces | HIGH |
| Generator | Display, Chains, Interfaces, Scan Cache, Behavior, Blocks, Metrics, Protocol, Slicers, Ts Scanner, Call Graph, Kt Scanner, Body Hints, Grouping, Multi Scanner, Recursive | Interfaces, Slicers, Blocks, Metrics, Kt Scanner, Call Graph, Scan Cache, Multi Scanner, Grouping, Recursive | HIGH |
| Grouping | Chains, Interfaces, Blocks, Behavior, Slicers, Scan Cache, Metrics, Protocol, Ts Scanner, Call Graph, Recursive, Display, Kt Scanner, Body Hints, Generator, Multi Scanner | Interfaces, Slicers, Blocks, Recursive, Kt Scanner, Call Graph, Metrics, Scan Cache, Multi Scanner, Generator | HIGH |
| Interfaces | Generator, Grouping, Multi Scanner, Recursive, Chains, Scan Cache, Blocks, Behavior, Slicers, Metrics, Protocol, Ts Scanner, Call Graph, Display, Kt Scanner, Body Hints | Generator, Grouping, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner | HIGH |
| Kt Scanner | Ts Scanner, Recursive, Display, Body Hints, Generator, Grouping, Chains, Multi Scanner, Scan Cache, Interfaces, Blocks, Behavior, Slicers, Call Graph, Metrics, Protocol | Recursive, Call Graph, Slicers, Blocks, Metrics, Scan Cache, Multi Scanner, Generator, Grouping, Interfaces | HIGH |
| Metrics | Generator, Protocol, Ts Scanner, Recursive, Display, Kt Scanner, Body Hints, Grouping, Chains, Multi Scanner, Scan Cache, Interfaces, Blocks, Behavior, Slicers, Call Graph | Multi Scanner, Generator, Grouping, Recursive, Interfaces, Slicers, Blocks, Kt Scanner, Call Graph, Scan Cache | HIGH |
| Multi Scanner | Blocks, Metrics, Behavior, Slicers, Ts Scanner, Call Graph, Body Hints, Generator, Protocol, Recursive, Display, Kt Scanner, Grouping, Chains, Scan Cache, Interfaces | Interfaces, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Generator, Grouping | HIGH |
| Protocol | — | Call Graph, Metrics, Scan Cache, Multi Scanner, Generator, Grouping, Interfaces, Slicers, Blocks, Recursive, Kt Scanner | HIGH |
| Recursive | Display, Kt Scanner, Body Hints, Grouping, Chains, Multi Scanner, Scan Cache, Interfaces, Blocks, Metrics, Behavior, Slicers, Call Graph, Generator, Protocol, Ts Scanner | Kt Scanner, Interfaces, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner, Grouping, Generator | HIGH |
| Scan Cache | Behavior, Slicers, Ts Scanner, Call Graph, Body Hints, Generator, Protocol, Recursive, Display, Kt Scanner, Grouping, Chains, Multi Scanner, Blocks, Interfaces, Metrics | Generator, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Grouping, Metrics, Call Graph, Multi Scanner | HIGH |
| Slicers | Body Hints, Generator, Grouping, Recursive, Display, Kt Scanner, Chains, Multi Scanner, Scan Cache, Interfaces, Blocks, Metrics, Behavior, Protocol, Ts Scanner, Call Graph | Call Graph, Scan Cache, Multi Scanner, Grouping, Interfaces, Generator, Recursive, Kt Scanner, Blocks, Metrics | HIGH |
| Ts Scanner | — | Kt Scanner, Call Graph, Scan Cache, Metrics, Multi Scanner, Generator, Grouping, Interfaces, Slicers, Blocks, Recursive | HIGH |
| Auto Enrich | — | Naming Context, Pipeline, Enrichment Context | MEDIUM |
| Behavior Decompose | — | Enrichment Context, Pipeline, Naming Context | MEDIUM |
| Behavior Flows | — | Naming Context, Pipeline, Enrichment Context | MEDIUM |
| Capability Inference | — | Enrichment Context, Naming Context, Pipeline | MEDIUM |
| Compaction | — | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Decompose | — | Naming Context, Pipeline, Enrichment Context | MEDIUM |
| Deep Decompose | — | Enrichment Context, Pipeline, Naming Context | MEDIUM |
| Enrich | — | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Enrichment Context | Capability Inference, Trigger Detection, Deep Decompose, Behavior Decompose, Enrich, Behavior Flows, Compaction, Auto Enrich, Decompose, Pipeline, Use Case Inference, Naming Context | Naming Context, Pipeline | MEDIUM |
| Naming Context | Enrichment Context, Behavior Flows, Enrich, Compaction, Auto Enrich, Decompose, Use Case Inference, Pipeline, Capability Inference, Trigger Detection, Deep Decompose, Behavior Decompose | Pipeline, Enrichment Context | MEDIUM |
| Pipeline | Enrichment Context, Enrich, Behavior Flows, Compaction, Auto Enrich, Decompose, Naming Context, Use Case Inference, Capability Inference, Behavior Decompose, Trigger Detection, Deep Decompose | Naming Context, Enrichment Context | MEDIUM |
| Trigger Detection | — | Enrichment Context, Naming Context, Pipeline | MEDIUM |
| Use Case Inference | — | Naming Context, Pipeline, Enrichment Context | MEDIUM |
| Scripts (core) | — | — | LOW |
| Scripts (dev_simulation) | — | — | LOW |
| Architecture Model Monitoring | — | — | LOW |
| Src (pipeline) | — | — | LOW |
| Core Analysis Engine | — | — | LOW |
| Src (config) | — | — | LOW |
| Src (manifest) | — | — | LOW |
| Src (utils) | — | — | LOW |
| CLI Interface Layer | — | — | LOW |
| Src (authoring) | — | — | LOW |
| Src (persistence) | — | — | LOW |
| Src (orchestration) | — | — | LOW |
| Src (extract) | — | — | LOW |
| Src (profiles) | — | — | LOW |
| Src (export) | — | — | LOW |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Checkout (scripts-dev-simulation-COMP-1)

**Files:**
- `scripts/dev_simulation/checkout.py`

### Cohesion (scripts-dev-simulation-COMP-2)

**Files:**
- `scripts/dev_simulation/cohesion.py`

### Drift Tracker (scripts-dev-simulation-COMP-3)

**Files:**
- `scripts/dev_simulation/drift_tracker.py`

### Extractor (scripts-dev-simulation-COMP-4)

**Files:**
- `scripts/dev_simulation/extractor.py`

### Llm Predictor (scripts-dev-simulation-COMP-5)

**Files:**
- `scripts/dev_simulation/llm_predictor.py`

### Regen Scorer (scripts-dev-simulation-COMP-6)

**Files:**
- `scripts/dev_simulation/regen_scorer.py`

### Report (scripts-dev-simulation-COMP-7)

**Files:**
- `scripts/dev_simulation/report.py`

### Runner (scripts-dev-simulation-COMP-8)

**Files:**
- `scripts/dev_simulation/runner.py`
**Downstream dependents (must re-test):** Infrastructure

### Slice Evaluator (scripts-dev-simulation-COMP-9)

**Files:**
- `scripts/dev_simulation/slice_evaluator.py`

### Infrastructure (scripts-dev-simulation-COMP-10)

**Files:**
- `scripts/dev_simulation/cli.py`

### Allocate (src-pipeline-COMP-16)

**Files:**
- `src/architecture_model/pipeline/allocate.py`
- `src/architecture_model/pipeline/allocate_types.py`
**Downstream dependents (must re-test):** Relate, Contract, Context Gen, Emit, Coordinator, Synthesize, Specify, Validate, Decompose, Artifacts, Cache

### Artifacts (src-pipeline-COMP-18)

**Files:**
- `src/architecture_model/pipeline/artifacts.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Synthesize, Coordinator

### Cache (src-pipeline-COMP-19)

**Files:**
- `src/architecture_model/pipeline/cache.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Coordinator, Decompose

### Context Gen (src-pipeline-COMP-20)

**Files:**
- `src/architecture_model/pipeline/context_gen.py`
**Downstream dependents (must re-test):** Coordinator, Decompose, Cache, Emit, Synthesize

### Contract (src-pipeline-COMP-21)

**Files:**
- `src/architecture_model/pipeline/contract.py`
- `src/architecture_model/pipeline/contract_types.py`
**Downstream dependents (must re-test):** Decompose, Artifacts, Cache, Emit, Coordinator, Synthesize

### Coordinator (src-pipeline-COMP-23)

**Files:**
- `src/architecture_model/pipeline/coordinator.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Synthesize

### Corrections (src-pipeline-COMP-24)

**Files:**
- `src/architecture_model/pipeline/corrections.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Synthesize, Allocate, Decompose, Cache, Infer

### Decompose (src-pipeline-COMP-25)

**Files:**
- `src/architecture_model/pipeline/__init__.py`
- `src/architecture_model/pipeline/decompose.py`
- `src/architecture_model/pipeline/decompose_types.py`
**Downstream dependents (must re-test):** Cache, Emit, Coordinator, Synthesize

### Emit (src-pipeline-COMP-27)

**Files:**
- `src/architecture_model/pipeline/emit.py`
- `src/architecture_model/pipeline/emit_types.py`
**Downstream dependents (must re-test):** Decompose, Cache, Coordinator, Synthesize

### Global Learning (src-pipeline-COMP-29)

**Files:**
- `src/architecture_model/pipeline/global_learning.py`
- `src/architecture_model/pipeline/learning.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Coordinator, Synthesize

### Infer (src-pipeline-COMP-30)

**Files:**
- `src/architecture_model/pipeline/infer.py`
- `src/architecture_model/pipeline/infer_types.py`
**Downstream dependents (must re-test):** Context Gen, Synthesize, Allocate, Validate, Decompose, Artifacts, Cache, Relate, Emit, Coordinator

### Lessons (src-pipeline-COMP-33)

**Files:**
- `src/architecture_model/pipeline/lessons.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Coordinator, Synthesize

### Observe (src-pipeline-COMP-34)

**Files:**
- `src/architecture_model/pipeline/observe.py`
- `src/architecture_model/pipeline/observe_types.py`
**Downstream dependents (must re-test):** Infer, Relate, Contract, Context Gen, Emit, Coordinator, Synthesize, Specify, Allocate, Decompose, Artifacts, Cache

### Protocol (src-pipeline-COMP-36)

**Files:**
- `src/architecture_model/pipeline/protocol.py`
**Downstream dependents (must re-test):** Lessons, Regen Score, Coordinator, Context Gen, Synthesize, Specify, Allocate, Observe, Global Learning, Report, Validate, Decompose, Cache, Artifacts, Infer, Relate, Contract, Emit

### Regen Score (src-pipeline-COMP-37)

**Files:**
- `src/architecture_model/pipeline/regen_score.py`
**Downstream dependents (must re-test):** Emit, Coordinator, Synthesize, Decompose, Cache

### Relate (src-pipeline-COMP-38)

**Files:**
- `src/architecture_model/pipeline/relate.py`
- `src/architecture_model/pipeline/relate_types.py`
**Downstream dependents (must re-test):** Coordinator, Validate, Decompose, Artifacts, Cache, Emit, Context Gen, Synthesize

### Report (src-pipeline-COMP-40)

**Files:**
- `src/architecture_model/pipeline/report.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Synthesize, Coordinator

### Requirements Derive (src-pipeline-COMP-41)

**Files:**
- `src/architecture_model/pipeline/requirements_derive.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Coordinator, Synthesize

### Specify (src-pipeline-COMP-42)

**Files:**
- `src/architecture_model/pipeline/specify.py`
- `src/architecture_model/pipeline/specify_types.py`
**Downstream dependents (must re-test):** Decompose, Cache, Artifacts, Emit, Coordinator, Synthesize

### Synthesize (src-pipeline-COMP-44)

**Files:**
- `src/architecture_model/pipeline/synthesize.py`
- `src/architecture_model/pipeline/synthesize_types.py`
**Downstream dependents (must re-test):** Coordinator, Decompose, Cache, Emit

### Validate (src-pipeline-COMP-46)

**Files:**
- `src/architecture_model/pipeline/validate.py`
- `src/architecture_model/pipeline/validate_types.py`
**Downstream dependents (must re-test):** Artifacts, Cache, Emit, Coordinator, Context Gen, Synthesize, Decompose

### Cluster (src-core-COMP-15)

**Files:**
- `src/architecture_model/core/cluster.py`
**Downstream dependents (must re-test):** Source Block Assign, Representativeness, Regen Readiness, Confidence, Decomposer

### Completeness (src-core-COMP-16)

**Files:**
- `src/architecture_model/core/completeness.py`
**Downstream dependents (must re-test):** Decomposer, Source Block Assign, Regen Readiness, Confidence, Representativeness

### Compression (src-core-COMP-17)

**Files:**
- `src/architecture_model/core/compression.py`
**Downstream dependents (must re-test):** Decomposer, Source Block Assign, Regen Readiness, Representativeness, Confidence

### Confidence (src-core-COMP-18)

**Files:**
- `src/architecture_model/core/confidence.py`
**Downstream dependents (must re-test):** Regen Readiness, Representativeness, Decomposer, Source Block Assign

### Corrections (src-core-COMP-19)

**Files:**
- `src/architecture_model/core/corrections.py`
**Downstream dependents (must re-test):** Confidence, Decomposer, Source Block Assign, Regen Readiness, Representativeness

### Coverage (src-core-COMP-20)

**Files:**
- `src/architecture_model/core/coverage.py`
**Downstream dependents (must re-test):** Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign

### Decomposer (src-core-COMP-21)

**Files:**
- `src/architecture_model/core/decomposer.py`
**Downstream dependents (must re-test):** Regen Readiness, Representativeness, Confidence, Source Block Assign

### Differ (src-core-COMP-22)

**Files:**
- `src/architecture_model/core/differ.py`
**Downstream dependents (must re-test):** Representativeness, Regen Readiness, Confidence, Decomposer, Source Block Assign

### Merger (src-core-COMP-23)

**Files:**
- `src/architecture_model/core/merger.py`
**Downstream dependents (must re-test):** Regen Readiness, Confidence, Representativeness, Decomposer, Source Block Assign

### Parser (src-core-COMP-24)

**Files:**
- `src/architecture_model/core/parser.py`
**Downstream dependents (must re-test):** Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign

### Regen Readiness (src-core-COMP-25)

**Files:**
- `src/architecture_model/core/regen_readiness.py`
**Downstream dependents (must re-test):** Confidence, Representativeness, Decomposer, Source Block Assign

### Representativeness (src-core-COMP-26)

**Files:**
- `src/architecture_model/core/representativeness.py`
**Downstream dependents (must re-test):** Decomposer, Source Block Assign, Regen Readiness, Confidence

### Slicer (src-core-COMP-27)

**Files:**
- `src/architecture_model/core/slicer.py`
**Downstream dependents (must re-test):** Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign

### Source Block Assign (src-core-COMP-28)

**Files:**
- `src/architecture_model/core/source_block_assign.py`
- `src/architecture_model/core/source_block_quality.py`
- `src/architecture_model/core/types.py`
**Downstream dependents (must re-test):** Confidence, Representativeness, Validator, Decomposer, Coverage, Slicer, Differ, Merger, Parser, Regen Readiness

### Validator (src-core-COMP-30)

**Files:**
- `src/architecture_model/core/validator.py`
**Downstream dependents (must re-test):** Regen Readiness, Representativeness, Confidence, Decomposer, Source Block Assign

### Visualize (src-core-COMP-31)

**Files:**
- `src/architecture_model/core/visualize.py`
**Downstream dependents (must re-test):** Source Block Assign, Representativeness, Regen Readiness, Confidence, Decomposer

### Behavior (src-manifest-COMP-16)

**Files:**
- `src/architecture_model/manifest/behavior.py`
**Downstream dependents (must re-test):** Scan Cache, Multi Scanner, Generator, Grouping, Interfaces, Recursive, Kt Scanner, Call Graph, Slicers, Blocks, Metrics

### Blocks (src-manifest-COMP-17)

**Files:**
- `src/architecture_model/manifest/__init__.py`
- `src/architecture_model/manifest/blocks.py`
- `src/architecture_model/manifest/types.py`
**Downstream dependents (must re-test):** Multi Scanner, Grouping, Interfaces, Generator, Recursive, Kt Scanner, Slicers, Metrics, Scan Cache, Body Hints, Call Graph

### Body Hints (src-manifest-COMP-18)

**Files:**
- `src/architecture_model/manifest/body_hints.py`
**Downstream dependents (must re-test):** Slicers, Blocks, Recursive, Kt Scanner, Call Graph, Scan Cache, Metrics, Multi Scanner, Generator, Grouping, Interfaces

### Call Graph (src-manifest-COMP-19)

**Files:**
- `src/architecture_model/manifest/call_graph.py`
**Downstream dependents (must re-test):** Scan Cache, Multi Scanner, Generator, Grouping, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Metrics

### Chains (src-manifest-COMP-20)

**Files:**
- `src/architecture_model/manifest/chains.py`
**Downstream dependents (must re-test):** Generator, Grouping, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner

### Display (src-manifest-COMP-21)

**Files:**
- `src/architecture_model/manifest/display.py`
**Downstream dependents (must re-test):** Generator, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner, Grouping, Interfaces

### Generator (src-manifest-COMP-22)

**Files:**
- `src/architecture_model/manifest/generator.py`
**Downstream dependents (must re-test):** Interfaces, Slicers, Blocks, Metrics, Kt Scanner, Call Graph, Scan Cache, Multi Scanner, Grouping, Recursive

### Grouping (src-manifest-COMP-23)

**Files:**
- `src/architecture_model/manifest/grouping.py`
**Downstream dependents (must re-test):** Interfaces, Slicers, Blocks, Recursive, Kt Scanner, Call Graph, Metrics, Scan Cache, Multi Scanner, Generator

### Interfaces (src-manifest-COMP-24)

**Files:**
- `src/architecture_model/manifest/interfaces.py`
**Downstream dependents (must re-test):** Generator, Grouping, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner

### Kt Scanner (src-manifest-COMP-25)

**Files:**
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/scanner.py`
**Downstream dependents (must re-test):** Recursive, Call Graph, Slicers, Blocks, Metrics, Scan Cache, Multi Scanner, Generator, Grouping, Interfaces

### Metrics (src-manifest-COMP-26)

**Files:**
- `src/architecture_model/manifest/metrics.py`
**Downstream dependents (must re-test):** Multi Scanner, Generator, Grouping, Recursive, Interfaces, Slicers, Blocks, Kt Scanner, Call Graph, Scan Cache

### Multi Scanner (src-manifest-COMP-27)

**Files:**
- `src/architecture_model/manifest/multi_scanner.py`
**Downstream dependents (must re-test):** Interfaces, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Generator, Grouping

### Protocol (src-manifest-COMP-28)

**Files:**
- `src/architecture_model/manifest/protocol.py`
**Downstream dependents (must re-test):** Call Graph, Metrics, Scan Cache, Multi Scanner, Generator, Grouping, Interfaces, Slicers, Blocks, Recursive, Kt Scanner

### Recursive (src-manifest-COMP-29)

**Files:**
- `src/architecture_model/manifest/recursive.py`
**Downstream dependents (must re-test):** Kt Scanner, Interfaces, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner, Grouping, Generator

### Scan Cache (src-manifest-COMP-30)

**Files:**
- `src/architecture_model/manifest/scan_cache.py`
**Downstream dependents (must re-test):** Generator, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Grouping, Metrics, Call Graph, Multi Scanner

### Slicers (src-manifest-COMP-32)

**Files:**
- `src/architecture_model/manifest/slicers.py`
**Downstream dependents (must re-test):** Call Graph, Scan Cache, Multi Scanner, Grouping, Interfaces, Generator, Recursive, Kt Scanner, Blocks, Metrics

### Ts Scanner (src-manifest-COMP-33)

**Files:**
- `src/architecture_model/manifest/ts_scanner.py`
**Downstream dependents (must re-test):** Kt Scanner, Call Graph, Scan Cache, Metrics, Multi Scanner, Generator, Grouping, Interfaces, Slicers, Blocks, Recursive

### Auto Enrich (src-orchestration-COMP-1)

**Files:**
- `src/architecture_model/orchestration/auto_enrich.py`
**Downstream dependents (must re-test):** Naming Context, Pipeline, Enrichment Context

### Behavior Decompose (src-orchestration-COMP-2)

**Files:**
- `src/architecture_model/orchestration/behavior_decompose.py`
**Downstream dependents (must re-test):** Enrichment Context, Pipeline, Naming Context

### Behavior Flows (src-orchestration-COMP-3)

**Files:**
- `src/architecture_model/orchestration/behavior_flows.py`
**Downstream dependents (must re-test):** Naming Context, Pipeline, Enrichment Context

### Capability Inference (src-orchestration-COMP-4)

**Files:**
- `src/architecture_model/orchestration/capability_inference.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context, Pipeline

### Compaction (src-orchestration-COMP-5)

**Files:**
- `src/architecture_model/orchestration/compaction.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Decompose (src-orchestration-COMP-6)

**Files:**
- `src/architecture_model/orchestration/decompose.py`
**Downstream dependents (must re-test):** Naming Context, Pipeline, Enrichment Context

### Deep Decompose (src-orchestration-COMP-7)

**Files:**
- `src/architecture_model/orchestration/deep_decompose.py`
**Downstream dependents (must re-test):** Enrichment Context, Pipeline, Naming Context

### Enrich (src-orchestration-COMP-8)

**Files:**
- `src/architecture_model/orchestration/enrich.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Enrichment Context (src-orchestration-COMP-9)

**Files:**
- `src/architecture_model/orchestration/enrichment_context.py`
**Downstream dependents (must re-test):** Naming Context, Pipeline

### Naming Context (src-orchestration-COMP-10)

**Files:**
- `src/architecture_model/orchestration/naming_context.py`
**Downstream dependents (must re-test):** Pipeline, Enrichment Context

### Pipeline (src-orchestration-COMP-11)

**Files:**
- `src/architecture_model/orchestration/pipeline.py`
**Downstream dependents (must re-test):** Naming Context, Enrichment Context

### Trigger Detection (src-orchestration-COMP-12)

**Files:**
- `src/architecture_model/orchestration/trigger_detection.py`
**Downstream dependents (must re-test):** Enrichment Context, Naming Context, Pipeline

### Use Case Inference (src-orchestration-COMP-13)

**Files:**
- `src/architecture_model/orchestration/use_case_inference.py`
**Downstream dependents (must re-test):** Naming Context, Pipeline, Enrichment Context

### Scripts (core) (COMP-3-1)

**Files:**
- `scripts/add_sub_behaviors.py`
- `scripts/bench_enrichment.py`
- `scripts/enrich_sub_behaviors.py`
- `scripts/generate_models_pdf.py`
- `scripts/se_enrich.py`
- `scripts/strip_sub_behaviors.py`

### Scripts (dev_simulation) (COMP-3-2)

**Files:**
- `scripts/dev_simulation/checkout.py`
- `scripts/dev_simulation/cli.py`
- `scripts/dev_simulation/cohesion.py`
- `scripts/dev_simulation/drift_tracker.py`
- `scripts/dev_simulation/extractor.py`
- `scripts/dev_simulation/llm_predictor.py`
- `scripts/dev_simulation/regen_scorer.py`
- `scripts/dev_simulation/report.py`
- `scripts/dev_simulation/runner.py`
- `scripts/dev_simulation/slice_evaluator.py`

### Architecture Model Monitoring (COMP-4-1)

**Files:**
- `src/architecture_model/__init__.py`
- `src/architecture_model/__main__.py`
- `src/architecture_model/monitoring.py`
- `src/architecture_model/monitoring_checks.py`
- `src/architecture_model/patterns.py`

### Src (pipeline) (COMP-4-2)

**Files:**
- `src/architecture_model/pipeline/__init__.py`
- `src/architecture_model/pipeline/allocate.py`
- `src/architecture_model/pipeline/allocate_types.py`
- `src/architecture_model/pipeline/artifacts.py`
- `src/architecture_model/pipeline/cache.py`
- `src/architecture_model/pipeline/context_gen.py`
- `src/architecture_model/pipeline/contract.py`
- `src/architecture_model/pipeline/contract_types.py`
- `src/architecture_model/pipeline/coordinator.py`
- `src/architecture_model/pipeline/corrections.py`
- `src/architecture_model/pipeline/decompose.py`
- `src/architecture_model/pipeline/decompose_types.py`
- `src/architecture_model/pipeline/emit.py`
- `src/architecture_model/pipeline/emit_types.py`
- `src/architecture_model/pipeline/global_learning.py`
- `src/architecture_model/pipeline/infer.py`
- `src/architecture_model/pipeline/infer_types.py`
- `src/architecture_model/pipeline/learning.py`
- `src/architecture_model/pipeline/lessons.py`
- `src/architecture_model/pipeline/observe.py`
- *...and 13 more files*

### Core Analysis Engine (COMP-4-3)

**Files:**
- `src/architecture_model/core/cluster.py`
- `src/architecture_model/core/completeness.py`
- `src/architecture_model/core/compression.py`
- `src/architecture_model/core/confidence.py`
- `src/architecture_model/core/corrections.py`
- `src/architecture_model/core/coverage.py`
- `src/architecture_model/core/decomposer.py`
- `src/architecture_model/core/differ.py`
- `src/architecture_model/core/merger.py`
- `src/architecture_model/core/parser.py`
- `src/architecture_model/core/regen_readiness.py`
- `src/architecture_model/core/representativeness.py`
- `src/architecture_model/core/slicer.py`
- `src/architecture_model/core/source_block_assign.py`
- `src/architecture_model/core/source_block_quality.py`
- `src/architecture_model/core/types.py`
- `src/architecture_model/core/validator.py`
- `src/architecture_model/core/visualize.py`

### Src (config) (COMP-4-4)

**Files:**
- `src/architecture_model/config/__init__.py`
- `src/architecture_model/config/loader.py`
- `src/architecture_model/config/schema.py`

### Src (manifest) (COMP-4-5)

**Files:**
- `src/architecture_model/manifest/__init__.py`
- `src/architecture_model/manifest/behavior.py`
- `src/architecture_model/manifest/blocks.py`
- `src/architecture_model/manifest/body_hints.py`
- `src/architecture_model/manifest/call_graph.py`
- `src/architecture_model/manifest/chains.py`
- `src/architecture_model/manifest/display.py`
- `src/architecture_model/manifest/generator.py`
- `src/architecture_model/manifest/grouping.py`
- `src/architecture_model/manifest/interfaces.py`
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/metrics.py`
- `src/architecture_model/manifest/multi_scanner.py`
- `src/architecture_model/manifest/protocol.py`
- `src/architecture_model/manifest/recursive.py`
- `src/architecture_model/manifest/scan_cache.py`
- `src/architecture_model/manifest/scanner.py`
- `src/architecture_model/manifest/slicers.py`
- `src/architecture_model/manifest/ts_scanner.py`
- `src/architecture_model/manifest/types.py`

### Src (utils) (COMP-4-6)

**Files:**
- `src/architecture_model/utils/discovery.py`

### CLI Interface Layer (COMP-4-7)

**Files:**
- `src/architecture_model/cli/main.py`
- `src/architecture_model/cli/visualize.py`

### Src (authoring) (COMP-4-8)

**Files:**
- `src/architecture_model/authoring/gate.py`
- `src/architecture_model/authoring/parser.py`

### Src (persistence) (COMP-4-9)

**Files:**
- `src/architecture_model/persistence/__init__.py`
- `src/architecture_model/persistence/store.py`

### Src (orchestration) (COMP-4-10)

**Files:**
- `src/architecture_model/orchestration/auto_enrich.py`
- `src/architecture_model/orchestration/behavior_decompose.py`
- `src/architecture_model/orchestration/behavior_flows.py`
- `src/architecture_model/orchestration/capability_inference.py`
- `src/architecture_model/orchestration/compaction.py`
- `src/architecture_model/orchestration/decompose.py`
- `src/architecture_model/orchestration/deep_decompose.py`
- `src/architecture_model/orchestration/enrich.py`
- `src/architecture_model/orchestration/enrichment_context.py`
- `src/architecture_model/orchestration/naming_context.py`
- `src/architecture_model/orchestration/pipeline.py`
- `src/architecture_model/orchestration/trigger_detection.py`
- `src/architecture_model/orchestration/use_case_inference.py`

### Src (extract) (COMP-4-11)

**Files:**
- `src/architecture_model/extract/constraint_detector.py`
- `src/architecture_model/extract/from_artifacts.py`
- `src/architecture_model/extract/from_code.py`
- `src/architecture_model/extract/route_detector.py`
- `src/architecture_model/extract/table_parser.py`

### Src (profiles) (COMP-4-12)

**Files:**
- `src/architecture_model/profiles/schema.py`

### Src (export) (COMP-4-13)

**Files:**
- `src/architecture_model/export/flatfiles.py`
- `src/architecture_model/export/reference.py`

## Known Constraints

*No constraint allocations defined.*
