---
document: Functional Analysis
system: Src (pipeline)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:52Z
generator_version: 0.3.0
model_hash: ccd998005d8e
edition: 14
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 21/21 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Functional Analysis: Src (pipeline)

## Capability Inventory

| ID | Capability | Priority | Status | Description |
|----|-----------|----------|--------|-------------|
| CAP-1 | Root Management | medium | ACTIVE | — |
| CAP-2 | Bookmarklet Management | medium | ACTIVE | — |
| CAP-3 | Tag Management | medium | ACTIVE | — |
| CAP-4 | Filter Management | medium | ACTIVE | — |
| CAP-5 | View Management | medium | ACTIVE | — |
| CAP-6 | Model Management | medium | ACTIVE | — |
| CAP-7 | ^Model Management | medium | ACTIVE | — |
| CAP-8 | Template Management | medium | ACTIVE | — |
| CAP-9 | Login Management | medium | ACTIVE | — |
| CAP-10 | Logout Management | medium | ACTIVE | — |
| CAP-11 | Password Change Management | medium | ACTIVE | — |
| CAP-12 | Password Reset Management | medium | ACTIVE | — |
| CAP-13 | Reset Management | medium | ACTIVE | — |
| CAP-14 | <Path:Url> Management | medium | ACTIVE | — |
| CAP-15 | gRPC Services | medium | ACTIVE | — |
| CAP-16 | Allocate | medium | ACTIVE | — |
| CAP-17 | Allocate Types | medium | ACTIVE | — |
| CAP-18 | Artifacts | medium | ACTIVE | — |
| CAP-19 | Cache | medium | ACTIVE | — |
| CAP-20 | Context Gen | medium | ACTIVE | — |
| CAP-21 | Contract | medium | ACTIVE | — |
| CAP-22 | Contract Types | medium | ACTIVE | — |
| CAP-23 | Coordinator | medium | ACTIVE | — |
| CAP-24 | Corrections | medium | ACTIVE | — |
| CAP-25 | Decompose | medium | ACTIVE | — |
| CAP-26 | Decompose Types | medium | ACTIVE | — |
| CAP-27 | Emit | medium | ACTIVE | — |
| CAP-28 | Emit Types | medium | ACTIVE | — |
| CAP-29 | Global Learning | medium | ACTIVE | — |
| CAP-30 | Infer | medium | ACTIVE | — |
| CAP-31 | Infer Types | medium | ACTIVE | — |
| CAP-32 | Learning | medium | ACTIVE | — |
| CAP-33 | Lessons | medium | ACTIVE | — |
| CAP-34 | Observe | medium | ACTIVE | — |
| CAP-35 | Observe Types | medium | ACTIVE | — |
| CAP-36 | Protocol | medium | ACTIVE | — |
| CAP-37 | Regen Score | medium | ACTIVE | — |
| CAP-38 | Relate | medium | ACTIVE | — |
| CAP-39 | Relate Types | medium | ACTIVE | — |
| CAP-40 | Report | medium | ACTIVE | — |
| CAP-41 | Requirements Derive | medium | ACTIVE | — |
| CAP-42 | Specify | medium | ACTIVE | — |
| CAP-43 | Specify Types | medium | ACTIVE | — |
| CAP-44 | Synthesize | medium | ACTIVE | — |
| CAP-45 | Synthesize Types | medium | ACTIVE | — |
| CAP-46 | Validate | medium | ACTIVE | — |
| CAP-47 | Validate Types | medium | ACTIVE | — |

## Functional Decomposition

