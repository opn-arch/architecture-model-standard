---
document: Maintenance Manual
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
| Allocate | Infer, Protocol, Observe, Corrections | Relate, Cache, Synthesize, Contract, Artifacts, Context Gen, Specify, Validate, Decompose, Coordinator, Emit | HIGH |
| Artifacts | Validate, Infer, Contract, Allocate, Observe, Specify, Protocol, Relate | Coordinator, Cache, Emit, Synthesize, Decompose | HIGH |
| Cache | Infer, Regen Score, Protocol, Allocate, Synthesize, Artifacts, Observe, Relate, Context Gen, Specify, Coordinator, Global Learning, Report, Validate, Corrections, Decompose, Emit, Requirements Derive, Contract, Lessons | Coordinator, Emit, Synthesize, Decompose | MEDIUM |
| Context Gen | Infer, Protocol, Allocate, Observe, Relate, Validate | Emit, Synthesize, Cache, Decompose, Coordinator | HIGH |
| Contract | Protocol, Allocate, Observe | Decompose, Artifacts, Coordinator, Cache, Emit, Synthesize | HIGH |
| Coordinator | Synthesize, Artifacts, Cache, Observe, Relate, Global Learning, Report, Validate, Corrections, Decompose, Emit, Requirements Derive, Contract, Lessons, Infer, Regen Score, Context Gen, Specify, Protocol, Allocate | Decompose, Cache, Emit, Synthesize | MEDIUM |
| Corrections | — | Coordinator, Cache, Emit, Synthesize, Infer, Decompose, Allocate | HIGH |
| Decompose | Emit, Coordinator, Requirements Derive, Contract, Lessons, Infer, Regen Score, Protocol, Allocate, Synthesize, Artifacts, Observe, Relate, Context Gen, Specify, Global Learning, Report, Validate, Corrections, Cache | Coordinator, Emit, Cache, Synthesize | MEDIUM |
| Emit | Observe, Regen Score, Context Gen, Specify, Global Learning, Synthesize, Artifacts, Cache, Relate, Decompose, Coordinator, Report, Validate, Corrections, Infer, Requirements Derive, Contract, Protocol, Allocate, Lessons | Decompose, Coordinator, Cache, Synthesize | MEDIUM |
| Global Learning | Protocol | Coordinator, Emit, Cache, Synthesize, Decompose | HIGH |
| Infer | Protocol, Observe, Corrections | Cache, Synthesize, Allocate, Artifacts, Context Gen, Validate, Decompose, Coordinator, Emit, Relate | HIGH |
| Lessons | Protocol | Decompose, Coordinator, Cache, Emit, Synthesize | HIGH |
| Observe | Protocol | Coordinator, Emit, Relate, Cache, Synthesize, Infer, Allocate, Contract, Artifacts, Context Gen, Specify, Decompose | HIGH |
| Protocol | — | Cache, Synthesize, Infer, Allocate, Contract, Context Gen, Specify, Validate, Decompose, Artifacts, Regen Score, Observe, Lessons, Global Learning, Coordinator, Emit, Report, Relate | HIGH |
| Regen Score | Protocol | Cache, Emit, Synthesize, Decompose, Coordinator | HIGH |
| Relate | Allocate, Observe, Infer, Protocol | Coordinator, Cache, Emit, Synthesize, Context Gen, Decompose, Artifacts, Validate | HIGH |
| Report | Protocol | Coordinator, Cache, Emit, Synthesize, Decompose | HIGH |
| Requirements Derive | — | Decompose, Coordinator, Cache, Emit, Synthesize | HIGH |
| Specify | Protocol, Allocate, Observe | Emit, Synthesize, Cache, Artifacts, Decompose, Coordinator | HIGH |
| Synthesize | Infer, Regen Score, Context Gen, Specify, Protocol, Allocate, Artifacts, Cache, Observe, Relate, Coordinator, Global Learning, Report, Validate, Corrections, Decompose, Emit, Requirements Derive, Contract, Lessons | Coordinator, Cache, Emit, Decompose | MEDIUM |
| Validate | Infer, Protocol, Allocate, Relate | Artifacts, Coordinator, Cache, Emit, Synthesize, Context Gen, Decompose | HIGH |
| Cluster | — | Representativeness, Decomposer, Source Block Assign, Regen Readiness, Confidence | HIGH |
| Completeness | — | Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness | HIGH |
| Compression | — | Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness | HIGH |
| Confidence | Parser, Regen Readiness, Slicer, Validator, Decomposer, Compression, Visualize, Completeness, Differ, Source Block Assign, Coverage, Representativeness, Corrections, Cluster, Merger | Representativeness, Regen Readiness, Source Block Assign, Decomposer | MEDIUM |
| Corrections | — | Representativeness, Decomposer, Confidence, Source Block Assign, Regen Readiness | HIGH |
| Coverage | Source Block Assign | Representativeness, Decomposer, Confidence, Source Block Assign, Regen Readiness | HIGH |
| Decomposer | Parser, Differ, Validator, Compression, Visualize, Completeness, Source Block Assign, Coverage, Cluster, Representativeness, Confidence, Corrections, Regen Readiness, Slicer, Merger | Source Block Assign, Regen Readiness, Confidence, Representativeness | MEDIUM |
| Differ | Source Block Assign | Decomposer, Source Block Assign, Regen Readiness, Confidence, Representativeness | HIGH |
| Merger | Source Block Assign | Source Block Assign, Regen Readiness, Representativeness, Decomposer, Confidence | HIGH |
| Parser | Source Block Assign | Decomposer, Confidence, Source Block Assign, Representativeness, Regen Readiness | HIGH |
| Regen Readiness | Slicer, Merger, Decomposer, Visualize, Differ, Validator, Compression, Completeness, Source Block Assign, Confidence, Coverage, Cluster, Representativeness, Parser, Corrections | Source Block Assign, Confidence, Representativeness, Decomposer | MEDIUM |
| Representativeness | Source Block Assign, Confidence, Coverage, Cluster, Corrections, Regen Readiness, Slicer, Merger, Parser, Decomposer, Visualize, Differ, Validator, Compression, Completeness | Decomposer, Confidence, Source Block Assign, Regen Readiness | MEDIUM |
| Slicer | Source Block Assign | Source Block Assign, Regen Readiness, Confidence, Representativeness, Decomposer | HIGH |
| Source Block Assign | Regen Readiness, Slicer, Merger, Parser, Decomposer, Visualize, Differ, Validator, Compression, Completeness, Confidence, Coverage, Cluster, Representativeness, Corrections | Representativeness, Coverage, Validator, Decomposer, Confidence, Differ, Regen Readiness, Merger, Parser, Slicer | HIGH |
| Validator | Source Block Assign | Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness | HIGH |
| Visualize | — | Source Block Assign, Regen Readiness, Decomposer, Confidence, Representativeness | HIGH |
| Behavior | — | Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics | HIGH |
| Blocks | Display, Behavior, Ts Scanner, Generator, Protocol, Slicers, Chains, Metrics, Recursive, Body Hints, Call Graph, Kt Scanner, Grouping, Interfaces, Multi Scanner, Scan Cache | Call Graph, Scan Cache, Body Hints, Generator, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics | HIGH |
| Body Hints | Blocks | Grouping, Metrics, Interfaces, Call Graph, Multi Scanner, Scan Cache, Blocks, Kt Scanner, Generator, Slicers, Recursive | HIGH |
| Call Graph | Scan Cache, Blocks, Metrics, Behavior, Protocol, Body Hints, Chains, Grouping, Recursive, Interfaces, Kt Scanner, Multi Scanner, Display, Ts Scanner, Generator, Slicers | Grouping, Interfaces, Recursive, Multi Scanner, Metrics, Blocks, Scan Cache, Generator, Slicers, Kt Scanner | HIGH |
| Chains | — | Recursive, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Interfaces | HIGH |
| Display | — | Blocks, Kt Scanner, Generator, Slicers, Recursive, Grouping, Metrics, Interfaces, Call Graph, Multi Scanner, Scan Cache | HIGH |
| Generator | Grouping, Interfaces, Kt Scanner, Multi Scanner, Display, Blocks, Behavior, Ts Scanner, Protocol, Slicers, Scan Cache, Chains, Metrics, Recursive, Body Hints, Call Graph | Scan Cache, Blocks, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Call Graph | HIGH |
| Grouping | Body Hints, Call Graph, Recursive, Interfaces, Kt Scanner, Multi Scanner, Display, Ts Scanner, Generator, Protocol, Slicers, Scan Cache, Blocks, Chains, Metrics, Behavior | Generator, Slicers, Kt Scanner, Interfaces, Recursive, Call Graph, Multi Scanner, Metrics, Blocks, Scan Cache | HIGH |
| Interfaces | Recursive, Body Hints, Call Graph, Kt Scanner, Multi Scanner, Grouping, Generator, Scan Cache, Display, Blocks, Behavior, Ts Scanner, Protocol, Slicers, Chains, Metrics | Generator, Slicers, Recursive, Grouping, Call Graph, Multi Scanner, Metrics, Blocks, Scan Cache, Kt Scanner | HIGH |
| Kt Scanner | Multi Scanner, Grouping, Display, Ts Scanner, Generator, Slicers, Scan Cache, Blocks, Behavior, Protocol, Body Hints, Chains, Metrics, Recursive, Interfaces, Call Graph | Generator, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Slicers | HIGH |
| Metrics | Protocol, Body Hints, Chains, Recursive, Call Graph, Kt Scanner, Multi Scanner, Grouping, Interfaces, Display, Generator, Slicers, Scan Cache, Blocks, Behavior, Ts Scanner | Recursive, Call Graph, Multi Scanner, Blocks, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Interfaces | HIGH |
| Multi Scanner | Slicers, Chains, Metrics, Recursive, Body Hints, Call Graph, Kt Scanner, Grouping, Interfaces, Generator, Protocol, Scan Cache, Display, Blocks, Behavior, Ts Scanner | Slicers, Kt Scanner, Generator, Interfaces, Recursive, Grouping, Metrics, Call Graph, Scan Cache, Blocks | HIGH |
| Protocol | — | Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Multi Scanner, Interfaces, Recursive | HIGH |
| Recursive | Chains, Metrics, Interfaces, Call Graph, Kt Scanner, Multi Scanner, Grouping, Display, Ts Scanner, Generator, Slicers, Scan Cache, Blocks, Behavior, Protocol, Body Hints | Interfaces, Grouping, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner | HIGH |
| Scan Cache | Generator, Slicers, Blocks, Behavior, Ts Scanner, Protocol, Body Hints, Chains, Metrics, Recursive, Call Graph, Kt Scanner, Multi Scanner, Grouping, Interfaces, Display | Call Graph, Slicers, Kt Scanner, Generator, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Blocks | HIGH |
| Slicers | Multi Scanner, Grouping, Interfaces, Generator, Scan Cache, Display, Blocks, Behavior, Ts Scanner, Protocol, Chains, Metrics, Recursive, Body Hints, Call Graph, Kt Scanner | Multi Scanner, Scan Cache, Blocks, Kt Scanner, Generator, Recursive, Grouping, Metrics, Interfaces, Call Graph | HIGH |
| Ts Scanner | — | Blocks, Scan Cache, Kt Scanner, Generator, Slicers, Recursive, Grouping, Interfaces, Call Graph, Multi Scanner, Metrics | HIGH |
| Auto Enrich | — | Naming Context, Enrichment Context, Pipeline | MEDIUM |
| Behavior Decompose | — | Naming Context, Enrichment Context, Pipeline | MEDIUM |
| Behavior Flows | — | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Capability Inference | — | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Compaction | — | Naming Context, Enrichment Context, Pipeline | MEDIUM |
| Decompose | — | Naming Context, Enrichment Context, Pipeline | MEDIUM |
| Deep Decompose | — | Naming Context, Enrichment Context, Pipeline | MEDIUM |
| Enrich | — | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Enrichment Context | Auto Enrich, Trigger Detection, Decompose, Use Case Inference, Compaction, Behavior Decompose, Pipeline, Deep Decompose, Enrich, Capability Inference, Behavior Flows, Naming Context | Pipeline, Naming Context | MEDIUM |
| Naming Context | Trigger Detection, Decompose, Auto Enrich, Use Case Inference, Behavior Decompose, Compaction, Pipeline, Deep Decompose, Enrich, Capability Inference, Behavior Flows, Enrichment Context | Pipeline, Enrichment Context | MEDIUM |
| Pipeline | Enrich, Capability Inference, Behavior Flows, Enrichment Context, Naming Context, Trigger Detection, Auto Enrich, Decompose, Use Case Inference, Compaction, Behavior Decompose, Deep Decompose | Naming Context, Enrichment Context | MEDIUM |
| Trigger Detection | — | Naming Context, Enrichment Context, Pipeline | MEDIUM |
| Use Case Inference | — | Naming Context, Enrichment Context, Pipeline | MEDIUM |
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
**Downstream dependents (must re-test):** Relate, Cache, Synthesize, Contract, Artifacts, Context Gen, Specify, Validate, Decompose, Coordinator, Emit

