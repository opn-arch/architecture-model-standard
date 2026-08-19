---
document: Functional Analysis
system: Src (core)
system_id: SYS-unknown
generated_at: 2026-08-19T17:00:06Z
generator_version: 0.3.0
model_hash: 65254bb02f54
edition: 14
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 16/16 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Functional Analysis: Src (core)

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
| CAP-15 | Cluster | medium | ACTIVE | — |
| CAP-16 | Completeness | medium | ACTIVE | — |
| CAP-17 | Compression | medium | ACTIVE | — |
| CAP-18 | Confidence | medium | ACTIVE | — |
| CAP-19 | Corrections | medium | ACTIVE | — |
| CAP-20 | Coverage | medium | ACTIVE | — |
| CAP-21 | Decomposer | medium | ACTIVE | — |
| CAP-22 | Differ | medium | ACTIVE | — |
| CAP-23 | Merger | medium | ACTIVE | — |
| CAP-24 | Parser | medium | ACTIVE | — |
| CAP-25 | Regen Readiness | medium | ACTIVE | — |
| CAP-26 | Representativeness | medium | ACTIVE | — |
| CAP-27 | Slicer | medium | ACTIVE | — |
| CAP-28 | Source Block Assign | medium | ACTIVE | — |
| CAP-29 | Source Block Quality | medium | ACTIVE | — |
| CAP-30 | Validator | medium | ACTIVE | — |
| CAP-31 | Visualize | medium | ACTIVE | — |

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
    CAP-15["Cluster"]
    CAP-16["Completeness"]
    CAP-17["Compression"]
    CAP-18["Confidence"]
    CAP-19["Corrections"]
    CAP-20["Coverage"]
    CAP-21["Decomposer"]
    CAP-22["Differ"]
    CAP-23["Merger"]
    CAP-24["Parser"]
    CAP-25["Regen Readiness"]
    CAP-26["Representativeness"]
    CAP-27["Slicer"]
    CAP-28["Source Block Assign"]
    CAP-29["Source Block Quality"]
    CAP-30["Validator"]
    CAP-31["Visualize"]
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
| Cluster | Cluster (src-core-COMP-15) | service |
| Completeness | Completeness (src-core-COMP-16) | service |
| Compression | Compression (src-core-COMP-17) | service |
| Confidence | Confidence (src-core-COMP-18) | service |
| Corrections | Corrections (src-core-COMP-19) | service |
| Coverage | Coverage (src-core-COMP-20) | service |
| Decomposer | Decomposer (src-core-COMP-21) | service |
| Differ | Differ (src-core-COMP-22) | service |
| Merger | Merger (src-core-COMP-23) | service |
| Parser | Parser (src-core-COMP-24) | service |
| Regen Readiness | Regen Readiness (src-core-COMP-25) | service |
| Representativeness | Representativeness (src-core-COMP-26) | service |
| Slicer | Slicer (src-core-COMP-27) | service |
| Source Block Assign | Source Block Assign (src-core-COMP-28) | service |
| Source Block Quality | *unrealized* | — |
| Validator | Validator (src-core-COMP-30) | service |
| Visualize | Visualize (src-core-COMP-31) | service |

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
