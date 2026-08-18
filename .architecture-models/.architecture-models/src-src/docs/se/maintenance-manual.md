---
document: Maintenance Manual
system: Src (src)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:26Z
generator_version: 0.3.0
model_hash: 254bd5a18b33
edition: 3
---

# Maintenance Manual: Src (src)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Gate (COMP-2) | service | — | 1 | 0 | 0 |
| Parser (COMP-3) | service | — | 2 | 0 | 0 |
| Main (COMP-4) | service | — | 2 | 0 | 0 |
| Loader (COMP-5) | service | — | 1 | 0 | 0 |
| Schema (COMP-6) | service | — | 2 | 0 | 0 |
| Cluster (COMP-7) | service | — | 1 | 0 | 0 |
| Completeness (COMP-8) | service | — | 1 | 0 | 0 |
| Compression (COMP-9) | service | — | 1 | 0 | 0 |
| Confidence (COMP-10) | service | — | 1 | 0 | 0 |
| Corrections (COMP-11) | service | — | 2 | 0 | 0 |
| Coverage (COMP-12) | service | — | 1 | 0 | 0 |
| Decomposer (COMP-13) | service | — | 1 | 0 | 0 |
| Differ (COMP-14) | service | — | 1 | 0 | 0 |
| Merger (COMP-15) | service | — | 1 | 0 | 0 |
| Regen Readiness (COMP-16) | service | — | 2 | 0 | 0 |
| Representativeness (COMP-17) | service | — | 1 | 0 | 0 |
| Slicer (COMP-18) | service | — | 1 | 0 | 0 |
| Source Block Assign (COMP-19) | service | — | 2 | 0 | 0 |
| Validator (COMP-21) | service | — | 1 | 0 | 0 |
| Visualize (COMP-22) | service | — | 2 | 0 | 0 |
| Flatfiles (COMP-23) | service | — | 1 | 0 | 0 |
| Reference (COMP-24) | service | — | 1 | 0 | 0 |
| Constraint Detector (COMP-25) | service | — | 1 | 0 | 0 |
| From Artifacts (COMP-26) | service | — | 3 | 0 | 0 |
| Route Detector (COMP-28) | service | — | 1 | 0 | 0 |
| Table Parser (COMP-29) | service | — | 1 | 0 | 0 |
| Behavior (COMP-30) | service | — | 3 | 0 | 0 |
| Blocks (COMP-31) | service | — | 1 | 0 | 0 |
| Body Hints (COMP-32) | service | — | 1 | 0 | 0 |
| Call Graph (COMP-33) | service | — | 1 | 0 | 0 |
| Chains (COMP-34) | service | — | 1 | 0 | 0 |
| Display (COMP-35) | service | — | 1 | 0 | 0 |
| Generator (COMP-36) | service | — | 1 | 0 | 0 |
| Grouping (COMP-37) | service | — | 1 | 0 | 0 |
| Interfaces (COMP-38) | service | — | 1 | 0 | 0 |
| Kt Scanner (COMP-39) | service | — | 2 | 0 | 0 |
| Metrics (COMP-40) | service | — | 1 | 0 | 0 |
| Multi Scanner (COMP-41) | service | — | 1 | 0 | 0 |
| Protocol (COMP-42) | service | — | 2 | 0 | 0 |
| Recursive (COMP-43) | service | — | 1 | 0 | 0 |
| Scan Cache (COMP-44) | service | — | 2 | 0 | 0 |
| Slicers (COMP-46) | service | — | 1 | 0 | 0 |
| Ts Scanner (COMP-47) | service | — | 1 | 0 | 0 |
| Monitoring (COMP-48) | service | — | 2 | 0 | 0 |
| Auto Enrich (COMP-50) | service | — | 2 | 0 | 0 |
| Behavior Decompose (COMP-51) | service | — | 3 | 0 | 0 |
| Capability Inference (COMP-53) | service | — | 1 | 0 | 0 |
| Compaction (COMP-54) | service | — | 1 | 0 | 0 |
| Deep Decompose (COMP-56) | service | — | 1 | 0 | 0 |
| Enrichment Context (COMP-58) | service | — | 2 | 0 | 0 |
| Naming Context (COMP-59) | service | — | 1 | 0 | 0 |
| Pipeline (COMP-60) | service | — | 1 | 0 | 0 |
| Trigger Detection (COMP-61) | service | — | 1 | 0 | 0 |
| Use Case Inference (COMP-62) | service | — | 1 | 0 | 0 |
| Patterns (COMP-63) | service | — | 1 | 0 | 0 |
| Store (COMP-64) | service | — | 1 | 0 | 0 |
| Allocate (COMP-65) | service | — | 2 | 0 | 0 |
| Allocate Types (COMP-66) | service | — | 2 | 0 | 0 |
| Contract (COMP-70) | service | — | 2 | 0 | 0 |
| Coordinator (COMP-72) | service | — | 1 | 0 | 0 |
| Emit (COMP-74) | service | — | 2 | 0 | 0 |
| Global Learning (COMP-76) | service | — | 2 | 0 | 0 |
| Infer (COMP-77) | service | — | 2 | 0 | 0 |
| Lessons (COMP-80) | service | — | 1 | 0 | 0 |
| Observe (COMP-81) | service | — | 2 | 0 | 0 |
| Relate (COMP-84) | service | — | 2 | 0 | 0 |
| Report (COMP-86) | service | — | 1 | 0 | 0 |
| Requirements Derive (COMP-87) | service | — | 1 | 0 | 0 |
| Specify (COMP-88) | service | — | 2 | 0 | 0 |
| Synthesize (COMP-90) | service | — | 2 | 0 | 0 |
| Validate (COMP-92) | service | — | 2 | 0 | 0 |
| Discovery (COMP-94) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Gate | Slicer, Parser, Main, Patterns, Body Hints, Source Block Assign, Recursive, Behavior, Multi Scanner, Monitoring, Display, Corrections, Chains, Metrics, Generator, Compression, Representativeness, Ts Scanner, Completeness, Merger, Confidence, Grouping, Decomposer, Slicers, Call Graph, Visualize, Scan Cache, Validator, Protocol, Allocate Types, Coverage, Cluster, Regen Readiness, Kt Scanner, Blocks, Interfaces, Differ | — | LOW |
| Parser | Allocate Types, Coverage, Cluster, Regen Readiness, Differ, Slicer, Main, Patterns, Source Block Assign, Monitoring, Compression, Merger, Confidence, Corrections, Representativeness, Completeness, Decomposer, Visualize, Validator | Pipeline, Gate, Capability Inference, Behavior Decompose, From Artifacts, Auto Enrich, Deep Decompose, Visualize, Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Source Block Assign, Representativeness, Regen Readiness, Confidence, Compaction, Grouping, Constraint Detector | HIGH |
| Main | Visualize | Grouping, Call Graph, Constraint Detector, Use Case Inference, Blocks, Source Block Assign, Slicer, Representativeness, Confidence, Gate, Capability Inference, Slicers, Enrichment Context, Interfaces, Generator, Differ, Scan Cache, Parser, Recursive, Pipeline, From Artifacts, Kt Scanner, Coverage, Validator, Behavior Decompose, Coordinator, Body Hints, Merger, Naming Context, Decomposer, Trigger Detection, Metrics, Emit, Cluster, Auto Enrich, Deep Decompose, Regen Readiness, Behavior, Compaction, Multi Scanner, Synthesize | HIGH |
| Loader | Discovery, Schema | Behavior Decompose, From Artifacts, Recursive | MEDIUM |
| Schema | — | Behavior Decompose, Loader, Recursive, From Artifacts | MEDIUM |
| Cluster | Main, Patterns, Monitoring | Parser, From Artifacts, Deep Decompose, Visualize, Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Auto Enrich, Source Block Assign, Regen Readiness, Confidence, Compaction, Grouping, Constraint Detector, Pipeline, Representativeness, Gate, Capability Inference, Behavior Decompose | HIGH |
| Completeness | — | Visualize, Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Auto Enrich, Source Block Assign, Regen Readiness, Behavior, Compaction, Grouping, Constraint Detector, Use Case Inference, Representativeness, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts, Deep Decompose | HIGH |
| Compression | — | Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Auto Enrich, Source Block Assign, Regen Readiness, Confidence, Compaction, Parser, Grouping, Constraint Detector, Pipeline, Representativeness, Gate, Capability Inference, Behavior Decompose, From Artifacts, Deep Decompose, Visualize | HIGH |
| Confidence | Slicer, Main, Patterns, Source Block Assign, Monitoring, Compression, Merger, Corrections, Cluster, Representativeness, Completeness, Decomposer, Visualize, Parser, Validator, Allocate Types, Coverage, Regen Readiness, Differ | Visualize, Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Source Block Assign, Representativeness, Regen Readiness, Compaction, Parser, Grouping, Constraint Detector, Pipeline, From Artifacts, Gate, Capability Inference, Behavior Decompose, Auto Enrich, Deep Decompose | HIGH |
| Corrections | — | Emit, Auto Enrich, Deep Decompose, Regen Readiness, Behavior, Compaction, Synthesize, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Confidence, Gate, Capability Inference, Scan Cache, Parser, Pipeline, From Artifacts, Visualize, Allocate, Infer, Behavior Decompose, Coordinator, Body Hints, Decomposer, Trigger Detection | HIGH |
| Coverage | Allocate Types, Main, Patterns, Monitoring | Parser, Grouping, Pipeline, From Artifacts, Behavior Decompose, Trigger Detection, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Body Hints, Decomposer, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Regen Readiness, Confidence, Gate, Capability Inference | HIGH |
| Decomposer | Compression, Representativeness, Completeness, Merger, Confidence, Visualize, Cluster, Differ, Parser, Validator, Main, Allocate Types, Patterns, Coverage, Source Block Assign, Regen Readiness, Monitoring, Slicer, Corrections | Visualize, Behavior Decompose, Body Hints, Trigger Detection, Auto Enrich, Deep Decompose, Regen Readiness, Behavior, Compaction, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts | HIGH |
| Differ | Main, Patterns, Monitoring, Allocate Types | Capability Inference, Parser, Pipeline, From Artifacts, Deep Decompose, Visualize, Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Auto Enrich, Source Block Assign, Regen Readiness, Behavior, Compaction, Grouping, Constraint Detector, Use Case Inference, Representativeness, Confidence, Gate | HIGH |
| Merger | Allocate Types, Main, Patterns, Monitoring, Discovery | Visualize, Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Auto Enrich, Source Block Assign, Regen Readiness, Confidence, Compaction, Parser, Grouping, Constraint Detector, Pipeline, Representativeness, Gate, Capability Inference, Behavior Decompose, From Artifacts, Deep Decompose | HIGH |
| Regen Readiness | Slicer, Corrections, Compression, Representativeness, Completeness, Merger, Confidence, Decomposer, Visualize, Protocol, Cluster, Differ, Parser, Validator, Main, Allocate Types, Patterns, Coverage, Source Block Assign, Monitoring | Scan Cache, Parser, Pipeline, From Artifacts, Behavior Decompose, Coordinator, Body Hints, Trigger Detection, Emit, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Decomposer, Synthesize, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Confidence, Gate, Capability Inference | HIGH |
| Representativeness | Main, Patterns, Source Block Assign, Recursive, Behavior, Multi Scanner, Monitoring, Display, Confidence, Corrections, Chains, Metrics, Generator, Compression, Blocks, Ts Scanner, Completeness, Merger, Grouping, Decomposer, Slicers, Call Graph, Visualize, Scan Cache, Parser, Validator, Protocol, Allocate Types, Coverage, Cluster, Body Hints, Regen Readiness, Kt Scanner, Interfaces, Differ, Slicer | Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Auto Enrich, Source Block Assign, Regen Readiness, Behavior, Compaction, Grouping, Constraint Detector, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts, Deep Decompose, Visualize | HIGH |
| Slicer | Main, Patterns, Monitoring, Allocate Types | Regen Readiness, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts, Behavior Decompose, Trigger Detection, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Body Hints, Decomposer, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness | HIGH |
| Source Block Assign | Main, Monitoring, Compression, Representativeness, Completeness, Merger, Confidence, Corrections, Cluster, Differ, Decomposer, Visualize, Parser, Validator, Allocate Types, Patterns, Coverage, Regen Readiness, Slicer | Grouping, Constraint Detector, Use Case Inference, Representativeness, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts, Deep Decompose, Visualize, Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Auto Enrich, Regen Readiness, Behavior, Compaction | HIGH |
| Validator | Allocate Types, Main, Patterns, Monitoring | Pipeline, From Artifacts, Behavior Decompose, Trigger Detection, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Body Hints, Decomposer, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Regen Readiness, Confidence, Gate, Capability Inference, Parser | HIGH |
| Visualize | Completeness, Merger, Confidence, Decomposer, Cluster, Differ, Parser, Validator, Allocate Types, Coverage, Source Block Assign, Regen Readiness, Slicer, Corrections, Compression, Representativeness | Pipeline, From Artifacts, Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Auto Enrich, Deep Decompose, Regen Readiness, Behavior, Compaction, Main, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Confidence, Gate, Capability Inference, Parser | HIGH |
| Flatfiles | — | — | LOW |
| Reference | — | — | LOW |
| Constraint Detector | Main, Patterns, Source Block Assign, Monitoring, Corrections, Compression, Representativeness, Completeness, Merger, Confidence, Decomposer, Visualize, Validator, Allocate Types, Coverage, Cluster, Regen Readiness, Differ, Slicer, Parser | From Artifacts | LOW |
| From Artifacts | Visualize, Validator, Protocol, Allocate Types, Coverage, Cluster, Regen Readiness, Specify, Infer, Differ, Slicer, Relate, Loader, Parser, Main, Patterns, Allocate, Source Block Assign, Observe, Table Parser, Validate, Constraint Detector, Monitoring, Confidence, Corrections, Contract, Route Detector, Compression, Representativeness, Schema, Completeness, Merger, Decomposer | Emit, Synthesize, Scan Cache, Behavior Decompose, Coordinator | HIGH |
| Route Detector | — | From Artifacts | LOW |
| Table Parser | — | From Artifacts | LOW |
| Behavior | Multi Scanner, Metrics, Monitoring, Compression, Display, Merger, Confidence, Corrections, Protocol, Chains, Cluster, Generator, Representativeness, Blocks, Ts Scanner, Interfaces, Completeness, Grouping, Decomposer, Slicers, Call Graph, Visualize, Scan Cache, Parser, Validator, Allocate Types, Coverage, Body Hints, Regen Readiness, Kt Scanner, Differ, Slicer, Main, Patterns, Source Block Assign, Recursive | Enrichment Context, Interfaces, Multi Scanner, Grouping, Recursive, Blocks, Representativeness, Gate, Slicers, Generator, Scan Cache, Metrics, Pipeline, Kt Scanner, Deep Decompose, Naming Context, Trigger Detection, Call Graph, Auto Enrich | HIGH |
| Blocks | Main, Patterns, Recursive, Behavior, Multi Scanner, Monitoring, Display, Discovery, Chains, Metrics, Generator, Ts Scanner, Grouping, Slicers, Call Graph, Scan Cache, Protocol, Allocate Types, Body Hints, Kt Scanner, Interfaces | Slicers, Generator, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Trigger Detection, Call Graph, Representativeness, Interfaces, Scan Cache, Multi Scanner, Grouping, Recursive, Pipeline, Gate | HIGH |
| Body Hints | Compression, Representativeness, Completeness, Merger, Confidence, Decomposer, Visualize, Cluster, Regen Readiness, Differ, Parser, Validator, Main, Allocate Types, Patterns, Coverage, Source Block Assign, Monitoring, Slicer, Corrections | Scan Cache, Multi Scanner, Grouping, Recursive, Pipeline, Gate, Slicers, Generator, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Trigger Detection, Call Graph, Blocks, Representativeness, Interfaces | HIGH |
| Call Graph | Main, Patterns, Recursive, Multi Scanner, Metrics, Generator, Monitoring, Display, Protocol, Chains, Blocks, Ts Scanner, Interfaces, Grouping, Slicers, Scan Cache, Allocate Types, Body Hints, Behavior, Kt Scanner | Kt Scanner, Trigger Detection, Metrics, Auto Enrich, Deep Decompose, Behavior, Multi Scanner, Grouping, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Recursive, Pipeline | HIGH |
| Chains | — | Trigger Detection, Auto Enrich, Behavior, Multi Scanner, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Recursive, Metrics, Pipeline, Kt Scanner, Deep Decompose | HIGH |
| Display | — | Behavior, Multi Scanner, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Recursive, Pipeline, Trigger Detection, Metrics, Kt Scanner, Auto Enrich, Deep Decompose | HIGH |
| Generator | Kt Scanner, Blocks, Ts Scanner, Interfaces, Slicers, Main, Allocate Types, Patterns, Body Hints, Recursive, Behavior, Multi Scanner, Monitoring, Display, Chains, Metrics, Grouping, Call Graph, Scan Cache, Discovery, Protocol | Trigger Detection, Call Graph, Auto Enrich, Behavior, Multi Scanner, Grouping, Blocks, Representativeness, Gate, Slicers, Interfaces, Scan Cache, Recursive, Metrics, Pipeline, Kt Scanner, Deep Decompose | HIGH |
| Grouping | Main, Patterns, Coverage, Body Hints, Source Block Assign, Recursive, Behavior, Multi Scanner, Monitoring, Display, Corrections, Chains, Metrics, Generator, Compression, Representativeness, Ts Scanner, Completeness, Merger, Confidence, Decomposer, Slicers, Call Graph, Visualize, Scan Cache, Validator, Protocol, Allocate Types, Cluster, Regen Readiness, Kt Scanner, Blocks, Interfaces, Differ, Slicer, Parser | Trigger Detection, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Multi Scanner, Recursive, Pipeline | HIGH |
| Interfaces | Behavior, Kt Scanner, Main, Patterns, Recursive, Multi Scanner, Metrics, Monitoring, Display, Protocol, Chains, Generator, Blocks, Ts Scanner, Grouping, Slicers, Call Graph, Scan Cache, Allocate Types, Body Hints | Slicers, Generator, Metrics, Kt Scanner, Deep Decompose, Behavior, Trigger Detection, Call Graph, Auto Enrich, Scan Cache, Multi Scanner, Grouping, Recursive, Blocks, Pipeline, Representativeness, Gate | HIGH |
| Kt Scanner | Call Graph, Discovery, Protocol, Blocks, Ts Scanner, Interfaces, Grouping, Slicers, Scan Cache, Main, Allocate Types, Patterns, Body Hints, Recursive, Behavior, Multi Scanner, Monitoring, Chains, Metrics, Generator, Display | Slicers, Interfaces, Generator, Scan Cache, Multi Scanner, Recursive, Pipeline, Trigger Detection, Metrics, Auto Enrich, Deep Decompose, Behavior, Grouping, Call Graph, Blocks, Representativeness, Gate | HIGH |
| Metrics | Discovery, Protocol, Blocks, Ts Scanner, Interfaces, Grouping, Slicers, Call Graph, Scan Cache, Allocate Types, Patterns, Body Hints, Recursive, Behavior, Kt Scanner, Multi Scanner, Main, Chains, Generator, Monitoring, Display | Behavior, Trigger Detection, Call Graph, Auto Enrich, Interfaces, Multi Scanner, Grouping, Recursive, Blocks, Representativeness, Gate, Slicers, Generator, Scan Cache, Pipeline, Kt Scanner, Deep Decompose | HIGH |
| Multi Scanner | Body Hints, Recursive, Behavior, Kt Scanner, Monitoring, Display, Chains, Metrics, Generator, Call Graph, Scan Cache, Protocol, Blocks, Ts Scanner, Interfaces, Grouping, Slicers, Main, Allocate Types, Patterns | Behavior, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Recursive, Metrics, Pipeline, Kt Scanner, Deep Decompose, Trigger Detection, Auto Enrich | HIGH |
| Protocol | — | Metrics, From Artifacts, Emit, Observe, Kt Scanner, Deep Decompose, Infer, Behavior, Synthesize, Trigger Detection, Call Graph, Auto Enrich, Regen Readiness, Contract, Lessons, Enrichment Context, Interfaces, Scan Cache, Multi Scanner, Global Learning, Grouping, Recursive, Blocks, Pipeline, Representativeness, Specify, Gate, Report, Allocate, Slicers, Behavior Decompose, Generator, Relate, Validate, Coordinator | HIGH |
| Recursive | Allocate Types, Body Hints, Behavior, Kt Scanner, Main, Patterns, Multi Scanner, Metrics, Monitoring, Display, Discovery, Protocol, Chains, Generator, Blocks, Ts Scanner, Schema, Interfaces, Grouping, Slicers, Call Graph, Loader, Scan Cache | Multi Scanner, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Metrics, Pipeline, Kt Scanner, Deep Decompose, Trigger Detection, Auto Enrich, Behavior | HIGH |
| Scan Cache | Body Hints, Global Learning, Observe, Regen Readiness, Specify, Kt Scanner, Main, Patterns, Allocate, Pipeline, Coordinator, Recursive, Lessons, Behavior, Validate, Multi Scanner, Monitoring, Display, Corrections, From Artifacts, Protocol, Behavior Decompose, Chains, Contract, Metrics, Generator, Report, Requirements Derive, Infer, Blocks, Ts Scanner, Enrichment Context, Interfaces, Grouping, Relate, Slicers, Call Graph, Emit, Synthesize, Allocate Types | Pipeline, Behavior Decompose, Coordinator, Trigger Detection, Metrics, Emit, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Multi Scanner, Synthesize, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Recursive | HIGH |
| Slicers | Kt Scanner, Blocks, Ts Scanner, Interfaces, Main, Allocate Types, Patterns, Body Hints, Recursive, Behavior, Multi Scanner, Monitoring, Display, Chains, Metrics, Generator, Grouping, Call Graph, Scan Cache, Protocol | Generator, Trigger Detection, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Grouping, Call Graph, Blocks, Representativeness, Gate, Interfaces, Scan Cache, Multi Scanner, Recursive, Pipeline | HIGH |
| Ts Scanner | — | Slicers, Generator, Trigger Detection, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Grouping, Call Graph, Blocks, Representativeness, Gate, Interfaces, Scan Cache, Multi Scanner, Recursive, Pipeline | HIGH |
| Monitoring | — | Behavior, Compaction, Multi Scanner, Synthesize, Grouping, Call Graph, Constraint Detector, Use Case Inference, Blocks, Source Block Assign, Slicer, Representativeness, Confidence, Gate, Capability Inference, Slicers, Enrichment Context, Interfaces, Generator, Differ, Scan Cache, Parser, Recursive, Pipeline, From Artifacts, Kt Scanner, Coverage, Validator, Behavior Decompose, Coordinator, Body Hints, Merger, Naming Context, Decomposer, Trigger Detection, Metrics, Emit, Cluster, Auto Enrich, Deep Decompose, Regen Readiness | HIGH |
| Auto Enrich | Corrections, Chains, Metrics, Generator, Compression, Representativeness, Blocks, Ts Scanner, Completeness, Merger, Grouping, Decomposer, Slicers, Call Graph, Visualize, Scan Cache, Parser, Validator, Protocol, Allocate Types, Coverage, Cluster, Body Hints, Regen Readiness, Kt Scanner, Interfaces, Differ, Slicer, Main, Patterns, Source Block Assign, Recursive, Behavior, Multi Scanner, Monitoring, Display, Confidence | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Behavior Decompose | Report, Requirements Derive, Representativeness, Infer, Schema, Enrichment Context, Completeness, Decomposer, Relate, Loader, Visualize, Scan Cache, Emit, Parser, Validator, Synthesize, Allocate Types, Coverage, Global Learning, Observe, Regen Readiness, Specify, Differ, Slicer, Main, Patterns, Allocate, Pipeline, Source Block Assign, Coordinator, Lessons, Validate, Monitoring, Compression, Merger, Confidence, Corrections, From Artifacts, Protocol, Contract, Cluster | Naming Context, Emit, Synthesize, Enrichment Context, Scan Cache, Pipeline, Coordinator | HIGH |
| Capability Inference | Differ, Slicer, Parser, Main, Patterns, Source Block Assign, Monitoring, Corrections, Compression, Representativeness, Completeness, Merger, Confidence, Decomposer, Visualize, Validator, Allocate Types, Coverage, Cluster, Regen Readiness | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Compaction | Monitoring, Corrections, Compression, Representativeness, Completeness, Merger, Confidence, Decomposer, Visualize, Validator, Allocate Types, Coverage, Cluster, Regen Readiness, Differ, Slicer, Parser, Main, Patterns, Source Block Assign | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Deep Decompose | Corrections, Protocol, Cluster, Blocks, Ts Scanner, Interfaces, Differ, Grouping, Decomposer, Slicers, Call Graph, Visualize, Scan Cache, Parser, Validator, Allocate Types, Patterns, Coverage, Body Hints, Source Block Assign, Regen Readiness, Recursive, Behavior, Kt Scanner, Multi Scanner, Slicer, Main, Chains, Metrics, Generator, Monitoring, Compression, Representativeness, Completeness, Merger, Confidence, Display | Naming Context, Enrichment Context, Pipeline | MEDIUM |
| Enrichment Context | Behavior, Main, Patterns, Pipeline, Validate, Monitoring, Naming Context, Protocol, Behavior Decompose, Use Case Inference, Capability Inference, Compaction, Infer, Relate, Deep Decompose, Allocate Types, Allocate, Auto Enrich, Observe, Trigger Detection | Behavior Decompose, Pipeline, Emit, Coordinator, Naming Context, Synthesize, Scan Cache | HIGH |
| Naming Context | Behavior Decompose, Pipeline, Deep Decompose, Use Case Inference, Capability Inference, Auto Enrich, Compaction, Enrichment Context, Main, Patterns, Trigger Detection, Behavior, Monitoring | Enrichment Context, Pipeline | MEDIUM |
| Pipeline | Visualize, Scan Cache, Parser, Validator, Use Case Inference, Allocate Types, Coverage, Body Hints, Capability Inference, Auto Enrich, Regen Readiness, Compaction, Kt Scanner, Enrichment Context, Differ, Slicer, Main, Patterns, Source Block Assign, Trigger Detection, Recursive, Behavior, Multi Scanner, Monitoring, Compression, Display, Merger, Confidence, Corrections, Naming Context, Protocol, Behavior Decompose, Chains, Cluster, Metrics, Generator, Representativeness, Blocks, Ts Scanner, Completeness, Interfaces, Grouping, Decomposer, Slicers, Call Graph, Deep Decompose | Naming Context, Synthesize, Enrichment Context, Scan Cache, Behavior Decompose, Emit, Coordinator | HIGH |
| Trigger Detection | Chains, Metrics, Generator, Compression, Representativeness, Ts Scanner, Completeness, Confidence, Merger, Grouping, Decomposer, Slicers, Call Graph, Visualize, Scan Cache, Validator, Protocol, Allocate Types, Coverage, Cluster, Regen Readiness, Kt Scanner, Blocks, Interfaces, Differ, Slicer, Parser, Main, Patterns, Body Hints, Source Block Assign, Recursive, Behavior, Multi Scanner, Monitoring, Display, Corrections | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Use Case Inference | Main, Patterns, Source Block Assign, Monitoring, Compression, Representativeness, Merger, Confidence, Corrections, Cluster, Completeness, Decomposer, Visualize, Parser, Validator, Allocate Types, Coverage, Regen Readiness, Differ, Slicer | Pipeline, Naming Context, Enrichment Context | MEDIUM |
| Patterns | — | Synthesize, Grouping, Call Graph, Constraint Detector, Use Case Inference, Blocks, Slicer, Representativeness, Confidence, Gate, Capability Inference, Slicers, Enrichment Context, Interfaces, Generator, Differ, Scan Cache, Parser, Recursive, Metrics, Pipeline, From Artifacts, Emit, Kt Scanner, Coverage, Deep Decompose, Validator, Behavior Decompose, Coordinator, Body Hints, Merger, Naming Context, Decomposer, Trigger Detection, Cluster, Auto Enrich, Source Block Assign, Regen Readiness, Behavior, Compaction, Multi Scanner | HIGH |
| Store | — | — | LOW |
| Allocate | Infer, Allocate Types, Observe, Corrections, Protocol | Scan Cache, Validate, From Artifacts, Emit, Specify, Behavior Decompose, Relate, Coordinator, Synthesize, Contract, Enrichment Context | HIGH |
| Allocate Types | — | Parser, Recursive, Pipeline, From Artifacts, Observe, Coverage, Specify, Validator, Allocate, Slicers, Infer, Behavior Decompose, Generator, Relate, Validate, Merger, Trigger Detection, Metrics, Emit, Kt Scanner, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Body Hints, Decomposer, Synthesize, Grouping, Call Graph, Constraint Detector, Use Case Inference, Blocks, Source Block Assign, Slicer, Representativeness, Regen Readiness, Contract, Confidence, Gate, Capability Inference, Enrichment Context, Interfaces, Differ, Scan Cache, Multi Scanner | HIGH |
| Contract | Protocol, Allocate Types, Allocate, Observe | Emit, Synthesize, Scan Cache, From Artifacts, Behavior Decompose, Coordinator | HIGH |
| Coordinator | Requirements Derive, Report, Relate, Scan Cache, Emit, Synthesize, Global Learning, Regen Readiness, Specify, Infer, Enrichment Context, Main, Patterns, Allocate, Observe, Lessons, Validate, Monitoring, Corrections, From Artifacts, Protocol, Behavior Decompose, Pipeline, Contract | Scan Cache, Emit, Behavior Decompose, Synthesize | MEDIUM |
| Emit | Corrections, From Artifacts, Protocol, Behavior Decompose, Contract, Global Learning, Specify, Report, Requirements Derive, Infer, Enrichment Context, Relate, Scan Cache, Synthesize, Allocate Types, Patterns, Allocate, Observe, Regen Readiness, Coordinator, Lessons, Main, Pipeline, Validate, Monitoring | Behavior Decompose, Coordinator, Synthesize, Scan Cache | MEDIUM |
| Global Learning | Protocol | Scan Cache, Emit, Behavior Decompose, Coordinator, Synthesize | HIGH |
| Infer | Protocol, Allocate Types, Observe, Corrections | Allocate, Behavior Decompose, Validate, From Artifacts, Emit, Relate, Coordinator, Synthesize, Enrichment Context, Scan Cache | HIGH |
| Lessons | Protocol | Synthesize, Scan Cache, Emit, Behavior Decompose, Coordinator | HIGH |
| Observe | Protocol, Allocate Types | Scan Cache, Allocate, Behavior Decompose, Relate, From Artifacts, Emit, Specify, Infer, Coordinator, Synthesize, Contract, Enrichment Context | HIGH |
| Relate | Allocate Types, Observe, Infer, Allocate, Protocol | Behavior Decompose, Validate, Coordinator, From Artifacts, Emit, Synthesize, Enrichment Context, Scan Cache | HIGH |
| Report | Protocol | Behavior Decompose, Coordinator, Emit, Synthesize, Scan Cache | HIGH |
| Requirements Derive | — | Behavior Decompose, Coordinator, Emit, Synthesize, Scan Cache | HIGH |
| Specify | Allocate Types, Allocate, Observe, Protocol | Scan Cache, From Artifacts, Emit, Behavior Decompose, Coordinator, Synthesize | HIGH |
| Synthesize | Patterns, Pipeline, Lessons, Validate, Monitoring, From Artifacts, Corrections, Protocol, Behavior Decompose, Contract, Global Learning, Specify, Requirements Derive, Report, Infer, Enrichment Context, Relate, Scan Cache, Emit, Allocate Types, Allocate, Observe, Regen Readiness, Coordinator, Main | Behavior Decompose, Coordinator, Emit, Scan Cache | MEDIUM |
| Validate | Infer, Relate, Allocate Types, Allocate, Protocol | Synthesize, Enrichment Context, Scan Cache, From Artifacts, Behavior Decompose, Coordinator, Emit | HIGH |
| Discovery | — | Metrics, Kt Scanner, Loader, Blocks, Recursive, Generator, Merger | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Gate (COMP-2)

