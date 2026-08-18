---
document: Functional Analysis
system: Projects (views)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:32Z
generator_version: 0.3.0
model_hash: a4f321da275c
edition: 3
---

# Functional Analysis: Projects (views)

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
| CAP-15 | Csrf | medium | ACTIVE | — |
| CAP-16 | Debug | medium | ACTIVE | — |
| CAP-17 | Cache | medium | ACTIVE | — |
| CAP-18 | Clickjacking | medium | ACTIVE | — |
| CAP-19 | Csp | medium | ACTIVE | — |
| CAP-20 | Http | medium | ACTIVE | — |
| CAP-21 | Vary | medium | ACTIVE | — |
| CAP-22 | Defaults | medium | ACTIVE | — |
| CAP-23 | Dates | medium | ACTIVE | — |
| CAP-24 | Detail | medium | ACTIVE | — |
| CAP-25 | Edit | medium | ACTIVE | — |
| CAP-26 | List | medium | ACTIVE | — |
| CAP-27 | I18N | medium | ACTIVE | — |
| CAP-28 | Static | medium | ACTIVE | — |

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
    CAP-15["Csrf"]
    CAP-16["Debug"]
    CAP-17["Cache"]
    CAP-18["Clickjacking"]
    CAP-19["Csp"]
    CAP-20["Http"]
    CAP-21["Vary"]
    CAP-22["Defaults"]
    CAP-23["Dates"]
    CAP-24["Detail"]
    CAP-25["Edit"]
    CAP-26["List"]
    CAP-27["I18N"]
    CAP-28["Static"]
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
| Csrf | Csrf (COMP-15) | service |
| Debug | Debug (COMP-16) | service |
| Cache | Cache (COMP-17) | service |
| Clickjacking | Clickjacking (COMP-18) | service |
| Csp | Csp (COMP-19) | service |
| Http | Http (COMP-20) | service |
| Vary | Vary (COMP-21) | service |
| Defaults | Defaults (COMP-22) | service |
| Dates | Dates (COMP-23) | service |
| Detail | Detail (COMP-24) | service |
| Edit | Edit (COMP-25) | service |
| List | List (COMP-26) | service |
| I18N | I18N (COMP-27) | service |
| Static | Static (COMP-28) | service |

## Behavioral Coverage

Total behaviors: 35

**Untraced behaviors:** 35
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
- *...and 25 more*
