---
document: Functional Analysis
system: Src (src)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:26Z
generator_version: 0.3.0
model_hash: 254bd5a18b33
edition: 3
---

# Functional Analysis: Src (src)

## Capability Inventory

| ID | Capability | Priority | Status | Description |
|----|-----------|----------|--------|-------------|
| CAP-1 | Web Routes | medium | ACTIVE | — |
| CAP-2 | Gate | medium | ACTIVE | — |
| CAP-3 | Parser | medium | ACTIVE | — |
| CAP-4 | Main | medium | ACTIVE | — |
| CAP-5 | Loader | medium | ACTIVE | — |
| CAP-6 | Schema | medium | ACTIVE | — |
| CAP-7 | Cluster | medium | ACTIVE | — |
| CAP-8 | Completeness | medium | ACTIVE | — |
| CAP-9 | Compression | medium | ACTIVE | — |
| CAP-10 | Confidence | medium | ACTIVE | — |
| CAP-11 | Corrections | medium | ACTIVE | — |
| CAP-12 | Coverage | medium | ACTIVE | — |
| CAP-13 | Decomposer | medium | ACTIVE | — |
| CAP-14 | Differ | medium | ACTIVE | — |
| CAP-15 | Merger | medium | ACTIVE | — |
| CAP-16 | Regen Readiness | medium | ACTIVE | — |
| CAP-17 | Representativeness | medium | ACTIVE | — |
| CAP-18 | Slicer | medium | ACTIVE | — |
| CAP-19 | Source Block Assign | medium | ACTIVE | — |
| CAP-20 | Source Block Quality | medium | ACTIVE | — |
| CAP-21 | Validator | medium | ACTIVE | — |
| CAP-22 | Visualize | medium | ACTIVE | — |
| CAP-23 | Flatfiles | medium | ACTIVE | — |
| CAP-24 | Reference | medium | ACTIVE | — |
| CAP-25 | Constraint Detector | medium | ACTIVE | — |
| CAP-26 | From Artifacts | medium | ACTIVE | — |
| CAP-27 | From Code | medium | ACTIVE | — |
| CAP-28 | Route Detector | medium | ACTIVE | — |
| CAP-29 | Table Parser | medium | ACTIVE | — |
| CAP-30 | Behavior | medium | ACTIVE | — |
| CAP-31 | Blocks | medium | ACTIVE | — |
| CAP-32 | Body Hints | medium | ACTIVE | — |
| CAP-33 | Call Graph | medium | ACTIVE | — |
| CAP-34 | Chains | medium | ACTIVE | — |
| CAP-35 | Display | medium | ACTIVE | — |
| CAP-36 | Generator | medium | ACTIVE | — |
| CAP-37 | Grouping | medium | ACTIVE | — |
| CAP-38 | Interfaces | medium | ACTIVE | — |
| CAP-39 | Kt Scanner | medium | ACTIVE | — |
| CAP-40 | Metrics | medium | ACTIVE | — |
| CAP-41 | Multi Scanner | medium | ACTIVE | — |
| CAP-42 | Protocol | medium | ACTIVE | — |
| CAP-43 | Recursive | medium | ACTIVE | — |
| CAP-44 | Scan Cache | medium | ACTIVE | — |
| CAP-45 | Scanner | medium | ACTIVE | — |
| CAP-46 | Slicers | medium | ACTIVE | — |
| CAP-47 | Ts Scanner | medium | ACTIVE | — |
| CAP-48 | Monitoring | medium | ACTIVE | — |
| CAP-49 | Monitoring Checks | medium | ACTIVE | — |
| CAP-50 | Auto Enrich | medium | ACTIVE | — |
| CAP-51 | Behavior Decompose | medium | ACTIVE | — |
| CAP-52 | Behavior Flows | medium | ACTIVE | — |
| CAP-53 | Capability Inference | medium | ACTIVE | — |
| CAP-54 | Compaction | medium | ACTIVE | — |
| CAP-55 | Decompose | medium | ACTIVE | — |
| CAP-56 | Deep Decompose | medium | ACTIVE | — |
| CAP-57 | Enrich | medium | ACTIVE | — |
| CAP-58 | Enrichment Context | medium | ACTIVE | — |
| CAP-59 | Naming Context | medium | ACTIVE | — |
| CAP-60 | Pipeline | medium | ACTIVE | — |
| CAP-61 | Trigger Detection | medium | ACTIVE | — |
| CAP-62 | Use Case Inference | medium | ACTIVE | — |
| CAP-63 | Patterns | medium | ACTIVE | — |
| CAP-64 | Store | medium | ACTIVE | — |
| CAP-65 | Allocate | medium | ACTIVE | — |
| CAP-66 | Allocate Types | medium | ACTIVE | — |
| CAP-67 | Artifacts | medium | ACTIVE | — |
| CAP-68 | Cache | medium | ACTIVE | — |
| CAP-69 | Context Gen | medium | ACTIVE | — |
| CAP-70 | Contract | medium | ACTIVE | — |
| CAP-71 | Contract Types | medium | ACTIVE | — |
| CAP-72 | Coordinator | medium | ACTIVE | — |
| CAP-73 | Decompose Types | medium | ACTIVE | — |
| CAP-74 | Emit | medium | ACTIVE | — |
| CAP-75 | Emit Types | medium | ACTIVE | — |
| CAP-76 | Global Learning | medium | ACTIVE | — |
| CAP-77 | Infer | medium | ACTIVE | — |
| CAP-78 | Infer Types | medium | ACTIVE | — |
| CAP-79 | Learning | medium | ACTIVE | — |
| CAP-80 | Lessons | medium | ACTIVE | — |
| CAP-81 | Observe | medium | ACTIVE | — |
| CAP-82 | Observe Types | medium | ACTIVE | — |
| CAP-83 | Regen Score | medium | ACTIVE | — |
| CAP-84 | Relate | medium | ACTIVE | — |
| CAP-85 | Relate Types | medium | ACTIVE | — |
| CAP-86 | Report | medium | ACTIVE | — |
| CAP-87 | Requirements Derive | medium | ACTIVE | — |
| CAP-88 | Specify | medium | ACTIVE | — |
| CAP-89 | Specify Types | medium | ACTIVE | — |
| CAP-90 | Synthesize | medium | ACTIVE | — |
| CAP-91 | Synthesize Types | medium | ACTIVE | — |
| CAP-92 | Validate | medium | ACTIVE | — |
| CAP-93 | Validate Types | medium | ACTIVE | — |
| CAP-94 | Discovery | medium | ACTIVE | — |
| CAP-95 | CLI Main | medium | ACTIVE | — |

