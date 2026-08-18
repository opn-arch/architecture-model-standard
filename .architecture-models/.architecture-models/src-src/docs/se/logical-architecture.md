---
document: Logical Architecture
system: Src (src)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:26Z
generator_version: 0.3.0
model_hash: 254bd5a18b33
edition: 3
---

# Logical Architecture: Src (src)

## Layer Structure

| Order | Layer | Technologies | Directories |
|-------|-------|-------------|-------------|
| 0 | data | — | — |
| 0 | web | — | — |

## Component Allocation

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Gate (COMP-2) | service | 1 files | — |
| Parser (COMP-3) | service | 2 files | — |
| Main (COMP-4) | service | 2 files | — |
| Loader (COMP-5) | service | 1 files | — |
| Schema (COMP-6) | service | 2 files | — |
| Cluster (COMP-7) | service | 1 files | — |
| Completeness (COMP-8) | service | 1 files | — |
| Compression (COMP-9) | service | 1 files | — |
| Confidence (COMP-10) | service | 1 files | — |
| Corrections (COMP-11) | service | 2 files | — |
| Coverage (COMP-12) | service | 1 files | — |
| Decomposer (COMP-13) | service | 1 files | — |
| Differ (COMP-14) | service | 1 files | — |
| Merger (COMP-15) | service | 1 files | — |
| Regen Readiness (COMP-16) | service | 2 files | — |
| Representativeness (COMP-17) | service | 1 files | — |
| Slicer (COMP-18) | service | 1 files | — |
| Source Block Assign (COMP-19) | service | 2 files | — |
| Validator (COMP-21) | service | 1 files | — |
| Visualize (COMP-22) | service | 2 files | — |
| Flatfiles (COMP-23) | service | 1 files | — |
| Reference (COMP-24) | service | 1 files | — |
| Constraint Detector (COMP-25) | service | 1 files | — |
| From Artifacts (COMP-26) | service | 3 files | — |
| Route Detector (COMP-28) | service | 1 files | — |
| Table Parser (COMP-29) | service | 1 files | — |
| Behavior (COMP-30) | service | 3 files | — |
| Blocks (COMP-31) | service | 1 files | — |
| Body Hints (COMP-32) | service | 1 files | — |
| Call Graph (COMP-33) | service | 1 files | — |
| Chains (COMP-34) | service | 1 files | — |
| Display (COMP-35) | service | 1 files | — |
| Generator (COMP-36) | service | 1 files | — |
| Grouping (COMP-37) | service | 1 files | — |
| Interfaces (COMP-38) | service | 1 files | — |
| Kt Scanner (COMP-39) | service | 2 files | — |
| Metrics (COMP-40) | service | 1 files | — |
| Multi Scanner (COMP-41) | service | 1 files | — |
| Protocol (COMP-42) | service | 2 files | — |
| Recursive (COMP-43) | service | 1 files | — |
| Scan Cache (COMP-44) | service | 2 files | — |
| Slicers (COMP-46) | service | 1 files | — |
| Ts Scanner (COMP-47) | service | 1 files | — |
| Monitoring (COMP-48) | service | 2 files | — |
| Auto Enrich (COMP-50) | service | 2 files | — |
| Behavior Decompose (COMP-51) | service | 3 files | — |
| Capability Inference (COMP-53) | service | 1 files | — |
| Compaction (COMP-54) | service | 1 files | — |
| Deep Decompose (COMP-56) | service | 1 files | — |
| Enrichment Context (COMP-58) | service | 2 files | — |
| Naming Context (COMP-59) | service | 1 files | — |
| Pipeline (COMP-60) | service | 1 files | — |
| Trigger Detection (COMP-61) | service | 1 files | — |
| Use Case Inference (COMP-62) | service | 1 files | — |
| Patterns (COMP-63) | service | 1 files | — |
| Store (COMP-64) | service | 1 files | — |
| Allocate (COMP-65) | service | 2 files | — |
| Allocate Types (COMP-66) | service | 2 files | — |
| Contract (COMP-70) | service | 2 files | — |
| Coordinator (COMP-72) | service | 1 files | — |
| Emit (COMP-74) | service | 2 files | — |
| Global Learning (COMP-76) | service | 2 files | — |
| Infer (COMP-77) | service | 2 files | — |
| Lessons (COMP-80) | service | 1 files | — |
| Observe (COMP-81) | service | 2 files | — |
| Relate (COMP-84) | service | 2 files | — |
| Report (COMP-86) | service | 1 files | — |
| Requirements Derive (COMP-87) | service | 1 files | — |
| Specify (COMP-88) | service | 2 files | — |
| Synthesize (COMP-90) | service | 2 files | — |
| Validate (COMP-92) | service | 2 files | — |
| Discovery (COMP-94) | service | 1 files | — |

## Inter-Component Interfaces

| Interface | Type | Protocol | Provider | Consumer |
|-----------|------|----------|----------|----------|
| main CLI | internal | — | — | — |

## Dependency Graph