**Files:**
- `src/architecture_model/authoring/gate.py`

### Parser (COMP-3)

**Files:**
- `src/architecture_model/authoring/parser.py`
- `src/architecture_model/core/parser.py`
**Downstream dependents (must re-test):** Pipeline, Gate, Capability Inference, Behavior Decompose, From Artifacts, Auto Enrich, Deep Decompose, Visualize, Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Source Block Assign, Representativeness, Regen Readiness, Confidence, Compaction, Grouping, Constraint Detector

### Main (COMP-4)

**Files:**
- `src/architecture_model/__main__.py`
- `src/architecture_model/cli/main.py`
**Downstream dependents (must re-test):** Grouping, Call Graph, Constraint Detector, Use Case Inference, Blocks, Source Block Assign, Slicer, Representativeness, Confidence, Gate, Capability Inference, Slicers, Enrichment Context, Interfaces, Generator, Differ, Scan Cache, Parser, Recursive, Pipeline, From Artifacts, Kt Scanner, Coverage, Validator, Behavior Decompose, Coordinator, Body Hints, Merger, Naming Context, Decomposer, Trigger Detection, Metrics, Emit, Cluster, Auto Enrich, Deep Decompose, Regen Readiness, Behavior, Compaction, Multi Scanner, Synthesize

### Loader (COMP-5)