### Artifacts (src-pipeline-COMP-18)

**Files:**
- `src/architecture_model/pipeline/artifacts.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Synthesize, Decompose

### Cache (src-pipeline-COMP-19)

**Files:**
- `src/architecture_model/pipeline/cache.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Synthesize, Decompose

### Context Gen (src-pipeline-COMP-20)

**Files:**
- `src/architecture_model/pipeline/context_gen.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Cache, Decompose, Coordinator

### Contract (src-pipeline-COMP-21)

**Files:**
- `src/architecture_model/pipeline/contract.py`
- `src/architecture_model/pipeline/contract_types.py`
**Downstream dependents (must re-test):** Decompose, Artifacts, Coordinator, Cache, Emit, Synthesize

### Coordinator (src-pipeline-COMP-23)

**Files:**
- `src/architecture_model/pipeline/coordinator.py`
**Downstream dependents (must re-test):** Decompose, Cache, Emit, Synthesize

### Corrections (src-pipeline-COMP-24)

**Files:**
- `src/architecture_model/pipeline/corrections.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Synthesize, Infer, Decompose, Allocate

### Decompose (src-pipeline-COMP-25)

**Files:**
- `src/architecture_model/pipeline/__init__.py`
- `src/architecture_model/pipeline/decompose.py`
- `src/architecture_model/pipeline/decompose_types.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Cache, Synthesize

### Emit (src-pipeline-COMP-27)

**Files:**
- `src/architecture_model/pipeline/emit.py`
- `src/architecture_model/pipeline/emit_types.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Cache, Synthesize

