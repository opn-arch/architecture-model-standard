---
document: Functional Analysis
system: Src (manifest)
system_id: SYS-unknown
generated_at: 2026-08-19T17:00:10Z
generator_version: 0.3.0
model_hash: 43ce18da3e69
edition: 7
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 17/17 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Functional Analysis: Src (manifest)

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
| CAP-16 | Behavior | medium | ACTIVE | — |
| CAP-17 | Blocks | medium | ACTIVE | — |
| CAP-18 | Body Hints | medium | ACTIVE | — |
| CAP-19 | Call Graph | medium | ACTIVE | — |
| CAP-20 | Chains | medium | ACTIVE | — |
| CAP-21 | Display | medium | ACTIVE | — |
| CAP-22 | Generator | medium | ACTIVE | — |
| CAP-23 | Grouping | medium | ACTIVE | — |
| CAP-24 | Interfaces | medium | ACTIVE | — |
| CAP-25 | Kt Scanner | medium | ACTIVE | — |
| CAP-26 | Metrics | medium | ACTIVE | — |
| CAP-27 | Multi Scanner | medium | ACTIVE | — |
| CAP-28 | Protocol | medium | ACTIVE | — |
| CAP-29 | Recursive | medium | ACTIVE | — |
| CAP-30 | Scan Cache | medium | ACTIVE | — |
| CAP-31 | Scanner | medium | ACTIVE | — |
| CAP-32 | Slicers | medium | ACTIVE | — |
| CAP-33 | Ts Scanner | medium | ACTIVE | — |

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
    CAP-16["Behavior"]
    CAP-17["Blocks"]
    CAP-18["Body Hints"]
    CAP-19["Call Graph"]
    CAP-20["Chains"]
    CAP-21["Display"]
    CAP-22["Generator"]
    CAP-23["Grouping"]
    CAP-24["Interfaces"]
    CAP-25["Kt Scanner"]
    CAP-26["Metrics"]
    CAP-27["Multi Scanner"]
    CAP-28["Protocol"]
    CAP-29["Recursive"]
    CAP-30["Scan Cache"]
    CAP-31["Scanner"]
    CAP-32["Slicers"]
    CAP-33["Ts Scanner"]
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
| Behavior | Behavior (src-manifest-COMP-16) | service |
| Blocks | Blocks (src-manifest-COMP-17) | service |
| Body Hints | Body Hints (src-manifest-COMP-18) | service |
| Call Graph | Call Graph (src-manifest-COMP-19) | service |
| Chains | Chains (src-manifest-COMP-20) | service |
| Display | Display (src-manifest-COMP-21) | service |
| Generator | Generator (src-manifest-COMP-22) | service |
| Grouping | Grouping (src-manifest-COMP-23) | service |
| Interfaces | Interfaces (src-manifest-COMP-24) | service |
| Kt Scanner | Kt Scanner (src-manifest-COMP-25) | service |
| Metrics | Metrics (src-manifest-COMP-26) | service |
| Multi Scanner | Multi Scanner (src-manifest-COMP-27) | service |
| Protocol | Protocol (src-manifest-COMP-28) | service |
| Recursive | Recursive (src-manifest-COMP-29) | service |
| Scan Cache | Scan Cache (src-manifest-COMP-30) | service |
| Scanner | *unrealized* | — |
| Slicers | Slicers (src-manifest-COMP-32) | service |
| Ts Scanner | Ts Scanner (src-manifest-COMP-33) | service |

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