**Files:**
- `src/architecture_model/config/loader.py`
**Downstream dependents (must re-test):** Behavior Decompose, From Artifacts, Recursive

### Schema (COMP-6)

**Files:**
- `src/architecture_model/config/schema.py`
- `src/architecture_model/profiles/schema.py`
**Downstream dependents (must re-test):** Behavior Decompose, Loader, Recursive, From Artifacts

### Cluster (COMP-7)

**Files:**
- `src/architecture_model/core/cluster.py`
**Downstream dependents (must re-test):** Parser, From Artifacts, Deep Decompose, Visualize, Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Auto Enrich, Source Block Assign, Regen Readiness, Confidence, Compaction, Grouping, Constraint Detector, Pipeline, Representativeness, Gate, Capability Inference, Behavior Decompose

### Completeness (COMP-8)

**Files:**
- `src/architecture_model/core/completeness.py`
**Downstream dependents (must re-test):** Visualize, Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Auto Enrich, Source Block Assign, Regen Readiness, Behavior, Compaction, Grouping, Constraint Detector, Use Case Inference, Representativeness, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts, Deep Decompose

### Compression (COMP-9)

**Files:**
- `src/architecture_model/core/compression.py`
**Downstream dependents (must re-test):** Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Auto Enrich, Source Block Assign, Regen Readiness, Confidence, Compaction, Parser, Grouping, Constraint Detector, Pipeline, Representativeness, Gate, Capability Inference, Behavior Decompose, From Artifacts, Deep Decompose, Visualize