### Global Learning (src-pipeline-COMP-29)

**Files:**
- `src/architecture_model/pipeline/global_learning.py`
- `src/architecture_model/pipeline/learning.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Cache, Synthesize, Decompose

### Infer (src-pipeline-COMP-30)

**Files:**
- `src/architecture_model/pipeline/infer.py`
- `src/architecture_model/pipeline/infer_types.py`
**Downstream dependents (must re-test):** Cache, Synthesize, Allocate, Artifacts, Context Gen, Validate, Decompose, Coordinator, Emit, Relate

### Lessons (src-pipeline-COMP-33)

**Files:**
- `src/architecture_model/pipeline/lessons.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Cache, Emit, Synthesize

### Observe (src-pipeline-COMP-34)

**Files:**
- `src/architecture_model/pipeline/observe.py`
- `src/architecture_model/pipeline/observe_types.py`
**Downstream dependents (must re-test):** Coordinator, Emit, Relate, Cache, Synthesize, Infer, Allocate, Contract, Artifacts, Context Gen, Specify, Decompose

### Protocol (src-pipeline-COMP-36)

**Files:**
- `src/architecture_model/pipeline/protocol.py`
**Downstream dependents (must re-test):** Cache, Synthesize, Infer, Allocate, Contract, Context Gen, Specify, Validate, Decompose, Artifacts, Regen Score, Observe, Lessons, Global Learning, Coordinator, Emit, Report, Relate