## Functional Decomposition

```mermaid
graph TD
    CAP-1["Web Routes"]
    CAP-2["Gate"]
    CAP-3["Parser"]
    CAP-4["Main"]
    CAP-5["Loader"]
    CAP-6["Schema"]
    CAP-7["Cluster"]
    CAP-8["Completeness"]
    CAP-9["Compression"]
    CAP-10["Confidence"]
    CAP-11["Corrections"]
    CAP-12["Coverage"]
    CAP-13["Decomposer"]
    CAP-14["Differ"]
    CAP-15["Merger"]
    CAP-16["Regen Readiness"]
    CAP-17["Representativeness"]
    CAP-18["Slicer"]
    CAP-19["Source Block Assign"]
    CAP-20["Source Block Quality"]
    CAP-21["Validator"]
    CAP-22["Visualize"]
    CAP-23["Flatfiles"]
    CAP-24["Reference"]
    CAP-25["Constraint Detector"]
    CAP-26["From Artifacts"]
    CAP-27["From Code"]
    CAP-28["Route Detector"]
    CAP-29["Table Parser"]
    CAP-30["Behavior"]
    CAP-31["Blocks"]
    CAP-32["Body Hints"]
    CAP-33["Call Graph"]
    CAP-34["Chains"]
    CAP-35["Display"]
    CAP-36["Generator"]
    CAP-37["Grouping"]
    CAP-38["Interfaces"]
    CAP-39["Kt Scanner"]
    CAP-40["Metrics"]
    CAP-41["Multi Scanner"]
    CAP-42["Protocol"]
    CAP-43["Recursive"]
    CAP-44["Scan Cache"]
    CAP-45["Scanner"]
    CAP-46["Slicers"]
    CAP-47["Ts Scanner"]
    CAP-48["Monitoring"]
    CAP-49["Monitoring Checks"]
    CAP-50["Auto Enrich"]
    CAP-51["Behavior Decompose"]
    CAP-52["Behavior Flows"]
    CAP-53["Capability Inference"]
    CAP-54["Compaction"]
    CAP-55["Decompose"]
    CAP-56["Deep Decompose"]
    CAP-57["Enrich"]
    CAP-58["Enrichment Context"]
    CAP-59["Naming Context"]
    CAP-60["Pipeline"]
    CAP-61["Trigger Detection"]
    CAP-62["Use Case Inference"]
    CAP-63["Patterns"]
    CAP-64["Store"]
    CAP-65["Allocate"]
    CAP-66["Allocate Types"]
    CAP-67["Artifacts"]
    CAP-68["Cache"]
    CAP-69["Context Gen"]
    CAP-70["Contract"]
    CAP-71["Contract Types"]
    CAP-72["Coordinator"]
    CAP-73["Decompose Types"]
    CAP-74["Emit"]
    CAP-75["Emit Types"]
    CAP-76["Global Learning"]
    CAP-77["Infer"]
    CAP-78["Infer Types"]
    CAP-79["Learning"]
    CAP-80["Lessons"]
    CAP-81["Observe"]
    CAP-82["Observe Types"]
    CAP-83["Regen Score"]
    CAP-84["Relate"]
    CAP-85["Relate Types"]
    CAP-86["Report"]
    CAP-87["Requirements Derive"]
    CAP-88["Specify"]
    CAP-89["Specify Types"]
    CAP-90["Synthesize"]
    CAP-91["Synthesize Types"]
    CAP-92["Validate"]
    CAP-93["Validate Types"]
    CAP-94["Discovery"]
    CAP-95["CLI Main"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Web Routes | *unrealized* | — |
| Gate | Gate (COMP-2) | service |
| Parser | Parser (COMP-3) | service |
| Main | Main (COMP-4) | service |
| Loader | Loader (COMP-5) | service |
| Schema | Schema (COMP-6) | service |
| Cluster | Cluster (COMP-7) | service |
| Completeness | Completeness (COMP-8) | service |
| Compression | Compression (COMP-9) | service |
| Confidence | Confidence (COMP-10) | service |
| Corrections | Corrections (COMP-11) | service |
| Coverage | Coverage (COMP-12) | service |
| Decomposer | Decomposer (COMP-13) | service |
| Differ | Differ (COMP-14) | service |
| Merger | Merger (COMP-15) | service |
| Regen Readiness | Regen Readiness (COMP-16) | service |
| Representativeness | Representativeness (COMP-17) | service |
| Slicer | Slicer (COMP-18) | service |
| Source Block Assign | Source Block Assign (COMP-19) | service |
| Source Block Quality | *unrealized* | — |
| Validator | Validator (COMP-21) | service |
| Visualize | Visualize (COMP-22) | service |
| Flatfiles | Flatfiles (COMP-23) | service |
| Reference | Reference (COMP-24) | service |
| Constraint Detector | Constraint Detector (COMP-25) | service |
| From Artifacts | From Artifacts (COMP-26) | service |
| From Code | *unrealized* | — |
| Route Detector | Route Detector (COMP-28) | service |
| Table Parser | Table Parser (COMP-29) | service |
| Behavior | Behavior (COMP-30) | service |
| Blocks | Blocks (COMP-31) | service |
| Body Hints | Body Hints (COMP-32) | service |
| Call Graph | Call Graph (COMP-33) | service |
| Chains | Chains (COMP-34) | service |
| Display | Display (COMP-35) | service |
| Generator | Generator (COMP-36) | service |
| Grouping | Grouping (COMP-37) | service |
| Interfaces | Interfaces (COMP-38) | service |
| Kt Scanner | Kt Scanner (COMP-39) | service |
| Metrics | Metrics (COMP-40) | service |
| Multi Scanner | Multi Scanner (COMP-41) | service |
| Protocol | Protocol (COMP-42) | service |
| Recursive | Recursive (COMP-43) | service |
| Scan Cache | Scan Cache (COMP-44) | service |
| Scanner | *unrealized* | — |
| Slicers | Slicers (COMP-46) | service |
| Ts Scanner | Ts Scanner (COMP-47) | service |
| Monitoring | Monitoring (COMP-48) | service |
| Monitoring Checks | *unrealized* | — |
| Auto Enrich | Auto Enrich (COMP-50) | service |
| Behavior Decompose | Behavior Decompose (COMP-51) | service |
| Behavior Flows | *unrealized* | — |
| Capability Inference | Capability Inference (COMP-53) | service |
| Compaction | Compaction (COMP-54) | service |
| Decompose | *unrealized* | — |
| Deep Decompose | Deep Decompose (COMP-56) | service |
| Enrich | *unrealized* | — |
| Enrichment Context | Enrichment Context (COMP-58) | service |
| Naming Context | Naming Context (COMP-59) | service |
| Pipeline | Pipeline (COMP-60) | service |
| Trigger Detection | Trigger Detection (COMP-61) | service |
| Use Case Inference | Use Case Inference (COMP-62) | service |
| Patterns | Patterns (COMP-63) | service |
| Store | Store (COMP-64) | service |
| Allocate | Allocate (COMP-65) | service |
| Allocate Types | Allocate Types (COMP-66) | service |
| Artifacts | *unrealized* | — |
| Cache | *unrealized* | — |
| Context Gen | *unrealized* | — |
| Contract | Contract (COMP-70) | service |
| Contract Types | *unrealized* | — |
| Coordinator | Coordinator (COMP-72) | service |
| Decompose Types | *unrealized* | — |
| Emit | Emit (COMP-74) | service |
| Emit Types | *unrealized* | — |
| Global Learning | Global Learning (COMP-76) | service |
| Infer | Infer (COMP-77) | service |
| Infer Types | *unrealized* | — |
| Learning | *unrealized* | — |
| Lessons | Lessons (COMP-80) | service |
| Observe | Observe (COMP-81) | service |
| Observe Types | *unrealized* | — |
| Regen Score | *unrealized* | — |
| Relate | Relate (COMP-84) | service |
| Relate Types | *unrealized* | — |
| Report | Report (COMP-86) | service |
| Requirements Derive | Requirements Derive (COMP-87) | service |
| Specify | Specify (COMP-88) | service |
| Specify Types | *unrealized* | — |
| Synthesize | Synthesize (COMP-90) | service |
| Synthesize Types | *unrealized* | — |
| Validate | Validate (COMP-92) | service |
| Validate Types | *unrealized* | — |
| Discovery | Discovery (COMP-94) | service |
| CLI Main | *unrealized* | — |

## Behavioral Coverage

Total behaviors: 19

**Untraced behaviors:** 19
- GET  (BEH-1)
- GET bookmarklets/ (BEH-2)
- GET tags/ (BEH-3)
- GET filters/ (BEH-4)
- GET views/ (BEH-5)
- GET views/<view>/ (BEH-6)
- GET models/ (BEH-7)
- GET ^models/(?P<app_label>[^.]+)\.(?P<model_name>[^/]+)/$ (BEH-8)
- GET templates/<path:template>/ (BEH-9)
- GET login/ (BEH-10)
- *...and 9 more*