```mermaid
graph TD
    COMP-59["Naming Context"]
    COMP-51["Behavior Decompose"]
    COMP-59 --> COMP-51
    COMP-60["Pipeline"]
    COMP-22["Visualize"]
    COMP-60 --> COMP-22
    COMP-37["Grouping"]
    COMP-4["Main"]
    COMP-37 --> COMP-4
    COMP-44["Scan Cache"]
    COMP-32["Body Hints"]
    COMP-44 --> COMP-32
    COMP-59 --> COMP-60
    COMP-8["Completeness"]
    COMP-22 --> COMP-8
    COMP-16["Regen Readiness"]
    COMP-18["Slicer"]
    COMP-16 --> COMP-18
    COMP-15["Merger"]
    COMP-22 --> COMP-15
    COMP-26["From Artifacts"]
    COMP-26 --> COMP-22
    COMP-30["Behavior"]
    COMP-41["Multi Scanner"]
    COMP-30 --> COMP-41
    COMP-10["Confidence"]
    COMP-22 --> COMP-10
    COMP-41 --> COMP-32
    COMP-74["Emit"]
    COMP-11["Corrections"]
    COMP-74 --> COMP-11
    COMP-60 --> COMP-44
    COMP-74 --> COMP-26
    COMP-46["Slicers"]
    COMP-39["Kt Scanner"]
    COMP-46 --> COMP-39
    COMP-33["Call Graph"]
    COMP-33 --> COMP-4
    COMP-13["Decomposer"]
    COMP-22 --> COMP-13
    COMP-65["Allocate"]
    COMP-77["Infer"]
    COMP-65 --> COMP-77
    COMP-76["Global Learning"]
    COMP-44 --> COMP-76
    COMP-39 --> COMP-33
    COMP-81["Observe"]
    COMP-44 --> COMP-81
    COMP-10 --> COMP-18
    COMP-44 --> COMP-16
    COMP-40["Metrics"]
    COMP-94["Discovery"]
    COMP-40 --> COMP-94
    COMP-2["Gate"]
    COMP-2 --> COMP-18
    COMP-25["Constraint Detector"]
    COMP-25 --> COMP-4
    COMP-86["Report"]
    COMP-51 --> COMP-86
    COMP-3["Parser"]
    COMP-60 --> COMP-3
    COMP-87["Requirements Derive"]
    COMP-51 --> COMP-87
    COMP-66["Allocate Types"]
    COMP-3 --> COMP-66
    COMP-31["Blocks"]
    COMP-46 --> COMP-31
    COMP-30 --> COMP-40
    COMP-58["Enrichment Context"]
    COMP-58 --> COMP-30
    COMP-21["Validator"]
    COMP-60 --> COMP-21
    COMP-90["Synthesize"]
    COMP-63["Patterns"]
    COMP-90 --> COMP-63
    COMP-47["Ts Scanner"]
    COMP-46 --> COMP-47
    COMP-53["Capability Inference"]
    COMP-14["Differ"]
    COMP-53 --> COMP-14
    COMP-38["Interfaces"]
    COMP-38 --> COMP-30
    COMP-38 --> COMP-39
    COMP-26 --> COMP-21
    COMP-48["Monitoring"]
    COMP-30 --> COMP-48
    COMP-88["Specify"]
    COMP-44 --> COMP-88
    COMP-50["Auto Enrich"]
    COMP-50 --> COMP-11
    COMP-46 --> COMP-38
    COMP-9["Compression"]
    COMP-30 --> COMP-9
    COMP-54["Compaction"]
    COMP-54 --> COMP-48
    COMP-17["Representativeness"]
    COMP-51 --> COMP-17
    COMP-62["Use Case Inference"]
    COMP-62 --> COMP-4
    COMP-12["Coverage"]
    COMP-3 --> COMP-12
    COMP-7["Cluster"]
    COMP-3 --> COMP-7
    COMP-90 --> COMP-60
    COMP-36["Generator"]
    COMP-36 --> COMP-39
    COMP-51 --> COMP-77
    COMP-31 --> COMP-4
    COMP-37 --> COMP-63
    COMP-6["Schema"]
    COMP-51 --> COMP-6
    COMP-19["Source Block Assign"]
    COMP-19 --> COMP-4
    COMP-42["Protocol"]
    COMP-40 --> COMP-42
    COMP-61["Trigger Detection"]
    COMP-34["Chains"]
    COMP-61 --> COMP-34
    COMP-51 --> COMP-58
    COMP-37 --> COMP-12
    COMP-36 --> COMP-31
    COMP-51 --> COMP-8
    COMP-56["Deep Decompose"]
    COMP-56 --> COMP-11
    COMP-36 --> COMP-47
    COMP-37 --> COMP-32
    COMP-43["Recursive"]
    COMP-41 --> COMP-43
    COMP-39 --> COMP-94
    COMP-44 --> COMP-39
    COMP-33 --> COMP-63
    COMP-26 --> COMP-42
    COMP-3 --> COMP-16
    COMP-36 --> COMP-38
    COMP-53 --> COMP-18
    COMP-74 --> COMP-42
    COMP-72["Coordinator"]
    COMP-72 --> COMP-87
    COMP-35["Display"]
    COMP-30 --> COMP-35
    COMP-30 --> COMP-15
    COMP-18 --> COMP-4
    COMP-37 --> COMP-19
    COMP-41 --> COMP-30
    COMP-41 --> COMP-39
    COMP-30 --> COMP-10
    COMP-51 --> COMP-13
    COMP-72 --> COMP-86
    COMP-32 --> COMP-9
    COMP-25 --> COMP-63
    COMP-81 --> COMP-42
    COMP-92["Validate"]
    COMP-92 --> COMP-77
    COMP-74 --> COMP-51
    COMP-43 --> COMP-66
    COMP-17 --> COMP-4
    COMP-60 --> COMP-62
    COMP-32 --> COMP-17
    COMP-2 --> COMP-3
    COMP-16 --> COMP-11
    COMP-39 --> COMP-42
    COMP-62 --> COMP-63
    COMP-25 --> COMP-19
    COMP-31 --> COMP-63
    COMP-43 --> COMP-32
    COMP-70["Contract"]
    COMP-74 --> COMP-70
    COMP-80["Lessons"]
    COMP-90 --> COMP-80
    COMP-60 --> COMP-66
    COMP-32 --> COMP-8
    COMP-90 --> COMP-92
    COMP-32 --> COMP-15
    COMP-26 --> COMP-66
    COMP-41 --> COMP-48
    COMP-32 --> COMP-10
    COMP-84["Relate"]
    COMP-51 --> COMP-84
    COMP-62 --> COMP-19
    COMP-10 --> COMP-4
    COMP-37 --> COMP-43
    COMP-32 --> COMP-13
    COMP-60 --> COMP-12
    COMP-56 --> COMP-42
    COMP-81 --> COMP-66
    COMP-50 --> COMP-34
    COMP-2 --> COMP-4
    COMP-60 --> COMP-32
    COMP-26 --> COMP-12
    COMP-18 --> COMP-63
    COMP-36 --> COMP-46
    COMP-26 --> COMP-7
    COMP-60 --> COMP-53
    COMP-37 --> COMP-30
    COMP-13 --> COMP-9
    COMP-5["Loader"]
    COMP-51 --> COMP-5
    COMP-33 --> COMP-43
    COMP-53 --> COMP-3
    COMP-37 --> COMP-41
    COMP-51 --> COMP-22
    COMP-60 --> COMP-50
    COMP-3 --> COMP-14
    COMP-17 --> COMP-63
    COMP-13 --> COMP-17
    COMP-61 --> COMP-40
    COMP-60 --> COMP-16
    COMP-90 --> COMP-48
    COMP-92 --> COMP-84
    COMP-61 --> COMP-36
    COMP-41 --> COMP-35
    COMP-74 --> COMP-76
    COMP-51 --> COMP-44
    COMP-12 --> COMP-66
    COMP-26 --> COMP-16
    COMP-30 --> COMP-11
    COMP-33 --> COMP-41
    COMP-61 --> COMP-9
    COMP-60 --> COMP-54
    COMP-51 --> COMP-74
    COMP-88 --> COMP-66
    COMP-54 --> COMP-11
    COMP-17 --> COMP-19
    COMP-72 --> COMP-84
    COMP-13 --> COMP-8
    COMP-13 --> COMP-15
    COMP-61 --> COMP-17
    COMP-13 --> COMP-10
    COMP-26 --> COMP-88
    COMP-51 --> COMP-3
    COMP-74 --> COMP-88
    COMP-31 --> COMP-43
    COMP-37 --> COMP-48
    COMP-43 --> COMP-30
    COMP-43 --> COMP-39
    COMP-53 --> COMP-4
    COMP-51 --> COMP-21
    COMP-10 --> COMP-63
    COMP-33 --> COMP-40
    COMP-61 --> COMP-47
    COMP-2 --> COMP-63
    COMP-46 --> COMP-4
    COMP-31 --> COMP-30
    COMP-3 --> COMP-18
    COMP-56 --> COMP-7
    COMP-33 --> COMP-36
    COMP-33 --> COMP-48
    COMP-51 --> COMP-90
    COMP-61 --> COMP-8
    COMP-31 --> COMP-41
    COMP-5 --> COMP-94
    COMP-32 --> COMP-22
    COMP-61 --> COMP-10
    COMP-61 --> COMP-15
    COMP-2 --> COMP-32
    COMP-74 --> COMP-86
    COMP-74 --> COMP-87
    COMP-77 --> COMP-42
    COMP-60 --> COMP-39
    COMP-58 --> COMP-4
    COMP-10 --> COMP-19
    COMP-61 --> COMP-37
    COMP-25 --> COMP-48
    COMP-61 --> COMP-13
    COMP-2 --> COMP-19
    COMP-72 --> COMP-44
    COMP-38 --> COMP-4
    COMP-72 --> COMP-74
    COMP-40 --> COMP-31
    COMP-40 --> COMP-47
    COMP-22 --> COMP-7
    COMP-37 --> COMP-35
    COMP-26 --> COMP-77
    COMP-17 --> COMP-43
    COMP-74 --> COMP-77
    COMP-50 --> COMP-40
    COMP-40 --> COMP-38
    COMP-36 --> COMP-4
    COMP-59 --> COMP-56
    COMP-62 --> COMP-48
    COMP-21 --> COMP-66
    COMP-30 --> COMP-42
    COMP-60 --> COMP-58
    COMP-50 --> COMP-36
    COMP-62 --> COMP-9
    COMP-65 --> COMP-66
    COMP-31 --> COMP-48
    COMP-60 --> COMP-14
    COMP-17 --> COMP-30
    COMP-14 --> COMP-4
    COMP-40 --> COMP-37
    COMP-33 --> COMP-35
    COMP-50 --> COMP-9
    COMP-74 --> COMP-58
    COMP-53 --> COMP-63
    COMP-26 --> COMP-14
    COMP-46 --> COMP-66
    COMP-19 --> COMP-48
    COMP-17 --> COMP-41
    COMP-62 --> COMP-17
    COMP-19 --> COMP-9
    COMP-44 --> COMP-4
    COMP-72 --> COMP-90
    COMP-50 --> COMP-17
    COMP-46 --> COMP-63
    COMP-77 --> COMP-66
    COMP-30 --> COMP-34
    COMP-39 --> COMP-31
    COMP-13 --> COMP-22
    COMP-19 --> COMP-17
    COMP-61 --> COMP-46
    COMP-39 --> COMP-47
    COMP-18 --> COMP-48
    COMP-46 --> COMP-32
    COMP-50 --> COMP-31
    COMP-53 --> COMP-19
    COMP-50 --> COMP-47
    COMP-2 --> COMP-43
    COMP-51 --> COMP-66
    COMP-58 --> COMP-63
    COMP-39 --> COMP-38
    COMP-62 --> COMP-15
    COMP-62 --> COMP-10
    COMP-61 --> COMP-33
    COMP-38 --> COMP-63
    COMP-50 --> COMP-8
    COMP-50 --> COMP-15
    COMP-31 --> COMP-35
    COMP-65 --> COMP-81
    COMP-2 --> COMP-30
    COMP-36 --> COMP-66
    COMP-17 --> COMP-48
    COMP-60 --> COMP-18
    COMP-39 --> COMP-37
    COMP-50 --> COMP-37
    COMP-51 --> COMP-12
    COMP-19 --> COMP-8
    COMP-58 --> COMP-60
    COMP-19 --> COMP-15
    COMP-26 --> COMP-18
    COMP-61 --> COMP-22
    COMP-2 --> COMP-41
    COMP-19 --> COMP-10
    COMP-36 --> COMP-63
    COMP-50 --> COMP-13
    COMP-90 --> COMP-26
    COMP-90 --> COMP-11
    COMP-40 --> COMP-46
    COMP-56 --> COMP-31
    COMP-84 --> COMP-66
    COMP-56 --> COMP-47
    COMP-30 --> COMP-7
    COMP-14 --> COMP-63
    COMP-36 --> COMP-32
    COMP-61 --> COMP-44
    COMP-56 --> COMP-38
    COMP-26 --> COMP-84
    COMP-16 --> COMP-9
    COMP-40 --> COMP-33
    COMP-74 --> COMP-84
    COMP-3 --> COMP-4
    COMP-56 --> COMP-14
    COMP-92 --> COMP-66
    COMP-51 --> COMP-76
    COMP-44 --> COMP-63
    COMP-37 --> COMP-11
    COMP-56 --> COMP-37
    COMP-44 --> COMP-65
    COMP-51 --> COMP-81
    COMP-51 --> COMP-16
    COMP-16 --> COMP-17
    COMP-56 --> COMP-13
    COMP-92 --> COMP-65
    COMP-10 --> COMP-48
    COMP-10 --> COMP-9
    COMP-2 --> COMP-48
    COMP-17 --> COMP-35
    COMP-61 --> COMP-21
    COMP-17 --> COMP-10
    COMP-26 --> COMP-5
    COMP-44 --> COMP-60
    COMP-46 --> COMP-43
    COMP-22 --> COMP-14
    COMP-51 --> COMP-88
    COMP-40 --> COMP-44
    COMP-39 --> COMP-46
    COMP-50 --> COMP-46
    COMP-59 --> COMP-62
    COMP-84 --> COMP-81
    COMP-16 --> COMP-8
    COMP-46 --> COMP-30
    COMP-16 --> COMP-15
    COMP-32 --> COMP-7
    COMP-16 --> COMP-10
    COMP-25 --> COMP-11
    COMP-74 --> COMP-44
    COMP-41 --> COMP-34
    COMP-15 --> COMP-66
    COMP-46 --> COMP-41
    COMP-50 --> COMP-33
    COMP-16 --> COMP-13
    COMP-38 --> COMP-43
    COMP-90 --> COMP-42
    COMP-61 --> COMP-42
    COMP-10 --> COMP-15
    COMP-58 --> COMP-92
    COMP-26 --> COMP-3
    COMP-62 --> COMP-11
    COMP-72 --> COMP-76
    COMP-50 --> COMP-22
    COMP-30 --> COMP-36
    COMP-2 --> COMP-35
    COMP-36 --> COMP-43
    COMP-3 --> COMP-63
    COMP-56 --> COMP-46
    COMP-44 --> COMP-72
    COMP-72 --> COMP-16
    COMP-43 --> COMP-4
    COMP-32 --> COMP-16
    COMP-90 --> COMP-51
    COMP-38 --> COMP-41
    COMP-53 --> COMP-48
    COMP-39 --> COMP-44
    COMP-54 --> COMP-9
    COMP-19 --> COMP-11
    COMP-36 --> COMP-30
    COMP-50 --> COMP-44
    COMP-56 --> COMP-33
    COMP-59 --> COMP-53
    COMP-30 --> COMP-17
    COMP-74 --> COMP-90
    COMP-72 --> COMP-88
    COMP-46 --> COMP-48
    COMP-36 --> COMP-41
    COMP-44 --> COMP-43
    COMP-3 --> COMP-19
    COMP-54 --> COMP-17
    COMP-56 --> COMP-22
    COMP-60 --> COMP-4
    COMP-30 --> COMP-31
    COMP-50 --> COMP-3
    COMP-90 --> COMP-70
    COMP-51 --> COMP-14
    COMP-30 --> COMP-47
    COMP-59 --> COMP-50
    COMP-44 --> COMP-80
    COMP-33 --> COMP-42
    COMP-50 --> COMP-21
    COMP-26 --> COMP-4
    COMP-31 --> COMP-94
    COMP-38 --> COMP-40
    COMP-44 --> COMP-30
    COMP-13 --> COMP-7
    COMP-58 --> COMP-48
    COMP-44 --> COMP-92
    COMP-84 --> COMP-77
    COMP-30 --> COMP-38
    COMP-5 --> COMP-6
    COMP-30 --> COMP-8
    COMP-56 --> COMP-44
    COMP-38 --> COMP-48
    COMP-44 --> COMP-41
    COMP-61 --> COMP-66
    COMP-37 --> COMP-34
    COMP-54 --> COMP-8
    COMP-59 --> COMP-54
    COMP-17 --> COMP-11
    COMP-54 --> COMP-15
    COMP-30 --> COMP-37
    COMP-54 --> COMP-10
    COMP-30 --> COMP-13
    COMP-36 --> COMP-48
    COMP-56 --> COMP-3
    COMP-54 --> COMP-13
    COMP-46 --> COMP-35
    COMP-61 --> COMP-12
    COMP-16 --> COMP-22
    COMP-56 --> COMP-21
    COMP-61 --> COMP-7
    COMP-33 --> COMP-34
    COMP-43 --> COMP-63
    COMP-72 --> COMP-77
    COMP-14 --> COMP-48
    COMP-39 --> COMP-4
    COMP-50 --> COMP-42
    COMP-40 --> COMP-66
    COMP-51 --> COMP-18
    COMP-44 --> COMP-48
    COMP-72 --> COMP-58
    COMP-41 --> COMP-40
    COMP-12 --> COMP-4
    COMP-90 --> COMP-76
    COMP-40 --> COMP-63
    COMP-22 --> COMP-3
    COMP-38 --> COMP-35
    COMP-10 --> COMP-11
    COMP-32 --> COMP-14
    COMP-41 --> COMP-36
    COMP-22 --> COMP-21
    COMP-74 --> COMP-66
    COMP-60 --> COMP-63
    COMP-2 --> COMP-11
    COMP-61 --> COMP-16
    COMP-26 --> COMP-63
    COMP-40 --> COMP-32
    COMP-36 --> COMP-35
    COMP-26 --> COMP-65
    COMP-74 --> COMP-63
    COMP-74 --> COMP-65
    COMP-31 --> COMP-34
    COMP-90 --> COMP-88
    COMP-30 --> COMP-46
    COMP-60 --> COMP-19
    COMP-30 --> COMP-33
    COMP-59 --> COMP-58
    COMP-39 --> COMP-66
    COMP-26 --> COMP-19
    COMP-44 --> COMP-35
    COMP-50 --> COMP-66
    COMP-90 --> COMP-87
    COMP-90 --> COMP-86
    COMP-39 --> COMP-63
    COMP-30 --> COMP-22
    COMP-26 --> COMP-81
    COMP-3 --> COMP-48
    COMP-62 --> COMP-7
    COMP-74 --> COMP-81
    COMP-54 --> COMP-22
    COMP-60 --> COMP-61
    COMP-74 --> COMP-16
    COMP-16 --> COMP-42
    COMP-50 --> COMP-12
    COMP-3 --> COMP-9
    COMP-4 --> COMP-22
    COMP-50 --> COMP-7
    COMP-39 --> COMP-32
    COMP-12 --> COMP-63
    COMP-50 --> COMP-32
    COMP-53 --> COMP-11
    COMP-30 --> COMP-44
    COMP-61 --> COMP-39
    COMP-37 --> COMP-40
    COMP-88 --> COMP-65
    COMP-13 --> COMP-14
    COMP-17 --> COMP-34
    COMP-19 --> COMP-7
    COMP-21 --> COMP-4
    COMP-56 --> COMP-66
    COMP-37 --> COMP-36
    COMP-70 --> COMP-42
    COMP-90 --> COMP-77
    COMP-74 --> COMP-72
    COMP-80 --> COMP-42
    COMP-37 --> COMP-9
    COMP-56 --> COMP-63
    COMP-61 --> COMP-31
    COMP-29["Table Parser"]
    COMP-26 --> COMP-29
    COMP-40 --> COMP-43
    COMP-30 --> COMP-3
    COMP-43 --> COMP-41
    COMP-90 --> COMP-58
    COMP-30 --> COMP-21
    COMP-56 --> COMP-12
    COMP-60 --> COMP-43
    COMP-50 --> COMP-16
    COMP-37 --> COMP-17
    COMP-61 --> COMP-38
    COMP-54 --> COMP-21
    COMP-56 --> COMP-32
    COMP-40 --> COMP-30
    COMP-40 --> COMP-39
    COMP-61 --> COMP-14
    COMP-22 --> COMP-66
    COMP-3 --> COMP-15
    COMP-3 --> COMP-10
    COMP-60 --> COMP-30
    COMP-40 --> COMP-41
    COMP-56 --> COMP-19
    COMP-88 --> COMP-81
    COMP-58 --> COMP-59
    COMP-74 --> COMP-80
    COMP-37 --> COMP-47
    COMP-25 --> COMP-9
    COMP-60 --> COMP-41
    COMP-26 --> COMP-92
    COMP-51 --> COMP-4
    COMP-43 --> COMP-40
    COMP-2 --> COMP-34
    COMP-22 --> COMP-12
    COMP-26 --> COMP-25
    COMP-37 --> COMP-8
    COMP-37 --> COMP-15
    COMP-37 --> COMP-10
    COMP-56 --> COMP-16
    COMP-43 --> COMP-48
    COMP-33 --> COMP-31
    COMP-25 --> COMP-17
    COMP-31 --> COMP-40
    COMP-33 --> COMP-47
    COMP-41 --> COMP-33
    COMP-16 --> COMP-7
    COMP-39 --> COMP-43
    COMP-32 --> COMP-3
    COMP-31 --> COMP-36
    COMP-22 --> COMP-19
    COMP-37 --> COMP-13
    COMP-33 --> COMP-38
    COMP-32 --> COMP-21
    COMP-21 --> COMP-63
    COMP-44 --> COMP-11
    COMP-44 --> COMP-26
    COMP-39 --> COMP-30
    COMP-61 --> COMP-18
    COMP-50 --> COMP-39
    COMP-33 --> COMP-37
    COMP-22 --> COMP-16
    COMP-60 --> COMP-48
    COMP-10 --> COMP-7
    COMP-25 --> COMP-8
    COMP-25 --> COMP-15
    COMP-39 --> COMP-41
    COMP-25 --> COMP-10
    COMP-60 --> COMP-9
    COMP-26 --> COMP-48
    COMP-90 --> COMP-84
    COMP-41 --> COMP-44
    COMP-25 --> COMP-13
    COMP-56 --> COMP-43
    COMP-58 --> COMP-42
    COMP-43 --> COMP-35
    COMP-31 --> COMP-47
    COMP-72 --> COMP-4
    COMP-62 --> COMP-8
    COMP-32 --> COMP-4
    COMP-38 --> COMP-42
    COMP-17 --> COMP-40
    COMP-50 --> COMP-38
    COMP-56 --> COMP-30
    COMP-56 --> COMP-39
    COMP-50 --> COMP-14
    COMP-51 --> COMP-63
    COMP-17 --> COMP-36
    COMP-46 --> COMP-34
    COMP-30 --> COMP-66
    COMP-58 --> COMP-51
    COMP-51 --> COMP-65
    COMP-62 --> COMP-13
    COMP-56 --> COMP-41
    COMP-37 --> COMP-46
    COMP-17 --> COMP-9
    COMP-31 --> COMP-37
    COMP-54 --> COMP-66
    COMP-19 --> COMP-14
    COMP-39 --> COMP-48
    COMP-60 --> COMP-35
    COMP-60 --> COMP-15
    COMP-13 --> COMP-3
    COMP-3 --> COMP-11
    COMP-60 --> COMP-10
    COMP-37 --> COMP-33
    COMP-30 --> COMP-12
    COMP-15 --> COMP-4
    COMP-58 --> COMP-62
    COMP-13 --> COMP-21
    COMP-19 --> COMP-13
    COMP-51 --> COMP-60
    COMP-77 --> COMP-81
    COMP-90 --> COMP-44
    COMP-26 --> COMP-10
    COMP-51 --> COMP-19
    COMP-30 --> COMP-32
    COMP-33 --> COMP-46
    COMP-12 --> COMP-48
    COMP-38 --> COMP-34
    COMP-54 --> COMP-12
    COMP-54 --> COMP-7
    COMP-90 --> COMP-74
    COMP-84 --> COMP-65
    COMP-59 --> COMP-4
    COMP-44 --> COMP-42
    COMP-37 --> COMP-22
    COMP-17 --> COMP-31
    COMP-17 --> COMP-47
    COMP-2 --> COMP-40
    COMP-36 --> COMP-34
    COMP-41 --> COMP-42
    COMP-61 --> COMP-3
    COMP-50 --> COMP-18
    COMP-2 --> COMP-36
    COMP-17 --> COMP-8
    COMP-17 --> COMP-15
    COMP-37 --> COMP-44
    COMP-32 --> COMP-66
    COMP-44 --> COMP-51
    COMP-76 --> COMP-42
    COMP-30 --> COMP-16
    COMP-2 --> COMP-9
    COMP-17 --> COMP-37
    COMP-72 --> COMP-63
    COMP-13 --> COMP-4
    COMP-32 --> COMP-63
    COMP-54 --> COMP-16
    COMP-72 --> COMP-65
    COMP-17 --> COMP-13
    COMP-51 --> COMP-72
    COMP-10 --> COMP-17
    COMP-25 --> COMP-22
    COMP-44 --> COMP-34
    COMP-31 --> COMP-46
    COMP-2 --> COMP-17
    COMP-32 --> COMP-12
    COMP-16 --> COMP-14
    COMP-33 --> COMP-44
    COMP-58 --> COMP-53
    COMP-37 --> COMP-21
    COMP-44 --> COMP-70
    COMP-56 --> COMP-18
    COMP-31 --> COMP-33
    COMP-2 --> COMP-47
    COMP-32 --> COMP-19
    COMP-15 --> COMP-63
    COMP-61 --> COMP-4
    COMP-62 --> COMP-22
    COMP-10 --> COMP-8
    COMP-51 --> COMP-80
    COMP-2 --> COMP-8
    COMP-2 --> COMP-15
    COMP-2 --> COMP-10
    COMP-59 --> COMP-63
    COMP-72 --> COMP-81
    COMP-51 --> COMP-92
    COMP-21 --> COMP-48
    COMP-58 --> COMP-54
    COMP-10 --> COMP-13
    COMP-2 --> COMP-37
    COMP-19 --> COMP-22
    COMP-22 --> COMP-18
    COMP-25 --> COMP-21
    COMP-2 --> COMP-13
    COMP-46 --> COMP-40
    COMP-30 --> COMP-39
    COMP-53 --> COMP-9
    COMP-31 --> COMP-44
    COMP-37 --> COMP-42
    COMP-46 --> COMP-36
    COMP-60 --> COMP-11
    COMP-13 --> COMP-66
    COMP-17 --> COMP-46
    COMP-40 --> COMP-4
    COMP-26 --> COMP-11
    COMP-43 --> COMP-94
    COMP-62 --> COMP-3
    COMP-53 --> COMP-17
    COMP-13 --> COMP-63
    COMP-62 --> COMP-21
    COMP-17 --> COMP-33
    COMP-60 --> COMP-59
    COMP-13 --> COMP-12
    COMP-74 --> COMP-4
    COMP-19 --> COMP-3
    COMP-38 --> COMP-36
    COMP-90 --> COMP-66
    COMP-30 --> COMP-14
    COMP-19 --> COMP-21
    COMP-17 --> COMP-22
    COMP-51 --> COMP-48
    COMP-59 --> COMP-61
    COMP-36 --> COMP-40
    COMP-7 --> COMP-4
    COMP-54 --> COMP-14
    COMP-51 --> COMP-9
    COMP-53 --> COMP-8
    COMP-13 --> COMP-19
    COMP-53 --> COMP-15
    COMP-72 --> COMP-80
    COMP-53 --> COMP-10
    COMP-90 --> COMP-65
    COMP-61 --> COMP-63
    COMP-72 --> COMP-92
    COMP-17 --> COMP-44
    COMP-58 --> COMP-77
    COMP-43 --> COMP-42
    COMP-2 --> COMP-46
    COMP-53 --> COMP-13
    COMP-13 --> COMP-16
    COMP-61 --> COMP-32
    COMP-37 --> COMP-66
    COMP-50 --> COMP-4
    COMP-46 --> COMP-37
    COMP-44 --> COMP-40
    COMP-31 --> COMP-42
    COMP-38 --> COMP-31
    COMP-2 --> COMP-33
    COMP-38 --> COMP-47
    COMP-17 --> COMP-3
    COMP-44 --> COMP-36
    COMP-61 --> COMP-19
    COMP-44 --> COMP-86
    COMP-44 --> COMP-87
    COMP-17 --> COMP-21
    COMP-10 --> COMP-22
    COMP-33 --> COMP-66
    COMP-37 --> COMP-7
    COMP-2 --> COMP-22
    COMP-30 --> COMP-18
    COMP-51 --> COMP-15
    COMP-60 --> COMP-42
    COMP-51 --> COMP-10
    COMP-90 --> COMP-81
    COMP-90 --> COMP-16
    COMP-59 --> COMP-30
    COMP-43 --> COMP-34
    COMP-38 --> COMP-37
    COMP-54 --> COMP-18
    COMP-16 --> COMP-3
    COMP-25 --> COMP-66
    COMP-56 --> COMP-4
    COMP-72 --> COMP-48
    COMP-16 --> COMP-21
    COMP-32 --> COMP-48
    COMP-2 --> COMP-44
    COMP-60 --> COMP-51
    COMP-44 --> COMP-77
    COMP-33 --> COMP-32
    COMP-36 --> COMP-37
    COMP-90 --> COMP-72
    COMP-44 --> COMP-31
    COMP-7 --> COMP-63
    COMP-40 --> COMP-34
    COMP-44 --> COMP-47
    COMP-22 --> COMP-11
    COMP-25 --> COMP-12
    COMP-37 --> COMP-16
    COMP-10 --> COMP-3
    COMP-25 --> COMP-7
    COMP-44 --> COMP-58
    COMP-62 --> COMP-66
    COMP-74 --> COMP-60
    COMP-41 --> COMP-31
    COMP-17 --> COMP-42
    COMP-10 --> COMP-21
    COMP-44 --> COMP-38
    COMP-60 --> COMP-34
    COMP-41 --> COMP-47
    COMP-31 --> COMP-66
    COMP-2 --> COMP-21
    COMP-15 --> COMP-48
    COMP-41 --> COMP-38
    COMP-44 --> COMP-37
    COMP-50 --> COMP-63
    COMP-19 --> COMP-66
    COMP-32 --> COMP-18
    COMP-61 --> COMP-43
    COMP-62 --> COMP-12
    COMP-26 --> COMP-70
    COMP-16 --> COMP-4
    COMP-46 --> COMP-33
    COMP-59 --> COMP-48
    COMP-41 --> COMP-37
    COMP-53 --> COMP-22
    COMP-58 --> COMP-84
    COMP-19 --> COMP-63
    COMP-88 --> COMP-42
    COMP-61 --> COMP-30
    COMP-25 --> COMP-16
    COMP-31 --> COMP-32
    COMP-65 --> COMP-11
    COMP-19 --> COMP-12
    COMP-38 --> COMP-46
    COMP-3 --> COMP-17
    COMP-18 --> COMP-66
    COMP-61 --> COMP-41
    COMP-50 --> COMP-19
    COMP-39 --> COMP-34
    COMP-60 --> COMP-7
    COMP-58 --> COMP-56
    COMP-38 --> COMP-33
    COMP-2 --> COMP-42
    COMP-77 --> COMP-11
    COMP-13 --> COMP-48
    COMP-62 --> COMP-16
    COMP-46 --> COMP-44
    COMP-37 --> COMP-39
    COMP-17 --> COMP-66
    COMP-54 --> COMP-3
    COMP-36 --> COMP-33
    COMP-53 --> COMP-21
    COMP-3 --> COMP-8
    COMP-19 --> COMP-16
    COMP-51 --> COMP-11
    COMP-44 --> COMP-84
    COMP-51 --> COMP-26
    COMP-33 --> COMP-30
    COMP-33 --> COMP-39
    COMP-37 --> COMP-31
    COMP-44 --> COMP-46
    COMP-17 --> COMP-12
    COMP-17 --> COMP-7
    COMP-16 --> COMP-66
    COMP-38 --> COMP-44
    COMP-56 --> COMP-34
    COMP-3 --> COMP-13
    COMP-61 --> COMP-48
    COMP-17 --> COMP-32
    COMP-28["Route Detector"]
    COMP-26 --> COMP-28
    COMP-74 --> COMP-92
    COMP-13 --> COMP-18
    COMP-37 --> COMP-38
    COMP-41 --> COMP-46
    COMP-44 --> COMP-33
    COMP-16 --> COMP-63
    COMP-37 --> COMP-14
    COMP-43 --> COMP-36
    COMP-36 --> COMP-44
    COMP-30 --> COMP-4
    COMP-70 --> COMP-66
    COMP-16 --> COMP-12
    COMP-10 --> COMP-66
    COMP-54 --> COMP-4
    COMP-50 --> COMP-43
    COMP-2 --> COMP-66
    COMP-70 --> COMP-65
    COMP-86 --> COMP-42
    COMP-65 --> COMP-42
    COMP-17 --> COMP-16
    COMP-40 --> COMP-36
    COMP-60 --> COMP-40
    COMP-40 --> COMP-48
    COMP-16 --> COMP-19
    COMP-50 --> COMP-30
    COMP-31 --> COMP-39
    COMP-60 --> COMP-36
    COMP-10 --> COMP-12
    COMP-36 --> COMP-94
    COMP-46 --> COMP-42
    COMP-25 --> COMP-14
    COMP-44 --> COMP-74
    COMP-2 --> COMP-12
    COMP-43 --> COMP-31
    COMP-2 --> COMP-7
    COMP-50 --> COMP-41
    COMP-61 --> COMP-35
    COMP-43 --> COMP-47
    COMP-43 --> COMP-6
    COMP-74 --> COMP-48
    COMP-72 --> COMP-11
    COMP-26 --> COMP-9
    COMP-32 --> COMP-11
    COMP-72 --> COMP-26
    COMP-43 --> COMP-38
    COMP-37 --> COMP-18
    COMP-60 --> COMP-17
    COMP-7 --> COMP-48
    COMP-62 --> COMP-14
    COMP-70 --> COMP-81
    COMP-26 --> COMP-17
    COMP-31 --> COMP-38
    COMP-43 --> COMP-37
    COMP-51 --> COMP-42
    COMP-10 --> COMP-16
    COMP-39 --> COMP-40
    COMP-60 --> COMP-31
    COMP-60 --> COMP-47
    COMP-2 --> COMP-16
    COMP-36 --> COMP-42
    COMP-39 --> COMP-36
    COMP-40 --> COMP-35
    COMP-44 --> COMP-90
    COMP-26 --> COMP-6
    COMP-30 --> COMP-63
    COMP-53 --> COMP-66
    COMP-3 --> COMP-22
    COMP-50 --> COMP-48
    COMP-60 --> COMP-8
    COMP-60 --> COMP-38
    COMP-17 --> COMP-39
    COMP-54 --> COMP-63
    COMP-25 --> COMP-18
    COMP-26 --> COMP-8
    COMP-26 --> COMP-15
    COMP-60 --> COMP-37
    COMP-84 --> COMP-42
    COMP-60 --> COMP-13
    COMP-53 --> COMP-12
    COMP-53 --> COMP-7
    COMP-26 --> COMP-13
    COMP-56 --> COMP-40
    COMP-30 --> COMP-19
    COMP-92 --> COMP-42
    COMP-51 --> COMP-70
    COMP-41 --> COMP-4
    COMP-62 --> COMP-18
    COMP-58 --> COMP-66
    COMP-56 --> COMP-36
    COMP-15 --> COMP-94
    COMP-54 --> COMP-19
    COMP-56 --> COMP-48
    COMP-17 --> COMP-38
    COMP-13 --> COMP-11
    COMP-38 --> COMP-66
    COMP-17 --> COMP-14
    COMP-56 --> COMP-9
    COMP-3 --> COMP-21
    COMP-58 --> COMP-65
    COMP-72 --> COMP-42
    COMP-39 --> COMP-35
    COMP-43 --> COMP-46
    COMP-19 --> COMP-18
    COMP-50 --> COMP-35
    COMP-50 --> COMP-10
    COMP-2 --> COMP-39
    COMP-53 --> COMP-16
    COMP-56 --> COMP-17
    COMP-43 --> COMP-33
    COMP-37 --> COMP-3
    COMP-51 --> COMP-7
    COMP-72 --> COMP-51
    COMP-38 --> COMP-32
    COMP-14 --> COMP-66
    COMP-61 --> COMP-11
    COMP-72 --> COMP-60
    COMP-22 --> COMP-9
    COMP-43 --> COMP-5
    COMP-2 --> COMP-31
    COMP-60 --> COMP-46
    COMP-16 --> COMP-48
    COMP-58 --> COMP-50
    COMP-90 --> COMP-4
    COMP-44 --> COMP-66
    COMP-56 --> COMP-8
    COMP-10 --> COMP-14
    COMP-22 --> COMP-17
    COMP-56 --> COMP-15
    COMP-2 --> COMP-38
    COMP-56 --> COMP-10
    COMP-56 --> COMP-35
    COMP-58 --> COMP-81
    COMP-2 --> COMP-14
    COMP-30 --> COMP-43
    COMP-60 --> COMP-33
    COMP-72 --> COMP-70
    COMP-17 --> COMP-18
    COMP-41 --> COMP-66
    COMP-43 --> COMP-44
    COMP-58 --> COMP-61
    COMP-25 --> COMP-3
    COMP-60 --> COMP-56
    COMP-41 --> COMP-63
```
