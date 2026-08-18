---
document: Functional Analysis
system: Src (orchestration)
system_id: SYS-unknown
generated_at: 2026-08-18T20:06:07Z
generator_version: 0.3.0
model_hash: 1390e5be5ea9
edition: 4
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 13/13 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Functional Analysis: Src (orchestration)

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
| CAP-15 | Auto Enrich | medium | ACTIVE | — |
| CAP-16 | Behavior Decompose | medium | ACTIVE | — |
| CAP-17 | Behavior Flows | medium | ACTIVE | — |
| CAP-18 | Capability Inference | medium | ACTIVE | — |
| CAP-19 | Compaction | medium | ACTIVE | — |
| CAP-20 | Decompose | medium | ACTIVE | — |
| CAP-21 | Deep Decompose | medium | ACTIVE | — |
| CAP-22 | Enrich | medium | ACTIVE | — |
| CAP-23 | Enrichment Context | medium | ACTIVE | — |
| CAP-24 | Naming Context | medium | ACTIVE | — |
| CAP-25 | Pipeline | medium | ACTIVE | — |
| CAP-26 | Trigger Detection | medium | ACTIVE | — |
| CAP-27 | Use Case Inference | medium | ACTIVE | — |

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
    CAP-15["Auto Enrich"]
    CAP-16["Behavior Decompose"]
    CAP-17["Behavior Flows"]
    CAP-18["Capability Inference"]
    CAP-19["Compaction"]
    CAP-20["Decompose"]
    CAP-21["Deep Decompose"]
    CAP-22["Enrich"]
    CAP-23["Enrichment Context"]
    CAP-24["Naming Context"]
    CAP-25["Pipeline"]
    CAP-26["Trigger Detection"]
    CAP-27["Use Case Inference"]
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
| Auto Enrich | Auto Enrich (src-orchestration-COMP-1) | service |
| Behavior Decompose | Behavior Decompose (src-orchestration-COMP-2) | service |
| Behavior Flows | Behavior Flows (src-orchestration-COMP-3) | service |
| Capability Inference | Capability Inference (src-orchestration-COMP-4) | service |
| Compaction | Compaction (src-orchestration-COMP-5) | service |
| Decompose | *unrealized* | — |
| Deep Decompose | Decompose (src-orchestration-COMP-6) | service |
| Deep Decompose | Deep Decompose (src-orchestration-COMP-7) | service |
| Enrich | Enrich (src-orchestration-COMP-8) | service |
| Enrichment Context | Enrichment Context (src-orchestration-COMP-9) | service |
| Naming Context | Naming Context (src-orchestration-COMP-10) | service |
| Pipeline | Pipeline (src-orchestration-COMP-11) | service |
| Trigger Detection | Trigger Detection (src-orchestration-COMP-12) | service |
| Use Case Inference | Use Case Inference (src-orchestration-COMP-13) | service |

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