### Regen Score (src-pipeline-COMP-37)

**Files:**
- `src/architecture_model/pipeline/regen_score.py`
**Downstream dependents (must re-test):** Cache, Emit, Synthesize, Decompose, Coordinator

### Relate (src-pipeline-COMP-38)

**Files:**
- `src/architecture_model/pipeline/relate.py`
- `src/architecture_model/pipeline/relate_types.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Synthesize, Context Gen, Decompose, Artifacts, Validate

### Report (src-pipeline-COMP-40)

**Files:**
- `src/architecture_model/pipeline/report.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Synthesize, Decompose

### Requirements Derive (src-pipeline-COMP-41)

**Files:**
- `src/architecture_model/pipeline/requirements_derive.py`
**Downstream dependents (must re-test):** Decompose, Coordinator, Cache, Emit, Synthesize

### Specify (src-pipeline-COMP-42)

**Files:**
- `src/architecture_model/pipeline/specify.py`
- `src/architecture_model/pipeline/specify_types.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Cache, Artifacts, Decompose, Coordinator

### Synthesize (src-pipeline-COMP-44)

**Files:**
- `src/architecture_model/pipeline/synthesize.py`
- `src/architecture_model/pipeline/synthesize_types.py`
**Downstream dependents (must re-test):** Coordinator, Cache, Emit, Decompose

### Validate (src-pipeline-COMP-46)

**Files:**
- `src/architecture_model/pipeline/validate.py`
- `src/architecture_model/pipeline/validate_types.py`
**Downstream dependents (must re-test):** Artifacts, Coordinator, Cache, Emit, Synthesize, Context Gen, Decompose

### Cluster (src-core-COMP-15)

**Files:**
- `src/architecture_model/core/cluster.py`
**Downstream dependents (must re-test):** Representativeness, Decomposer, Source Block Assign, Regen Readiness, Confidence

### Completeness (src-core-COMP-16)

**Files:**
- `src/architecture_model/core/completeness.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness

### Compression (src-core-COMP-17)

**Files:**
- `src/architecture_model/core/compression.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness

### Confidence (src-core-COMP-18)

**Files:**
- `src/architecture_model/core/confidence.py`
**Downstream dependents (must re-test):** Representativeness, Regen Readiness, Source Block Assign, Decomposer

### Corrections (src-core-COMP-19)

**Files:**
- `src/architecture_model/core/corrections.py`
**Downstream dependents (must re-test):** Representativeness, Decomposer, Confidence, Source Block Assign, Regen Readiness

### Coverage (src-core-COMP-20)

**Files:**
- `src/architecture_model/core/coverage.py`
**Downstream dependents (must re-test):** Representativeness, Decomposer, Confidence, Source Block Assign, Regen Readiness

### Decomposer (src-core-COMP-21)

**Files:**
- `src/architecture_model/core/decomposer.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Confidence, Representativeness

### Differ (src-core-COMP-22)

**Files:**
- `src/architecture_model/core/differ.py`
**Downstream dependents (must re-test):** Decomposer, Source Block Assign, Regen Readiness, Confidence, Representativeness

### Merger (src-core-COMP-23)

**Files:**
- `src/architecture_model/core/merger.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Representativeness, Decomposer, Confidence

### Parser (src-core-COMP-24)

**Files:**
- `src/architecture_model/core/parser.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Representativeness, Regen Readiness

### Regen Readiness (src-core-COMP-25)

**Files:**
- `src/architecture_model/core/regen_readiness.py`
**Downstream dependents (must re-test):** Source Block Assign, Confidence, Representativeness, Decomposer

### Representativeness (src-core-COMP-26)

**Files:**
- `src/architecture_model/core/representativeness.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Regen Readiness

### Slicer (src-core-COMP-27)

**Files:**
- `src/architecture_model/core/slicer.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Confidence, Representativeness, Decomposer

### Source Block Assign (src-core-COMP-28)

**Files:**
- `src/architecture_model/core/source_block_assign.py`
- `src/architecture_model/core/source_block_quality.py`
- `src/architecture_model/core/types.py`
**Downstream dependents (must re-test):** Representativeness, Coverage, Validator, Decomposer, Confidence, Differ, Regen Readiness, Merger, Parser, Slicer

### Validator (src-core-COMP-30)

**Files:**
- `src/architecture_model/core/validator.py`
**Downstream dependents (must re-test):** Decomposer, Confidence, Source Block Assign, Regen Readiness, Representativeness

### Visualize (src-core-COMP-31)

**Files:**
- `src/architecture_model/core/visualize.py`
**Downstream dependents (must re-test):** Source Block Assign, Regen Readiness, Decomposer, Confidence, Representativeness