### Confidence (COMP-10)

**Files:**
- `src/architecture_model/core/confidence.py`
**Downstream dependents (must re-test):** Visualize, Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Source Block Assign, Representativeness, Regen Readiness, Compaction, Parser, Grouping, Constraint Detector, Pipeline, From Artifacts, Gate, Capability Inference, Behavior Decompose, Auto Enrich, Deep Decompose

### Corrections (COMP-11)

**Files:**
- `src/architecture_model/core/corrections.py`
- `src/architecture_model/pipeline/corrections.py`
**Downstream dependents (must re-test):** Emit, Auto Enrich, Deep Decompose, Regen Readiness, Behavior, Compaction, Synthesize, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Confidence, Gate, Capability Inference, Scan Cache, Parser, Pipeline, From Artifacts, Visualize, Allocate, Infer, Behavior Decompose, Coordinator, Body Hints, Decomposer, Trigger Detection

### Coverage (COMP-12)

**Files:**
- `src/architecture_model/core/coverage.py`
**Downstream dependents (must re-test):** Parser, Grouping, Pipeline, From Artifacts, Behavior Decompose, Trigger Detection, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Body Hints, Decomposer, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Regen Readiness, Confidence, Gate, Capability Inference

### Decomposer (COMP-13)

**Files:**
- `src/architecture_model/core/decomposer.py`
**Downstream dependents (must re-test):** Visualize, Behavior Decompose, Body Hints, Trigger Detection, Auto Enrich, Deep Decompose, Regen Readiness, Behavior, Compaction, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts

### Differ (COMP-14)

**Files:**
- `src/architecture_model/core/differ.py`
**Downstream dependents (must re-test):** Capability Inference, Parser, Pipeline, From Artifacts, Deep Decompose, Visualize, Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Auto Enrich, Source Block Assign, Regen Readiness, Behavior, Compaction, Grouping, Constraint Detector, Use Case Inference, Representativeness, Confidence, Gate

### Merger (COMP-15)

**Files:**
- `src/architecture_model/core/merger.py`
**Downstream dependents (must re-test):** Visualize, Behavior, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Auto Enrich, Source Block Assign, Regen Readiness, Confidence, Compaction, Parser, Grouping, Constraint Detector, Pipeline, Representativeness, Gate, Capability Inference, Behavior Decompose, From Artifacts, Deep Decompose

### Regen Readiness (COMP-16)

**Files:**
- `src/architecture_model/core/regen_readiness.py`
- `src/architecture_model/pipeline/regen_score.py`
**Downstream dependents (must re-test):** Scan Cache, Parser, Pipeline, From Artifacts, Behavior Decompose, Coordinator, Body Hints, Trigger Detection, Emit, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Decomposer, Synthesize, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Confidence, Gate, Capability Inference

### Representativeness (COMP-17)

**Files:**
- `src/architecture_model/core/representativeness.py`
**Downstream dependents (must re-test):** Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Use Case Inference, Auto Enrich, Source Block Assign, Regen Readiness, Behavior, Compaction, Grouping, Constraint Detector, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts, Deep Decompose, Visualize