```mermaid
graph TD
    CAP-1["Root Management"]
    CAP-2["Bookmarklet Management"]
    CAP-3["Tag Management"]
    CAP-4["Filter Management"]
    CAP-5["View Management"]
    CAP-6["Model Management"]
    CAP-7["^Model Management"]
    CAP-8["Template Management"]
    CAP-9["Login Management"]
    CAP-10["Logout Management"]
    CAP-11["Password Change Management"]
    CAP-12["Password Reset Management"]
    CAP-13["Reset Management"]
    CAP-14["<Path:Url> Management"]
    CAP-15["gRPC Services"]
    CAP-16["Allocate"]
    CAP-17["Allocate Types"]
    CAP-18["Artifacts"]
    CAP-19["Cache"]
    CAP-20["Context Gen"]
    CAP-21["Contract"]
    CAP-22["Contract Types"]
    CAP-23["Coordinator"]
    CAP-24["Corrections"]
    CAP-25["Decompose"]
    CAP-26["Decompose Types"]
    CAP-27["Emit"]
    CAP-28["Emit Types"]
    CAP-29["Global Learning"]
    CAP-30["Infer"]
    CAP-31["Infer Types"]
    CAP-32["Learning"]
    CAP-33["Lessons"]
    CAP-34["Observe"]
    CAP-35["Observe Types"]
    CAP-36["Protocol"]
    CAP-37["Regen Score"]
    CAP-38["Relate"]
    CAP-39["Relate Types"]
    CAP-40["Report"]
    CAP-41["Requirements Derive"]
    CAP-42["Specify"]
    CAP-43["Specify Types"]
    CAP-44["Synthesize"]
    CAP-45["Synthesize Types"]
    CAP-46["Validate"]
    CAP-47["Validate Types"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Root Management | *unrealized* | — |
| Bookmarklet Management | *unrealized* | — |
| Tag Management | *unrealized* | — |
| Filter Management | *unrealized* | — |
| View Management | *unrealized* | — |
| Model Management | *unrealized* | — |
| ^Model Management | *unrealized* | — |
| Template Management | *unrealized* | — |
| Login Management | *unrealized* | — |
| Logout Management | *unrealized* | — |
| Password Change Management | *unrealized* | — |
| Password Reset Management | *unrealized* | — |
| Reset Management | *unrealized* | — |
| <Path:Url> Management | *unrealized* | — |
| gRPC Services | *unrealized* | — |
| Allocate | Allocate (src-pipeline-COMP-16) | service |
| Allocate Types | *unrealized* | — |
| Artifacts | Artifacts (src-pipeline-COMP-18) | service |
| Cache | Cache (src-pipeline-COMP-19) | service |
| Context Gen | Context Gen (src-pipeline-COMP-20) | service |
| Contract | Contract (src-pipeline-COMP-21) | service |
| Contract Types | *unrealized* | — |
| Coordinator | Coordinator (src-pipeline-COMP-23) | service |
| Corrections | Corrections (src-pipeline-COMP-24) | service |
| Decompose | Decompose (src-pipeline-COMP-25) | service |
| Decompose Types | *unrealized* | — |
| Emit | Emit (src-pipeline-COMP-27) | service |
| Emit Types | *unrealized* | — |
| Global Learning | Global Learning (src-pipeline-COMP-29) | service |
| Infer | Infer (src-pipeline-COMP-30) | service |
| Infer Types | *unrealized* | — |
| Learning | *unrealized* | — |
| Lessons | Lessons (src-pipeline-COMP-33) | service |
| Observe | Observe (src-pipeline-COMP-34) | service |
| Observe Types | *unrealized* | — |
| Protocol | Protocol (src-pipeline-COMP-36) | service |
| Regen Score | Regen Score (src-pipeline-COMP-37) | service |
| Relate | Relate (src-pipeline-COMP-38) | service |
| Relate Types | *unrealized* | — |
| Report | Report (src-pipeline-COMP-40) | service |
| Requirements Derive | Requirements Derive (src-pipeline-COMP-41) | service |
| Specify | Specify (src-pipeline-COMP-42) | service |
| Specify Types | *unrealized* | — |
| Synthesize | Synthesize (src-pipeline-COMP-44) | service |
| Synthesize Types | *unrealized* | — |
| Validate | Validate (src-pipeline-COMP-46) | service |
| Validate Types | *unrealized* | — |

## Behavioral Coverage

Total behaviors: 18

**Untraced behaviors:** 18
- GET  (BEH-1)
- GET bookmarklets/ (BEH-2)
- GET tags/ (BEH-3)
- GET filters/ (BEH-4)
- GET views/ (BEH-5)
- GET views/<view>/ (BEH-6)
- GET models/ (BEH-7)
- GET ^models/(?P<app_label>[^.]+)\.(?P<model_name>[^/]+)/$ (BEH-8)
- GET templates/<path:template>/ (BEH-9)
- GET password_change/ (BEH-12)
- *...and 8 more*