### Behavior (src-manifest-COMP-16)

**Files:**
- `src/architecture_model/manifest/behavior.py`
**Downstream dependents (must re-test):** Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics

### Blocks (src-manifest-COMP-17)

**Files:**
- `src/architecture_model/manifest/__init__.py`
- `src/architecture_model/manifest/blocks.py`
- `src/architecture_model/manifest/types.py`
**Downstream dependents (must re-test):** Call Graph, Scan Cache, Body Hints, Generator, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics

### Body Hints (src-manifest-COMP-18)

**Files:**
- `src/architecture_model/manifest/body_hints.py`
**Downstream dependents (must re-test):** Grouping, Metrics, Interfaces, Call Graph, Multi Scanner, Scan Cache, Blocks, Kt Scanner, Generator, Slicers, Recursive

### Call Graph (src-manifest-COMP-19)

**Files:**
- `src/architecture_model/manifest/call_graph.py`
**Downstream dependents (must re-test):** Grouping, Interfaces, Recursive, Multi Scanner, Metrics, Blocks, Scan Cache, Generator, Slicers, Kt Scanner

### Chains (src-manifest-COMP-20)

**Files:**
- `src/architecture_model/manifest/chains.py`
**Downstream dependents (must re-test):** Recursive, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Interfaces

### Display (src-manifest-COMP-21)

**Files:**
- `src/architecture_model/manifest/display.py`
**Downstream dependents (must re-test):** Blocks, Kt Scanner, Generator, Slicers, Recursive, Grouping, Metrics, Interfaces, Call Graph, Multi Scanner, Scan Cache

### Generator (src-manifest-COMP-22)

**Files:**
- `src/architecture_model/manifest/generator.py`
**Downstream dependents (must re-test):** Scan Cache, Blocks, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Call Graph

### Grouping (src-manifest-COMP-23)

**Files:**
- `src/architecture_model/manifest/grouping.py`
**Downstream dependents (must re-test):** Generator, Slicers, Kt Scanner, Interfaces, Recursive, Call Graph, Multi Scanner, Metrics, Blocks, Scan Cache

### Interfaces (src-manifest-COMP-24)

**Files:**
- `src/architecture_model/manifest/interfaces.py`
**Downstream dependents (must re-test):** Generator, Slicers, Recursive, Grouping, Call Graph, Multi Scanner, Metrics, Blocks, Scan Cache, Kt Scanner

### Kt Scanner (src-manifest-COMP-25)

**Files:**
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/scanner.py`
**Downstream dependents (must re-test):** Generator, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Slicers

### Metrics (src-manifest-COMP-26)

**Files:**
- `src/architecture_model/manifest/metrics.py`
**Downstream dependents (must re-test):** Recursive, Call Graph, Multi Scanner, Blocks, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Interfaces

### Multi Scanner (src-manifest-COMP-27)

**Files:**
- `src/architecture_model/manifest/multi_scanner.py`
**Downstream dependents (must re-test):** Slicers, Kt Scanner, Generator, Interfaces, Recursive, Grouping, Metrics, Call Graph, Scan Cache, Blocks

### Protocol (src-manifest-COMP-28)

**Files:**
- `src/architecture_model/manifest/protocol.py`
**Downstream dependents (must re-test):** Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Multi Scanner, Interfaces, Recursive

### Recursive (src-manifest-COMP-29)

**Files:**
- `src/architecture_model/manifest/recursive.py`
**Downstream dependents (must re-test):** Interfaces, Grouping, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner

### Scan Cache (src-manifest-COMP-30)

**Files:**
- `src/architecture_model/manifest/scan_cache.py`
**Downstream dependents (must re-test):** Call Graph, Slicers, Kt Scanner, Generator, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Blocks

### Slicers (src-manifest-COMP-32)

**Files:**
- `src/architecture_model/manifest/slicers.py`
**Downstream dependents (must re-test):** Multi Scanner, Scan Cache, Blocks, Kt Scanner, Generator, Recursive, Grouping, Metrics, Interfaces, Call Graph

### Ts Scanner (src-manifest-COMP-33)

**Files:**
- `src/architecture_model/manifest/ts_scanner.py`
**Downstream dependents (must re-test):** Blocks, Scan Cache, Kt Scanner, Generator, Slicers, Recursive, Grouping, Interfaces, Call Graph, Multi Scanner, Metrics

### Auto Enrich (src-orchestration-COMP-1)

**Files:**
- `src/architecture_model/orchestration/auto_enrich.py`
**Downstream dependents (must re-test):** Naming Context, Enrichment Context, Pipeline

### Behavior Decompose (src-orchestration-COMP-2)

**Files:**
- `src/architecture_model/orchestration/behavior_decompose.py`
**Downstream dependents (must re-test):** Naming Context, Enrichment Context, Pipeline

### Behavior Flows (src-orchestration-COMP-3)

**Files:**
- `src/architecture_model/orchestration/behavior_flows.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Capability Inference (src-orchestration-COMP-4)