### Slicer (COMP-18)

**Files:**
- `src/architecture_model/core/slicer.py`
**Downstream dependents (must re-test):** Regen Readiness, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts, Behavior Decompose, Trigger Detection, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Body Hints, Decomposer, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness

### Source Block Assign (COMP-19)

**Files:**
- `src/architecture_model/core/source_block_assign.py`
- `src/architecture_model/core/source_block_quality.py`
**Downstream dependents (must re-test):** Grouping, Constraint Detector, Use Case Inference, Representativeness, Confidence, Gate, Capability Inference, Parser, Pipeline, From Artifacts, Deep Decompose, Visualize, Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Auto Enrich, Regen Readiness, Behavior, Compaction

### Validator (COMP-21)

**Files:**
- `src/architecture_model/core/validator.py`
**Downstream dependents (must re-test):** Pipeline, From Artifacts, Behavior Decompose, Trigger Detection, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Body Hints, Decomposer, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Regen Readiness, Confidence, Gate, Capability Inference, Parser

### Visualize (COMP-22)

**Files:**
- `src/architecture_model/cli/visualize.py`
- `src/architecture_model/core/visualize.py`
**Downstream dependents (must re-test):** Pipeline, From Artifacts, Behavior Decompose, Body Hints, Decomposer, Trigger Detection, Auto Enrich, Deep Decompose, Regen Readiness, Behavior, Compaction, Main, Grouping, Constraint Detector, Use Case Inference, Source Block Assign, Representativeness, Confidence, Gate, Capability Inference, Parser

### Flatfiles (COMP-23)

**Files:**
- `src/architecture_model/export/flatfiles.py`

### Reference (COMP-24)

**Files:**
- `src/architecture_model/export/reference.py`

### Constraint Detector (COMP-25)

**Files:**
- `src/architecture_model/extract/constraint_detector.py`
**Downstream dependents (must re-test):** From Artifacts

### From Artifacts (COMP-26)

