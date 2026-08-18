---
document: Functional Analysis
system: Projects (db)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:31Z
generator_version: 0.3.0
model_hash: fcdfcd0d1016
edition: 3
---

# Functional Analysis: Projects (db)

## Capability Inventory

| ID | Capability | Priority | Status | Description |
|----|-----------|----------|--------|-------------|
| CAP-1 | Web Routes | medium | ACTIVE | — |
| CAP-2 | Client | medium | ACTIVE | — |
| CAP-3 | Creation | medium | ACTIVE | — |
| CAP-4 | Features | medium | ACTIVE | — |
| CAP-5 | Introspection | medium | ACTIVE | — |
| CAP-6 | Operations | medium | ACTIVE | — |
| CAP-7 | Schema | medium | ACTIVE | — |
| CAP-8 | Validation | medium | ACTIVE | — |
| CAP-9 | Ddl References | medium | ACTIVE | — |
| CAP-10 | Compiler | medium | ACTIVE | — |
| CAP-11 | Functions | medium | ACTIVE | — |
| CAP-12 | Autodetector | medium | ACTIVE | — |
| CAP-13 | Exceptions | medium | ACTIVE | — |
| CAP-14 | Executor | medium | ACTIVE | — |
| CAP-15 | Graph | medium | ACTIVE | — |
| CAP-16 | Loader | medium | ACTIVE | — |
| CAP-17 | Migration | medium | ACTIVE | — |
| CAP-18 | Fields | medium | ACTIVE | — |
| CAP-19 | Models | medium | ACTIVE | — |
| CAP-20 | Special | medium | ACTIVE | — |
| CAP-21 | Optimizer | medium | ACTIVE | — |
| CAP-22 | Questioner | medium | ACTIVE | — |
| CAP-23 | Recorder | medium | ACTIVE | — |
| CAP-24 | Serializer | medium | ACTIVE | — |
| CAP-25 | State | medium | ACTIVE | — |
| CAP-26 | Writer | medium | ACTIVE | — |
| CAP-27 | Aggregates | medium | ACTIVE | — |
| CAP-28 | Constraints | medium | ACTIVE | — |
| CAP-29 | Deletion | medium | ACTIVE | — |
| CAP-30 | Enums | medium | ACTIVE | — |
| CAP-31 | Expressions | medium | ACTIVE | — |
| CAP-32 | Fetch Modes | medium | ACTIVE | — |
| CAP-33 | Composite | medium | ACTIVE | — |
| CAP-34 | Files | medium | ACTIVE | — |
| CAP-35 | Generated | medium | ACTIVE | — |
| CAP-36 | Json | medium | ACTIVE | — |
| CAP-37 | Mixins | medium | ACTIVE | — |
| CAP-38 | Proxy | medium | ACTIVE | — |
| CAP-39 | Related | medium | ACTIVE | — |
| CAP-40 | Related Descriptors | medium | ACTIVE | — |
| CAP-41 | Related Lookups | medium | ACTIVE | — |
| CAP-42 | Reverse Related | medium | ACTIVE | — |
| CAP-43 | Tuple Lookups | medium | ACTIVE | — |
| CAP-44 | Comparison | medium | ACTIVE | — |
| CAP-45 | Datetime | medium | ACTIVE | — |
| CAP-46 | Math | medium | ACTIVE | — |
| CAP-47 | Text | medium | ACTIVE | — |
| CAP-48 | Uuid | medium | ACTIVE | — |
| CAP-49 | Window | medium | ACTIVE | — |
| CAP-50 | Indexes | medium | ACTIVE | — |
| CAP-51 | Lookups | medium | ACTIVE | — |
| CAP-52 | Manager | medium | ACTIVE | — |
| CAP-53 | Options | medium | ACTIVE | — |
| CAP-54 | Query | medium | ACTIVE | — |
| CAP-55 | Query Utils | medium | ACTIVE | — |
| CAP-56 | Signals | medium | ACTIVE | — |
| CAP-57 | Datastructures | medium | ACTIVE | — |
| CAP-58 | Subqueries | medium | ACTIVE | — |
| CAP-59 | Where | medium | ACTIVE | — |
| CAP-60 | Transaction | medium | ACTIVE | — |
| CAP-61 | Database Migrations | medium | ACTIVE | — |

## Functional Decomposition