**Files:**
- `src/architecture_model/orchestration/capability_inference.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Compaction (src-orchestration-COMP-5)

**Files:**
- `src/architecture_model/orchestration/compaction.py`
**Downstream dependents (must re-test):** Naming Context, Enrichment Context, Pipeline

### Decompose (src-orchestration-COMP-6)

**Files:**
- `src/architecture_model/orchestration/decompose.py`
**Downstream dependents (must re-test):** Naming Context, Enrichment Context, Pipeline

### Deep Decompose (src-orchestration-COMP-7)

**Files:**
- `src/architecture_model/orchestration/deep_decompose.py`
**Downstream dependents (must re-test):** Naming Context, Enrichment Context, Pipeline

### Enrich (src-orchestration-COMP-8)

**Files:**
- `src/architecture_model/orchestration/enrich.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Enrichment Context (src-orchestration-COMP-9)

**Files:**
- `src/architecture_model/orchestration/enrichment_context.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context

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
**Downstream dependents (must re-test):** Naming Context, Enrichment Context, Pipeline

### Use Case Inference (src-orchestration-COMP-13)

**Files:**
- `src/architecture_model/orchestration/use_case_inference.py`
**Downstream dependents (must re-test):** Naming Context, Enrichment Context, Pipeline

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

---

---

## LLM Review

*Reviewed: 2026-08-18T23:37:27.227237+00:00 | Duration: 6382ms*

**Summary:** This maintenance manual is severely incomplete at 14% model completeness, with all 92 components lacking descriptions, responsibilities, signatures, and test contracts, rendering it nearly useless for actual maintenance purposes despite having a basic inventory and partial dependency analysis.

- The dependency impact analysis shows Allocate, Artifacts, Contract, and Context Gen as HIGH impact risk components with significant fan-in/fan-out, yet none have documented interfaces or test contracts to safeguard against breaking changes.
- Every component is classified as "service" kind regardless of actual role (scanners, parsers, CLI layers, configs), suggesting the extraction pipeline lacks differentiation logic and the taxonomy needs refinement.

<details>
<summary>Review details</summary>

**Prompt sent (truncated):**
```
Review the following architecture artifact 'docs/se/maintenance-manual.md'.
Respond ONLY in this format:
SUMMARY: <one paragraph overall assessment>
COMMENT: <specific observation>
COMMENT: <another observation>

---
---
document: Maintenance Manual
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T23:36:29Z
generator_version: 0.3.0
model_hash: 41fb0d4bec16
edition: 7
---

> **Model Completeness: F (14%)**
> Some sections may be empty due to missing model entities.
> - No interfaces
```

**Full LLM response:**
```
SUMMARY: This maintenance manual is severely incomplete at 14% model completeness, with all 92 components lacking descriptions, responsibilities, signatures, and test contracts, rendering it nearly useless for actual maintenance purposes despite having a basic inventory and partial dependency analysis.
COMMENT: The dependency impact analysis shows Allocate, Artifacts, Contract, and Context Gen as HIGH impact risk components with significant fan-in/fan-out, yet none have documented interfaces or test contracts to safeguard against breaking changes.
COMMENT: Every component is classified as "service" kind regardless of actual role (scanners, parsers, CLI layers, configs), suggesting the extraction pipeline lacks differentiation logic and the taxonomy needs refinement.
```

</details>