**Files:**
- `src/architecture_model/extract/from_artifacts.py`
- `src/architecture_model/extract/from_code.py`
- `src/architecture_model/pipeline/artifacts.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Scan Cache, Behavior Decompose, Coordinator

### Route Detector (COMP-28)

**Files:**
- `src/architecture_model/extract/route_detector.py`
**Downstream dependents (must re-test):** From Artifacts

### Table Parser (COMP-29)

**Files:**
- `src/architecture_model/extract/table_parser.py`
**Downstream dependents (must re-test):** From Artifacts

### Behavior (COMP-30)

**Files:**
- `src/architecture_model/manifest/behavior.py`
- `src/architecture_model/orchestration/behavior_decompose.py`
- `src/architecture_model/orchestration/behavior_flows.py`
**Downstream dependents (must re-test):** Enrichment Context, Interfaces, Multi Scanner, Grouping, Recursive, Blocks, Representativeness, Gate, Slicers, Generator, Scan Cache, Metrics, Pipeline, Kt Scanner, Deep Decompose, Naming Context, Trigger Detection, Call Graph, Auto Enrich

### Blocks (COMP-31)

**Files:**
- `src/architecture_model/manifest/blocks.py`
**Downstream dependents (must re-test):** Slicers, Generator, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Trigger Detection, Call Graph, Representativeness, Interfaces, Scan Cache, Multi Scanner, Grouping, Recursive, Pipeline, Gate

### Body Hints (COMP-32)

**Files:**
- `src/architecture_model/manifest/body_hints.py`
**Downstream dependents (must re-test):** Scan Cache, Multi Scanner, Grouping, Recursive, Pipeline, Gate, Slicers, Generator, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Trigger Detection, Call Graph, Blocks, Representativeness, Interfaces

### Call Graph (COMP-33)

**Files:**
- `src/architecture_model/manifest/call_graph.py`
**Downstream dependents (must re-test):** Kt Scanner, Trigger Detection, Metrics, Auto Enrich, Deep Decompose, Behavior, Multi Scanner, Grouping, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Recursive, Pipeline

### Chains (COMP-34)

**Files:**
- `src/architecture_model/manifest/chains.py`
**Downstream dependents (must re-test):** Trigger Detection, Auto Enrich, Behavior, Multi Scanner, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Recursive, Metrics, Pipeline, Kt Scanner, Deep Decompose

### Display (COMP-35)

**Files:**
- `src/architecture_model/manifest/display.py`
**Downstream dependents (must re-test):** Behavior, Multi Scanner, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Recursive, Pipeline, Trigger Detection, Metrics, Kt Scanner, Auto Enrich, Deep Decompose

### Generator (COMP-36)

**Files:**
- `src/architecture_model/manifest/generator.py`
**Downstream dependents (must re-test):** Trigger Detection, Call Graph, Auto Enrich, Behavior, Multi Scanner, Grouping, Blocks, Representativeness, Gate, Slicers, Interfaces, Scan Cache, Recursive, Metrics, Pipeline, Kt Scanner, Deep Decompose

### Grouping (COMP-37)

**Files:**
- `src/architecture_model/manifest/grouping.py`
**Downstream dependents (must re-test):** Trigger Detection, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Multi Scanner, Recursive, Pipeline

### Interfaces (COMP-38)

**Files:**
- `src/architecture_model/manifest/interfaces.py`
**Downstream dependents (must re-test):** Slicers, Generator, Metrics, Kt Scanner, Deep Decompose, Behavior, Trigger Detection, Call Graph, Auto Enrich, Scan Cache, Multi Scanner, Grouping, Recursive, Blocks, Pipeline, Representativeness, Gate

### Kt Scanner (COMP-39)

**Files:**
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/scanner.py`
**Downstream dependents (must re-test):** Slicers, Interfaces, Generator, Scan Cache, Multi Scanner, Recursive, Pipeline, Trigger Detection, Metrics, Auto Enrich, Deep Decompose, Behavior, Grouping, Call Graph, Blocks, Representativeness, Gate

### Metrics (COMP-40)

**Files:**
- `src/architecture_model/manifest/metrics.py`
**Downstream dependents (must re-test):** Behavior, Trigger Detection, Call Graph, Auto Enrich, Interfaces, Multi Scanner, Grouping, Recursive, Blocks, Representativeness, Gate, Slicers, Generator, Scan Cache, Pipeline, Kt Scanner, Deep Decompose

### Multi Scanner (COMP-41)

**Files:**
- `src/architecture_model/manifest/multi_scanner.py`
**Downstream dependents (must re-test):** Behavior, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Recursive, Metrics, Pipeline, Kt Scanner, Deep Decompose, Trigger Detection, Auto Enrich

### Protocol (COMP-42)

**Files:**
- `src/architecture_model/manifest/protocol.py`
- `src/architecture_model/pipeline/protocol.py`
**Downstream dependents (must re-test):** Metrics, From Artifacts, Emit, Observe, Kt Scanner, Deep Decompose, Infer, Behavior, Synthesize, Trigger Detection, Call Graph, Auto Enrich, Regen Readiness, Contract, Lessons, Enrichment Context, Interfaces, Scan Cache, Multi Scanner, Global Learning, Grouping, Recursive, Blocks, Pipeline, Representativeness, Specify, Gate, Report, Allocate, Slicers, Behavior Decompose, Generator, Relate, Validate, Coordinator

### Recursive (COMP-43)

**Files:**
- `src/architecture_model/manifest/recursive.py`
**Downstream dependents (must re-test):** Multi Scanner, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Scan Cache, Metrics, Pipeline, Kt Scanner, Deep Decompose, Trigger Detection, Auto Enrich, Behavior

### Scan Cache (COMP-44)

**Files:**
- `src/architecture_model/manifest/scan_cache.py`
- `src/architecture_model/pipeline/cache.py`
**Downstream dependents (must re-test):** Pipeline, Behavior Decompose, Coordinator, Trigger Detection, Metrics, Emit, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Multi Scanner, Synthesize, Grouping, Call Graph, Blocks, Representativeness, Gate, Slicers, Interfaces, Generator, Recursive

### Slicers (COMP-46)

**Files:**
- `src/architecture_model/manifest/slicers.py`
**Downstream dependents (must re-test):** Generator, Trigger Detection, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Grouping, Call Graph, Blocks, Representativeness, Gate, Interfaces, Scan Cache, Multi Scanner, Recursive, Pipeline

### Ts Scanner (COMP-47)

**Files:**
- `src/architecture_model/manifest/ts_scanner.py`
**Downstream dependents (must re-test):** Slicers, Generator, Trigger Detection, Metrics, Kt Scanner, Auto Enrich, Deep Decompose, Behavior, Grouping, Call Graph, Blocks, Representativeness, Gate, Interfaces, Scan Cache, Multi Scanner, Recursive, Pipeline

### Monitoring (COMP-48)

**Files:**
- `src/architecture_model/monitoring.py`
- `src/architecture_model/monitoring_checks.py`
**Downstream dependents (must re-test):** Behavior, Compaction, Multi Scanner, Synthesize, Grouping, Call Graph, Constraint Detector, Use Case Inference, Blocks, Source Block Assign, Slicer, Representativeness, Confidence, Gate, Capability Inference, Slicers, Enrichment Context, Interfaces, Generator, Differ, Scan Cache, Parser, Recursive, Pipeline, From Artifacts, Kt Scanner, Coverage, Validator, Behavior Decompose, Coordinator, Body Hints, Merger, Naming Context, Decomposer, Trigger Detection, Metrics, Emit, Cluster, Auto Enrich, Deep Decompose, Regen Readiness

### Auto Enrich (COMP-50)

**Files:**
- `src/architecture_model/orchestration/auto_enrich.py`
- `src/architecture_model/orchestration/enrich.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Behavior Decompose (COMP-51)

**Files:**
- `src/architecture_model/orchestration/decompose.py`
- `src/architecture_model/pipeline/decompose.py`
- `src/architecture_model/pipeline/decompose_types.py`
**Downstream dependents (must re-test):** Naming Context, Emit, Synthesize, Enrichment Context, Scan Cache, Pipeline, Coordinator

### Capability Inference (COMP-53)

**Files:**
- `src/architecture_model/orchestration/capability_inference.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Compaction (COMP-54)