```mermaid
graph TD
    CAP-1["Web Routes"]
    CAP-2["Client"]
    CAP-3["Creation"]
    CAP-4["Features"]
    CAP-5["Introspection"]
    CAP-6["Operations"]
    CAP-7["Schema"]
    CAP-8["Validation"]
    CAP-9["Ddl References"]
    CAP-10["Compiler"]
    CAP-11["Functions"]
    CAP-12["Autodetector"]
    CAP-13["Exceptions"]
    CAP-14["Executor"]
    CAP-15["Graph"]
    CAP-16["Loader"]
    CAP-17["Migration"]
    CAP-18["Fields"]
    CAP-19["Models"]
    CAP-20["Special"]
    CAP-21["Optimizer"]
    CAP-22["Questioner"]
    CAP-23["Recorder"]
    CAP-24["Serializer"]
    CAP-25["State"]
    CAP-26["Writer"]
    CAP-27["Aggregates"]
    CAP-28["Constraints"]
    CAP-29["Deletion"]
    CAP-30["Enums"]
    CAP-31["Expressions"]
    CAP-32["Fetch Modes"]
    CAP-33["Composite"]
    CAP-34["Files"]
    CAP-35["Generated"]
    CAP-36["Json"]
    CAP-37["Mixins"]
    CAP-38["Proxy"]
    CAP-39["Related"]
    CAP-40["Related Descriptors"]
    CAP-41["Related Lookups"]
    CAP-42["Reverse Related"]
    CAP-43["Tuple Lookups"]
    CAP-44["Comparison"]
    CAP-45["Datetime"]
    CAP-46["Math"]
    CAP-47["Text"]
    CAP-48["Uuid"]
    CAP-49["Window"]
    CAP-50["Indexes"]
    CAP-51["Lookups"]
    CAP-52["Manager"]
    CAP-53["Options"]
    CAP-54["Query"]
    CAP-55["Query Utils"]
    CAP-56["Signals"]
    CAP-57["Datastructures"]
    CAP-58["Subqueries"]
    CAP-59["Where"]
    CAP-60["Transaction"]
    CAP-61["Database Migrations"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Web Routes | *unrealized* | — |
| Client | Client (COMP-2) | service |
| Creation | Creation (COMP-3) | service |
| Features | Features (COMP-4) | service |
| Introspection | Introspection (COMP-5) | service |
| Operations | Operations (COMP-6) | service |
| Schema | Schema (COMP-7) | service |
| Validation | Validation (COMP-8) | service |
| Ddl References | Ddl References (COMP-9) | service |
| Compiler | Compiler (COMP-10) | service |
| Functions | Functions (COMP-11) | service |
| Autodetector | Autodetector (COMP-12) | service |
| Exceptions | Exceptions (COMP-13) | service |
| Executor | Executor (COMP-14) | service |
| Graph | Graph (COMP-15) | service |
| Loader | Loader (COMP-16) | service |
| Migration | Migration (COMP-17) | service |
| Fields | Fields (COMP-18) | service |
| Models | Models (COMP-19) | service |
| Special | Special (COMP-20) | service |
| Optimizer | Optimizer (COMP-21) | service |
| Questioner | Questioner (COMP-22) | service |
| Recorder | Recorder (COMP-23) | service |
| Serializer | Serializer (COMP-24) | service |
| State | State (COMP-25) | service |
| Writer | Writer (COMP-26) | service |
| Aggregates | Aggregates (COMP-27) | service |
| Constraints | Constraints (COMP-28) | service |
| Deletion | Deletion (COMP-29) | service |
| Enums | Enums (COMP-30) | service |
| Expressions | Expressions (COMP-31) | service |
| Fetch Modes | Fetch Modes (COMP-32) | service |
| Composite | Composite (COMP-33) | service |
| Files | Files (COMP-34) | service |
| Generated | Generated (COMP-35) | service |
| Json | Json (COMP-36) | service |
| Mixins | Mixins (COMP-37) | service |
| Proxy | Proxy (COMP-38) | service |
| Related | Related (COMP-39) | service |
| Related Descriptors | *unrealized* | — |
| Related Lookups | Related Lookups (COMP-41) | service |
| Reverse Related | Reverse Related (COMP-42) | service |
| Tuple Lookups | Tuple Lookups (COMP-43) | service |
| Comparison | Comparison (COMP-44) | service |
| Datetime | Datetime (COMP-45) | service |
| Math | Math (COMP-46) | service |
| Text | Text (COMP-47) | service |
| Uuid | Uuid (COMP-48) | service |
| Window | Window (COMP-49) | service |
| Indexes | Indexes (COMP-50) | service |
| Lookups | *unrealized* | — |
| Manager | Manager (COMP-52) | service |
| Options | Options (COMP-53) | service |
| Query | Query (COMP-54) | service |
| Query Utils | Query Utils (COMP-55) | service |
| Signals | Signals (COMP-56) | service |
| Datastructures | Datastructures (COMP-57) | service |
| Subqueries | Subqueries (COMP-58) | service |
| Where | Where (COMP-59) | service |
| Transaction | Transaction (COMP-60) | service |
| Database Migrations | *unrealized* | — |

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