**Files:**
- `src/architecture_model/orchestration/compaction.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Deep Decompose (COMP-56)

**Files:**
- `src/architecture_model/orchestration/deep_decompose.py`
**Downstream dependents (must re-test):** Naming Context, Enrichment Context, Pipeline

### Enrichment Context (COMP-58)

**Files:**
- `src/architecture_model/orchestration/enrichment_context.py`
- `src/architecture_model/pipeline/context_gen.py`
**Downstream dependents (must re-test):** Behavior Decompose, Pipeline, Emit, Coordinator, Naming Context, Synthesize, Scan Cache

### Naming Context (COMP-59)

**Files:**
- `src/architecture_model/orchestration/naming_context.py`
**Downstream dependents (must re-test):** Enrichment Context, Pipeline

### Pipeline (COMP-60)

**Files:**
- `src/architecture_model/orchestration/pipeline.py`
**Downstream dependents (must re-test):** Naming Context, Synthesize, Enrichment Context, Scan Cache, Behavior Decompose, Emit, Coordinator

### Trigger Detection (COMP-61)

**Files:**
- `src/architecture_model/orchestration/trigger_detection.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Use Case Inference (COMP-62)

**Files:**
- `src/architecture_model/orchestration/use_case_inference.py`
**Downstream dependents (must re-test):** Pipeline, Naming Context, Enrichment Context

### Patterns (COMP-63)

**Files:**
- `src/architecture_model/patterns.py`
**Downstream dependents (must re-test):** Synthesize, Grouping, Call Graph, Constraint Detector, Use Case Inference, Blocks, Slicer, Representativeness, Confidence, Gate, Capability Inference, Slicers, Enrichment Context, Interfaces, Generator, Differ, Scan Cache, Parser, Recursive, Metrics, Pipeline, From Artifacts, Emit, Kt Scanner, Coverage, Deep Decompose, Validator, Behavior Decompose, Coordinator, Body Hints, Merger, Naming Context, Decomposer, Trigger Detection, Cluster, Auto Enrich, Source Block Assign, Regen Readiness, Behavior, Compaction, Multi Scanner

### Store (COMP-64)

**Files:**
- `src/architecture_model/persistence/store.py`

### Allocate (COMP-65)

**Files:**
- `src/architecture_model/pipeline/allocate.py`
- `src/architecture_model/pipeline/allocate_types.py`
**Downstream dependents (must re-test):** Scan Cache, Validate, From Artifacts, Emit, Specify, Behavior Decompose, Relate, Coordinator, Synthesize, Contract, Enrichment Context

### Allocate Types (COMP-66)

**Files:**
- `src/architecture_model/core/types.py`
- `src/architecture_model/manifest/types.py`
**Downstream dependents (must re-test):** Parser, Recursive, Pipeline, From Artifacts, Observe, Coverage, Specify, Validator, Allocate, Slicers, Infer, Behavior Decompose, Generator, Relate, Validate, Merger, Trigger Detection, Metrics, Emit, Kt Scanner, Auto Enrich, Deep Decompose, Visualize, Behavior, Compaction, Body Hints, Decomposer, Synthesize, Grouping, Call Graph, Constraint Detector, Use Case Inference, Blocks, Source Block Assign, Slicer, Representativeness, Regen Readiness, Contract, Confidence, Gate, Capability Inference, Enrichment Context, Interfaces, Differ, Scan Cache, Multi Scanner

### Contract (COMP-70)

**Files:**
- `src/architecture_model/pipeline/contract.py`
- `src/architecture_model/pipeline/contract_types.py`
**Downstream dependents (must re-test):** Emit, Synthesize, Scan Cache, From Artifacts, Behavior Decompose, Coordinator

### Coordinator (COMP-72)

**Files:**
- `src/architecture_model/pipeline/coordinator.py`
**Downstream dependents (must re-test):** Scan Cache, Emit, Behavior Decompose, Synthesize

### Emit (COMP-74)

**Files:**
- `src/architecture_model/pipeline/emit.py`
- `src/architecture_model/pipeline/emit_types.py`
**Downstream dependents (must re-test):** Behavior Decompose, Coordinator, Synthesize, Scan Cache

### Global Learning (COMP-76)

**Files:**
- `src/architecture_model/pipeline/global_learning.py`
- `src/architecture_model/pipeline/learning.py`
**Downstream dependents (must re-test):** Scan Cache, Emit, Behavior Decompose, Coordinator, Synthesize

### Infer (COMP-77)

**Files:**
- `src/architecture_model/pipeline/infer.py`
- `src/architecture_model/pipeline/infer_types.py`
**Downstream dependents (must re-test):** Allocate, Behavior Decompose, Validate, From Artifacts, Emit, Relate, Coordinator, Synthesize, Enrichment Context, Scan Cache

### Lessons (COMP-80)

**Files:**
- `src/architecture_model/pipeline/lessons.py`
**Downstream dependents (must re-test):** Synthesize, Scan Cache, Emit, Behavior Decompose, Coordinator

### Observe (COMP-81)

**Files:**
- `src/architecture_model/pipeline/observe.py`
- `src/architecture_model/pipeline/observe_types.py`
**Downstream dependents (must re-test):** Scan Cache, Allocate, Behavior Decompose, Relate, From Artifacts, Emit, Specify, Infer, Coordinator, Synthesize, Contract, Enrichment Context

### Relate (COMP-84)

**Files:**
- `src/architecture_model/pipeline/relate.py`
- `src/architecture_model/pipeline/relate_types.py`
**Downstream dependents (must re-test):** Behavior Decompose, Validate, Coordinator, From Artifacts, Emit, Synthesize, Enrichment Context, Scan Cache

### Report (COMP-86)

**Files:**
- `src/architecture_model/pipeline/report.py`
**Downstream dependents (must re-test):** Behavior Decompose, Coordinator, Emit, Synthesize, Scan Cache

### Requirements Derive (COMP-87)

**Files:**
- `src/architecture_model/pipeline/requirements_derive.py`
**Downstream dependents (must re-test):** Behavior Decompose, Coordinator, Emit, Synthesize, Scan Cache

### Specify (COMP-88)

**Files:**
- `src/architecture_model/pipeline/specify.py`
- `src/architecture_model/pipeline/specify_types.py`
**Downstream dependents (must re-test):** Scan Cache, From Artifacts, Emit, Behavior Decompose, Coordinator, Synthesize

### Synthesize (COMP-90)

**Files:**
- `src/architecture_model/pipeline/synthesize.py`
- `src/architecture_model/pipeline/synthesize_types.py`
**Downstream dependents (must re-test):** Behavior Decompose, Coordinator, Emit, Scan Cache

### Validate (COMP-92)

**Files:**
- `src/architecture_model/pipeline/validate.py`
- `src/architecture_model/pipeline/validate_types.py`
**Downstream dependents (must re-test):** Synthesize, Enrichment Context, Scan Cache, From Artifacts, Behavior Decompose, Coordinator, Emit

### Discovery (COMP-94)

**Files:**
- `src/architecture_model/utils/discovery.py`
**Downstream dependents (must re-test):** Metrics, Kt Scanner, Loader, Blocks, Recursive, Generator, Merger

## Known Constraints

*No constraint allocations defined.*
