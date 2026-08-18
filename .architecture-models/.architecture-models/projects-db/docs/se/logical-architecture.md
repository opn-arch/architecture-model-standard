---
document: Logical Architecture
system: Projects (db)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:31Z
generator_version: 0.3.0
model_hash: fcdfcd0d1016
edition: 3
---

# Logical Architecture: Projects (db)

## Layer Structure

| Order | Layer | Technologies | Directories |
|-------|-------|-------------|-------------|
| 0 | data | — | — |
| 0 | infra | — | — |

## Component Allocation

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Client (COMP-2) | service | 5 files | — |
| Creation (COMP-3) | service | 5 files | — |
| Features (COMP-4) | service | 6 files | — |
| Introspection (COMP-5) | service | 5 files | — |
| Operations (COMP-6) | service | 5 files | — |
| Schema (COMP-7) | service | 5 files | — |
| Validation (COMP-8) | service | 3 files | — |
| Ddl References (COMP-9) | service | 1 files | — |
| Compiler (COMP-10) | service | 3 files | — |
| Functions (COMP-11) | service | 2 files | — |
| Autodetector (COMP-12) | service | 1 files | — |
| Exceptions (COMP-13) | service | 1 files | — |
| Executor (COMP-14) | service | 1 files | — |
| Graph (COMP-15) | service | 1 files | — |
| Loader (COMP-16) | service | 1 files | — |
| Migration (COMP-17) | service | 1 files | — |
| Fields (COMP-18) | service | 1 files | — |
| Models (COMP-19) | service | 1 files | — |
| Special (COMP-20) | service | 1 files | — |
| Optimizer (COMP-21) | service | 1 files | — |
| Questioner (COMP-22) | service | 1 files | — |
| Recorder (COMP-23) | service | 1 files | — |
| Serializer (COMP-24) | service | 1 files | — |
| State (COMP-25) | service | 1 files | — |
| Writer (COMP-26) | service | 1 files | — |
| Aggregates (COMP-27) | service | 1 files | — |
| Constraints (COMP-28) | service | 1 files | — |
| Deletion (COMP-29) | service | 1 files | — |
| Enums (COMP-30) | service | 1 files | — |
| Expressions (COMP-31) | service | 1 files | — |
| Fetch Modes (COMP-32) | service | 1 files | — |
| Composite (COMP-33) | service | 1 files | — |
| Files (COMP-34) | service | 1 files | — |
| Generated (COMP-35) | service | 1 files | — |
| Json (COMP-36) | service | 2 files | — |
| Mixins (COMP-37) | service | 2 files | — |
| Proxy (COMP-38) | service | 1 files | — |
| Related (COMP-39) | service | 3 files | — |
| Related Lookups (COMP-41) | service | 1 files | — |
| Reverse Related (COMP-42) | service | 1 files | — |
| Tuple Lookups (COMP-43) | service | 1 files | — |
| Comparison (COMP-44) | service | 1 files | — |
| Datetime (COMP-45) | service | 1 files | — |
| Math (COMP-46) | service | 1 files | — |
| Text (COMP-47) | service | 1 files | — |
| Uuid (COMP-48) | service | 1 files | — |
| Window (COMP-49) | service | 1 files | — |
| Indexes (COMP-50) | service | 1 files | — |
| Manager (COMP-52) | service | 1 files | — |
| Options (COMP-53) | service | 1 files | — |
| Query (COMP-54) | service | 3 files | — |
| Query Utils (COMP-55) | service | 13 files | — |
| Signals (COMP-56) | service | 2 files | — |
| Datastructures (COMP-57) | service | 1 files | — |
| Subqueries (COMP-58) | service | 1 files | — |
| Where (COMP-59) | service | 1 files | — |
| Transaction (COMP-60) | service | 1 files | — |
| Infrastructure (COMP-62) | service | 3 files | — |

## Inter-Component Interfaces

*No interfaces defined.*

## Dependency Graph

```mermaid
graph TD
    COMP-44["Comparison"]
    COMP-53["Options"]
    COMP-44 --> COMP-53
    COMP-26["Writer"]
    COMP-22["Questioner"]
    COMP-26 --> COMP-22
    COMP-5["Introspection"]
    COMP-28["Constraints"]
    COMP-5 --> COMP-28
    COMP-36["Json"]
    COMP-54["Query"]
    COMP-36 --> COMP-54
    COMP-14["Executor"]
    COMP-16["Loader"]
    COMP-14 --> COMP-16
    COMP-3["Creation"]
    COMP-62["Infrastructure"]
    COMP-3 --> COMP-62
    COMP-46["Math"]
    COMP-28 --> COMP-46
    COMP-50["Indexes"]
    COMP-44 --> COMP-50
    COMP-41["Related Lookups"]
    COMP-19["Models"]
    COMP-41 --> COMP-19
    COMP-10["Compiler"]
    COMP-18["Fields"]
    COMP-10 --> COMP-18
    COMP-27["Aggregates"]
    COMP-54 --> COMP-27
    COMP-38["Proxy"]
    COMP-53 --> COMP-38
    COMP-47["Text"]
    COMP-46 --> COMP-47
    COMP-30["Enums"]
    COMP-38 --> COMP-30
    COMP-21["Optimizer"]
    COMP-26 --> COMP-21
    COMP-12["Autodetector"]
    COMP-24["Serializer"]
    COMP-12 --> COMP-24
    COMP-11["Functions"]
    COMP-50 --> COMP-11
    COMP-8["Validation"]
    COMP-8 --> COMP-5
    COMP-12 --> COMP-22
    COMP-9["Ddl References"]
    COMP-5 --> COMP-9
    COMP-57["Datastructures"]
    COMP-59["Where"]
    COMP-57 --> COMP-59
    COMP-7["Schema"]
    COMP-2["Client"]
    COMP-7 --> COMP-2
    COMP-33["Composite"]
    COMP-27 --> COMP-33
    COMP-55["Query Utils"]
    COMP-55 --> COMP-18
    COMP-56["Signals"]
    COMP-27 --> COMP-56
    COMP-36 --> COMP-47
    COMP-45["Datetime"]
    COMP-59 --> COMP-45
    COMP-58["Subqueries"]
    COMP-58 --> COMP-55
    COMP-59 --> COMP-28
    COMP-37["Mixins"]
    COMP-37 --> COMP-19
    COMP-22 --> COMP-56
    COMP-12 --> COMP-21
    COMP-49["Window"]
    COMP-29["Deletion"]
    COMP-49 --> COMP-29
    COMP-3 --> COMP-54
    COMP-52["Manager"]
    COMP-59 --> COMP-52
    COMP-59 --> COMP-36
    COMP-34["Files"]
    COMP-7 --> COMP-34
    COMP-35["Generated"]
    COMP-35 --> COMP-10
    COMP-15["Graph"]
    COMP-17["Migration"]
    COMP-15 --> COMP-17
    COMP-41 --> COMP-55
    COMP-49 --> COMP-27
    COMP-47 --> COMP-53
    COMP-33 --> COMP-29
    COMP-36 --> COMP-46
    COMP-19 --> COMP-34
    COMP-47 --> COMP-50
    COMP-25["State"]
    COMP-25 --> COMP-29
    COMP-3 --> COMP-58
    COMP-20["Special"]
    COMP-20 --> COMP-2
    COMP-37 --> COMP-41
    COMP-18 --> COMP-19
    COMP-33 --> COMP-28
    COMP-13["Exceptions"]
    COMP-59 --> COMP-13
    COMP-35 --> COMP-57
    COMP-39["Related"]
    COMP-39 --> COMP-53
    COMP-57 --> COMP-53
    COMP-5 --> COMP-59
    COMP-37 --> COMP-55
    COMP-22 --> COMP-62
    COMP-4["Features"]
    COMP-4 --> COMP-59
    COMP-12 --> COMP-53
    COMP-28 --> COMP-50
    COMP-35 --> COMP-56
    COMP-57 --> COMP-50
    COMP-25 --> COMP-27
    COMP-11 --> COMP-56
    COMP-33 --> COMP-36
    COMP-29 --> COMP-28
    COMP-12 --> COMP-50
    COMP-32["Fetch Modes"]
    COMP-24 --> COMP-32
    COMP-29 --> COMP-52
    COMP-6["Operations"]
    COMP-60["Transaction"]
    COMP-6 --> COMP-60
    COMP-43["Tuple Lookups"]
    COMP-43 --> COMP-27
    COMP-24 --> COMP-16
    COMP-18 --> COMP-41
    COMP-45 --> COMP-43
    COMP-31["Expressions"]
    COMP-48["Uuid"]
    COMP-31 --> COMP-48
    COMP-20 --> COMP-7
    COMP-7 --> COMP-31
    COMP-45 --> COMP-30
    COMP-7 --> COMP-6
    COMP-10 --> COMP-29
    COMP-54 --> COMP-60
    COMP-22 --> COMP-54
    COMP-4 --> COMP-60
    COMP-53 --> COMP-19
    COMP-39 --> COMP-38
    COMP-10 --> COMP-45
    COMP-50 --> COMP-37
    COMP-55 --> COMP-29
    COMP-35 --> COMP-62
    COMP-48 --> COMP-19
    COMP-3 --> COMP-4
    COMP-55 --> COMP-45
    COMP-5 --> COMP-53
    COMP-34 --> COMP-55
    COMP-37 --> COMP-11
    COMP-55 --> COMP-28
    COMP-45 --> COMP-35
    COMP-44 --> COMP-19
    COMP-7 --> COMP-5
    COMP-53 --> COMP-41
    COMP-38 --> COMP-29
    COMP-16 --> COMP-15
    COMP-20 --> COMP-6
    COMP-16 --> COMP-13
    COMP-24 --> COMP-18
    COMP-50 --> COMP-56
    COMP-55 --> COMP-9
    COMP-49 --> COMP-60
    COMP-15 --> COMP-12
    COMP-38 --> COMP-28
    COMP-35 --> COMP-54
    COMP-48 --> COMP-41
    COMP-34 --> COMP-5
    COMP-59 --> COMP-53
    COMP-46 --> COMP-48
    COMP-59 --> COMP-50
    COMP-44 --> COMP-41
    COMP-16 --> COMP-24
    COMP-36 --> COMP-48
    COMP-16 --> COMP-22
    COMP-25 --> COMP-60
    COMP-20 --> COMP-5
    COMP-35 --> COMP-58
    COMP-42["Reverse Related"]
    COMP-42 --> COMP-55
    COMP-58 --> COMP-10
    COMP-52 --> COMP-56
    COMP-43 --> COMP-60
    COMP-11 --> COMP-27
    COMP-22 --> COMP-3
    COMP-10 --> COMP-59
    COMP-50 --> COMP-62
    COMP-47 --> COMP-19
    COMP-33 --> COMP-53
    COMP-7 --> COMP-32
    COMP-22 --> COMP-4
    COMP-45 --> COMP-42
    COMP-15 --> COMP-55
    COMP-6 --> COMP-2
    COMP-23["Recorder"]
    COMP-23 --> COMP-13
    COMP-58 --> COMP-57
    COMP-55 --> COMP-59
    COMP-29 --> COMP-53
    COMP-39 --> COMP-19
    COMP-28 --> COMP-19
    COMP-57 --> COMP-19
    COMP-29 --> COMP-50
    COMP-12 --> COMP-19
    COMP-10 --> COMP-60
    COMP-50 --> COMP-54
    COMP-2 --> COMP-60
    COMP-47 --> COMP-41
    COMP-27 --> COMP-60
    COMP-41 --> COMP-57
    COMP-7 --> COMP-30
    COMP-7 --> COMP-39
    COMP-25 --> COMP-17
    COMP-41 --> COMP-33
    COMP-41 --> COMP-56
    COMP-33 --> COMP-38
    COMP-22 --> COMP-50
    COMP-45 --> COMP-28
    COMP-56 --> COMP-29
    COMP-39 --> COMP-41
    COMP-24 --> COMP-29
    COMP-6 --> COMP-7
    COMP-28 --> COMP-41
    COMP-34 --> COMP-43
    COMP-57 --> COMP-41
    COMP-45 --> COMP-52
    COMP-34 --> COMP-30
    COMP-12 --> COMP-41
    COMP-50 --> COMP-58
    COMP-24 --> COMP-45
    COMP-46 --> COMP-34
    COMP-45 --> COMP-36
    COMP-39 --> COMP-55
    COMP-57 --> COMP-55
    COMP-55 --> COMP-53
    COMP-19 --> COMP-37
    COMP-37 --> COMP-33
    COMP-58 --> COMP-62
    COMP-56 --> COMP-27
    COMP-7 --> COMP-18
    COMP-37 --> COMP-56
    COMP-8 --> COMP-9
    COMP-4 --> COMP-7
    COMP-14 --> COMP-60
    COMP-36 --> COMP-34
    COMP-41 --> COMP-42
    COMP-27 --> COMP-48
    COMP-3 --> COMP-2
    COMP-15 --> COMP-23
    COMP-38 --> COMP-53
    COMP-41 --> COMP-62
    COMP-11 --> COMP-60
    COMP-6 --> COMP-31
    COMP-34 --> COMP-35
    COMP-10 --> COMP-38
    COMP-19 --> COMP-33
    COMP-52 --> COMP-27
    COMP-24 --> COMP-15
    COMP-58 --> COMP-52
    COMP-58 --> COMP-54
    COMP-47 --> COMP-11
    COMP-6 --> COMP-55
    COMP-37 --> COMP-42
    COMP-18 --> COMP-56
    COMP-59 --> COMP-19
    COMP-55 --> COMP-38
    COMP-54 --> COMP-31
    COMP-37 --> COMP-62
    COMP-39 --> COMP-11
    COMP-28 --> COMP-11
    COMP-41 --> COMP-54
    COMP-53 --> COMP-37
    COMP-5 --> COMP-55
    COMP-4 --> COMP-55
    COMP-6 --> COMP-5
    COMP-58 --> COMP-13
    COMP-48 --> COMP-37
    COMP-59 --> COMP-41
    COMP-11 --> COMP-48
    COMP-25 --> COMP-12
    COMP-37 --> COMP-54
    COMP-53 --> COMP-33
    COMP-53 --> COMP-56
    COMP-18 --> COMP-62
    COMP-4 --> COMP-5
    COMP-59 --> COMP-55
    COMP-31 --> COMP-32
    COMP-49 --> COMP-31
    COMP-34 --> COMP-42
    COMP-29 --> COMP-19
    COMP-48 --> COMP-33
    COMP-46 --> COMP-44
    COMP-3 --> COMP-6
    COMP-48 --> COMP-56
    COMP-7 --> COMP-29
    COMP-56 --> COMP-60
    COMP-24 --> COMP-60
    COMP-41 --> COMP-46
    COMP-27 --> COMP-34
    COMP-7 --> COMP-45
    COMP-45 --> COMP-53
    COMP-44 --> COMP-56
    COMP-36 --> COMP-44
    COMP-16 --> COMP-12
    COMP-7 --> COMP-28
    COMP-19 --> COMP-29
    COMP-18 --> COMP-54
    COMP-53 --> COMP-42
    COMP-25 --> COMP-31
    COMP-45 --> COMP-50
    COMP-17 --> COMP-16
    COMP-15 --> COMP-57
    COMP-43 --> COMP-31
    COMP-2 --> COMP-7
    COMP-33 --> COMP-55
    COMP-29 --> COMP-41
    COMP-19 --> COMP-25
    COMP-52 --> COMP-60
    COMP-53 --> COMP-62
    COMP-34 --> COMP-28
    COMP-7 --> COMP-9
    COMP-34 --> COMP-52
    COMP-19 --> COMP-27
    COMP-50 --> COMP-48
    COMP-47 --> COMP-37
    COMP-59 --> COMP-11
    COMP-18 --> COMP-14
    COMP-54 --> COMP-32
    COMP-34 --> COMP-36
    COMP-6 --> COMP-43
    COMP-39 --> COMP-35
    COMP-6 --> COMP-49
    COMP-6 --> COMP-30
    COMP-57 --> COMP-10
    COMP-24 --> COMP-17
    COMP-28 --> COMP-37
    COMP-53 --> COMP-54
    COMP-34 --> COMP-8
    COMP-58 --> COMP-50
    COMP-27 --> COMP-31
    COMP-16 --> COMP-55
    COMP-47 --> COMP-33
    COMP-47 --> COMP-56
    COMP-34 --> COMP-13
    COMP-54 --> COMP-43
    COMP-10 --> COMP-55
    COMP-54 --> COMP-49
    COMP-2 --> COMP-55
    COMP-54 --> COMP-30
    COMP-46 --> COMP-39
    COMP-39 --> COMP-33
    COMP-28 --> COMP-33
    COMP-20 --> COMP-8
    COMP-39 --> COMP-56
    COMP-28 --> COMP-56
    COMP-57 --> COMP-56
    COMP-7 --> COMP-59
    COMP-49 --> COMP-32
    COMP-6 --> COMP-35
    COMP-12 --> COMP-56
    COMP-36 --> COMP-39
    COMP-19 --> COMP-4
    COMP-47 --> COMP-42
    COMP-2 --> COMP-5
    COMP-48 --> COMP-27
    COMP-25 --> COMP-23
    COMP-18 --> COMP-4
    COMP-38 --> COMP-55
    COMP-27 --> COMP-44
    COMP-54 --> COMP-35
    COMP-34 --> COMP-3
    COMP-5 --> COMP-10
    COMP-6 --> COMP-57
    COMP-4 --> COMP-10
    COMP-47 --> COMP-62
    COMP-49 --> COMP-43
    COMP-44 --> COMP-27
    COMP-25 --> COMP-32
    COMP-14 --> COMP-55
    COMP-39 --> COMP-42
    COMP-49 --> COMP-30
    COMP-49 --> COMP-39
    COMP-11 --> COMP-31
    COMP-43 --> COMP-32
    COMP-32 --> COMP-13
    COMP-39 --> COMP-62
    COMP-19 --> COMP-60
    COMP-57 --> COMP-62
    COMP-5 --> COMP-57
    COMP-4 --> COMP-57
    COMP-12 --> COMP-62
    COMP-33 --> COMP-43
    COMP-15 --> COMP-13
    COMP-7 --> COMP-53
    COMP-25 --> COMP-43
    COMP-47 --> COMP-54
    COMP-59 --> COMP-37
    COMP-25 --> COMP-30
    COMP-31 --> COMP-29
    COMP-49 --> COMP-18
    COMP-45 --> COMP-19
    COMP-37 --> COMP-48
    COMP-43 --> COMP-30
    COMP-31 --> COMP-45
    COMP-34 --> COMP-53
    COMP-24 --> COMP-12
    COMP-39 --> COMP-54
    COMP-57 --> COMP-54
    COMP-27 --> COMP-32
    COMP-34 --> COMP-50
    COMP-12 --> COMP-54
    COMP-15 --> COMP-24
    COMP-31 --> COMP-27
    COMP-15 --> COMP-22
    COMP-59 --> COMP-56
    COMP-33 --> COMP-35
    COMP-26 --> COMP-14
    COMP-25 --> COMP-35
    COMP-7 --> COMP-38
    COMP-45 --> COMP-41
    COMP-15 --> COMP-21
    COMP-19 --> COMP-17
    COMP-10 --> COMP-43
    COMP-39 --> COMP-47
    COMP-50 --> COMP-31
    COMP-12 --> COMP-25
    COMP-5 --> COMP-62
    COMP-28 --> COMP-27
    COMP-57 --> COMP-58
    COMP-10 --> COMP-30
    COMP-6 --> COMP-45
    COMP-14 --> COMP-23
    COMP-27 --> COMP-49
    COMP-27 --> COMP-30
    COMP-6 --> COMP-28
    COMP-27 --> COMP-39
    COMP-12 --> COMP-14
    COMP-6 --> COMP-52
    COMP-56 --> COMP-31
    COMP-58 --> COMP-19
    COMP-48 --> COMP-60
    COMP-55 --> COMP-43
    COMP-46 --> COMP-29
    COMP-6 --> COMP-36
    COMP-24 --> COMP-55
    COMP-6 --> COMP-9
    COMP-54 --> COMP-45
    COMP-44 --> COMP-60
    COMP-54 --> COMP-28
    COMP-39 --> COMP-46
    COMP-19 --> COMP-20
    COMP-59 --> COMP-62
    COMP-54 --> COMP-52
    COMP-5 --> COMP-52
    COMP-5 --> COMP-54
    COMP-11 --> COMP-32
    COMP-41 --> COMP-34
    COMP-36 --> COMP-29
    COMP-6 --> COMP-47
    COMP-52 --> COMP-31
    COMP-27 --> COMP-18
    COMP-29 --> COMP-56
    COMP-10 --> COMP-35
    COMP-6 --> COMP-8
    COMP-46 --> COMP-27
    COMP-58 --> COMP-41
    COMP-54 --> COMP-36
    COMP-6 --> COMP-13
    COMP-50 --> COMP-44
    COMP-4 --> COMP-9
    COMP-24 --> COMP-5
    COMP-55 --> COMP-35
    COMP-55 --> COMP-10
    COMP-33 --> COMP-42
    COMP-36 --> COMP-27
    COMP-54 --> COMP-47
    COMP-5 --> COMP-58
    COMP-37 --> COMP-34
    COMP-59 --> COMP-54
    COMP-10 --> COMP-57
    COMP-5 --> COMP-8
    COMP-19 --> COMP-2
    COMP-4 --> COMP-8
    COMP-11 --> COMP-30
    COMP-54 --> COMP-13
    COMP-6 --> COMP-46
    COMP-33 --> COMP-62
    COMP-16 --> COMP-26
    COMP-18 --> COMP-2
    COMP-49 --> COMP-28
    COMP-49 --> COMP-52
    COMP-55 --> COMP-57
    COMP-31 --> COMP-60
    COMP-6 --> COMP-59
    COMP-29 --> COMP-62
    COMP-54 --> COMP-46
    COMP-59 --> COMP-47
    COMP-49 --> COMP-36
    COMP-43 --> COMP-29
    COMP-17 --> COMP-60
    COMP-3 --> COMP-9
    COMP-33 --> COMP-52
    COMP-33 --> COMP-54
    COMP-24 --> COMP-23
    COMP-25 --> COMP-28
    COMP-50 --> COMP-32
    COMP-28 --> COMP-60
    COMP-19 --> COMP-7
    COMP-25 --> COMP-52
    COMP-54 --> COMP-59
    COMP-10 --> COMP-42
    COMP-39 --> COMP-50
    COMP-43 --> COMP-28
    COMP-5 --> COMP-3
    COMP-56 --> COMP-32
    COMP-34 --> COMP-19
    COMP-29 --> COMP-54
    COMP-25 --> COMP-36
    COMP-59 --> COMP-46
    COMP-55 --> COMP-42
    COMP-25 --> COMP-47
    COMP-47 --> COMP-48
    COMP-55 --> COMP-62
    COMP-25 --> COMP-15
    COMP-27 --> COMP-29
    COMP-6 --> COMP-53
    COMP-52 --> COMP-32
    COMP-25 --> COMP-13
    COMP-46 --> COMP-60
    COMP-53 --> COMP-34
    COMP-7 --> COMP-55
    COMP-19 --> COMP-31
    COMP-56 --> COMP-30
    COMP-6 --> COMP-50
    COMP-22 --> COMP-29
    COMP-34 --> COMP-41
    COMP-19 --> COMP-6
    COMP-24 --> COMP-30
    COMP-10 --> COMP-28
    COMP-27 --> COMP-45
    COMP-27 --> COMP-28
    COMP-10 --> COMP-52
    COMP-39 --> COMP-48
    COMP-28 --> COMP-48
    COMP-18 --> COMP-31
    COMP-18 --> COMP-6
    COMP-38 --> COMP-62
    COMP-36 --> COMP-60
    COMP-48 --> COMP-34
    COMP-3 --> COMP-59
    COMP-54 --> COMP-53
    COMP-10 --> COMP-36
    COMP-55 --> COMP-52
    COMP-37 --> COMP-44
    COMP-55 --> COMP-54
    COMP-54 --> COMP-50
    COMP-22 --> COMP-27
    COMP-5 --> COMP-50
    COMP-2 --> COMP-9
    COMP-25 --> COMP-24
    COMP-45 --> COMP-37
    COMP-25 --> COMP-22
    COMP-16 --> COMP-14
    COMP-10 --> COMP-47
    COMP-55 --> COMP-36
    COMP-6 --> COMP-38
    COMP-2 --> COMP-8
    COMP-20 --> COMP-55
    COMP-19 --> COMP-5
    COMP-43 --> COMP-59
    COMP-10 --> COMP-13
    COMP-25 --> COMP-21
    COMP-38 --> COMP-52
    COMP-38 --> COMP-54
    COMP-3 --> COMP-60
    COMP-55 --> COMP-47
    COMP-55 --> COMP-58
    COMP-35 --> COMP-29
    COMP-12 --> COMP-20
    COMP-55 --> COMP-8
    COMP-11 --> COMP-29
    COMP-45 --> COMP-33
    COMP-55 --> COMP-13
    COMP-45 --> COMP-56
    COMP-54 --> COMP-38
    COMP-49 --> COMP-53
    COMP-8 --> COMP-56
    COMP-11 --> COMP-45
    COMP-10 --> COMP-46
    COMP-48 --> COMP-31
    COMP-35 --> COMP-27
    COMP-24 --> COMP-26
    COMP-55 --> COMP-46
    COMP-16 --> COMP-21
    COMP-11 --> COMP-9
    COMP-44 --> COMP-31
    COMP-47 --> COMP-34
    COMP-19 --> COMP-23
    COMP-14 --> COMP-13
    COMP-25 --> COMP-53
    COMP-33 --> COMP-50
    COMP-59 --> COMP-48
    COMP-25 --> COMP-50
    COMP-43 --> COMP-53
    COMP-41 --> COMP-37
    COMP-55 --> COMP-3
    COMP-19 --> COMP-32
    COMP-49 --> COMP-38
    COMP-39 --> COMP-34
    COMP-45 --> COMP-62
    COMP-28 --> COMP-34
    COMP-58 --> COMP-56
    COMP-37 --> COMP-39
    COMP-18 --> COMP-32
    COMP-19 --> COMP-16
    COMP-17 --> COMP-12
    COMP-7 --> COMP-43
    COMP-50 --> COMP-29
    COMP-18 --> COMP-16
    COMP-22 --> COMP-60
    COMP-19 --> COMP-43
    COMP-50 --> COMP-45
    COMP-25 --> COMP-38
    COMP-10 --> COMP-53
    COMP-19 --> COMP-30
    COMP-19 --> COMP-39
    COMP-45 --> COMP-54
    COMP-27 --> COMP-53
    COMP-37 --> COMP-18
    COMP-6 --> COMP-19
    COMP-10 --> COMP-50
    COMP-50 --> COMP-27
    COMP-47 --> COMP-31
    COMP-56 --> COMP-28
    COMP-24 --> COMP-28
    COMP-24 --> COMP-52
    COMP-31 --> COMP-55
    COMP-55 --> COMP-50
    COMP-53 --> COMP-32
    COMP-7 --> COMP-35
    COMP-52 --> COMP-29
    COMP-7 --> COMP-10
    COMP-54 --> COMP-19
    COMP-28 --> COMP-31
    COMP-5 --> COMP-19
    COMP-19 --> COMP-18
    COMP-12 --> COMP-31
    COMP-12 --> COMP-6
    COMP-17 --> COMP-55
    COMP-6 --> COMP-41
    COMP-35 --> COMP-60
    COMP-48 --> COMP-32
    COMP-34 --> COMP-37
    COMP-38 --> COMP-50
    COMP-24 --> COMP-8
    COMP-27 --> COMP-38
    COMP-7 --> COMP-57
    COMP-24 --> COMP-13
    COMP-23 --> COMP-60
    COMP-44 --> COMP-32
    COMP-53 --> COMP-39
    COMP-47 --> COMP-44
    COMP-54 --> COMP-41
    COMP-5 --> COMP-41
    COMP-11 --> COMP-53
    COMP-13 --> COMP-60
    COMP-46 --> COMP-31
    COMP-48 --> COMP-39
    COMP-34 --> COMP-33
    COMP-24 --> COMP-46
    COMP-49 --> COMP-19
    COMP-54 --> COMP-55
    COMP-3 --> COMP-7
    COMP-34 --> COMP-56
    COMP-28 --> COMP-44
    COMP-50 --> COMP-59
    COMP-58 --> COMP-27
    COMP-41 --> COMP-29
    COMP-36 --> COMP-31
    COMP-24 --> COMP-22
    COMP-53 --> COMP-18
    COMP-8 --> COMP-3
    COMP-7 --> COMP-42
    COMP-33 --> COMP-19
    COMP-24 --> COMP-3
    COMP-24 --> COMP-21
    COMP-41 --> COMP-27
    COMP-42 --> COMP-37
    COMP-25 --> COMP-19
    COMP-48 --> COMP-18
    COMP-8 --> COMP-4
    COMP-49 --> COMP-41
    COMP-7 --> COMP-62
    COMP-37 --> COMP-29
    COMP-6 --> COMP-11
    COMP-50 --> COMP-60
    COMP-22 --> COMP-2
    COMP-47 --> COMP-32
    COMP-17 --> COMP-23
    COMP-49 --> COMP-55
    COMP-34 --> COMP-62
    COMP-26 --> COMP-16
    COMP-37 --> COMP-27
    COMP-33 --> COMP-41
    COMP-3 --> COMP-55
    COMP-54 --> COMP-11
    COMP-5 --> COMP-11
    COMP-28 --> COMP-32
    COMP-4 --> COMP-11
    COMP-25 --> COMP-41
    COMP-7 --> COMP-52
    COMP-12 --> COMP-32
    COMP-7 --> COMP-54
    COMP-31 --> COMP-30
    COMP-18 --> COMP-29
    COMP-47 --> COMP-39
    COMP-56 --> COMP-53
    COMP-24 --> COMP-53
    COMP-19 --> COMP-28
    COMP-12 --> COMP-16
    COMP-10 --> COMP-19
    COMP-25 --> COMP-55
    COMP-7 --> COMP-36
    COMP-19 --> COMP-52
    COMP-24 --> COMP-50
    COMP-22 --> COMP-7
    COMP-34 --> COMP-54
    COMP-43 --> COMP-55
    COMP-18 --> COMP-25
    COMP-3 --> COMP-5
    COMP-15 --> COMP-26
    COMP-28 --> COMP-49
    COMP-19 --> COMP-36
    COMP-55 --> COMP-19
    COMP-18 --> COMP-27
    COMP-28 --> COMP-30
    COMP-28 --> COMP-39
    COMP-59 --> COMP-44
    COMP-7 --> COMP-58
    COMP-60 --> COMP-55
    COMP-7 --> COMP-8
    COMP-46 --> COMP-32
    COMP-7 --> COMP-13
    COMP-47 --> COMP-18
    COMP-39 --> COMP-37
    COMP-10 --> COMP-41
    COMP-19 --> COMP-8
    COMP-58 --> COMP-60
    COMP-19 --> COMP-15
    COMP-34 --> COMP-27
    COMP-38 --> COMP-19
    COMP-36 --> COMP-32
    COMP-53 --> COMP-29
    COMP-22 --> COMP-31
    COMP-55 --> COMP-41
    COMP-22 --> COMP-6
    COMP-28 --> COMP-18
    COMP-27 --> COMP-55
    COMP-46 --> COMP-43
    COMP-12 --> COMP-18
    COMP-41 --> COMP-60
    COMP-46 --> COMP-49
    COMP-46 --> COMP-30
    COMP-48 --> COMP-29
    COMP-53 --> COMP-27
    COMP-19 --> COMP-24
    COMP-6 --> COMP-10
    COMP-36 --> COMP-43
    COMP-6 --> COMP-37
    COMP-38 --> COMP-41
    COMP-36 --> COMP-49
    COMP-7 --> COMP-3
    COMP-44 --> COMP-29
    COMP-36 --> COMP-30
    COMP-37 --> COMP-60
    COMP-22 --> COMP-5
    COMP-46 --> COMP-18
    COMP-17 --> COMP-26
    COMP-54 --> COMP-10
    COMP-54 --> COMP-37
    COMP-46 --> COMP-35
    COMP-35 --> COMP-31
    COMP-6 --> COMP-33
    COMP-6 --> COMP-56
    COMP-10 --> COMP-11
    COMP-36 --> COMP-18
    COMP-34 --> COMP-4
    COMP-36 --> COMP-35
    COMP-54 --> COMP-57
    COMP-11 --> COMP-55
    COMP-20 --> COMP-3
    COMP-15 --> COMP-14
    COMP-18 --> COMP-60
    COMP-54 --> COMP-33
    COMP-55 --> COMP-11
    COMP-54 --> COMP-56
    COMP-5 --> COMP-56
    COMP-4 --> COMP-56
    COMP-7 --> COMP-50
    COMP-20 --> COMP-4
    COMP-29 --> COMP-32
    COMP-47 --> COMP-29
    COMP-19 --> COMP-53
    COMP-45 --> COMP-34
    COMP-49 --> COMP-35
    COMP-6 --> COMP-42
    COMP-31 --> COMP-28
    COMP-47 --> COMP-45
    COMP-31 --> COMP-52
    COMP-3 --> COMP-10
    COMP-56 --> COMP-19
    COMP-24 --> COMP-19
    COMP-6 --> COMP-62
    COMP-39 --> COMP-29
    COMP-26 --> COMP-25
    COMP-28 --> COMP-29
    COMP-57 --> COMP-29
    COMP-22 --> COMP-32
    COMP-47 --> COMP-27
    COMP-12 --> COMP-29
    COMP-54 --> COMP-42
    COMP-28 --> COMP-45
    COMP-33 --> COMP-37
    COMP-22 --> COMP-16
    COMP-3 --> COMP-57
    COMP-53 --> COMP-60
    COMP-25 --> COMP-37
    COMP-49 --> COMP-56
    COMP-54 --> COMP-62
    COMP-39 --> COMP-27
    COMP-4 --> COMP-62
    COMP-43 --> COMP-10
    COMP-27 --> COMP-43
    COMP-57 --> COMP-27
    COMP-18 --> COMP-17
    COMP-12 --> COMP-27
    COMP-19 --> COMP-38
    COMP-56 --> COMP-41
    COMP-24 --> COMP-41
    COMP-31 --> COMP-13
    COMP-6 --> COMP-54
    COMP-50 --> COMP-55
    COMP-22 --> COMP-30
    COMP-45 --> COMP-31
    COMP-33 --> COMP-56
    COMP-43 --> COMP-57
    COMP-56 --> COMP-55
    COMP-17 --> COMP-15
    COMP-25 --> COMP-33
    COMP-25 --> COMP-56
    COMP-8 --> COMP-6
    COMP-17 --> COMP-13
    COMP-35 --> COMP-32
    COMP-46 --> COMP-45
    COMP-4 --> COMP-54
    COMP-12 --> COMP-15
    COMP-25 --> COMP-26
    COMP-46 --> COMP-28
    COMP-49 --> COMP-42
    COMP-46 --> COMP-52
    COMP-6 --> COMP-58
    COMP-27 --> COMP-35
    COMP-10 --> COMP-37
    COMP-49 --> COMP-62
    COMP-36 --> COMP-45
    COMP-36 --> COMP-28
    COMP-46 --> COMP-36
    COMP-52 --> COMP-55
    COMP-36 --> COMP-52
    COMP-17 --> COMP-24
    COMP-55 --> COMP-37
    COMP-54 --> COMP-58
    COMP-17 --> COMP-22
    COMP-5 --> COMP-27
    COMP-4 --> COMP-58
    COMP-25 --> COMP-42
    COMP-35 --> COMP-30
    COMP-58 --> COMP-31
    COMP-59 --> COMP-29
    COMP-10 --> COMP-33
    COMP-28 --> COMP-59
    COMP-10 --> COMP-56
    COMP-25 --> COMP-62
    COMP-2 --> COMP-56
    COMP-17 --> COMP-21
    COMP-49 --> COMP-54
    COMP-48 --> COMP-38
    COMP-43 --> COMP-62
    COMP-47 --> COMP-60
    COMP-55 --> COMP-33
    COMP-55 --> COMP-56
    COMP-26 --> COMP-60
    COMP-34 --> COMP-2
    COMP-59 --> COMP-27
    COMP-41 --> COMP-31
    COMP-6 --> COMP-3
    COMP-7 --> COMP-19
    COMP-39 --> COMP-60
    COMP-31 --> COMP-53
    COMP-57 --> COMP-60
    COMP-19 --> COMP-12
    COMP-25 --> COMP-54
    COMP-6 --> COMP-4
    COMP-12 --> COMP-60
    COMP-31 --> COMP-50
    COMP-27 --> COMP-42
    COMP-38 --> COMP-56
    COMP-43 --> COMP-52
    COMP-43 --> COMP-54
    COMP-18 --> COMP-12
    COMP-18 --> COMP-7
    COMP-4 --> COMP-3
    COMP-3 --> COMP-8
    COMP-37 --> COMP-31
    COMP-10 --> COMP-62
    COMP-3 --> COMP-13
    COMP-27 --> COMP-62
    COMP-45 --> COMP-32
    COMP-28 --> COMP-53
    COMP-33 --> COMP-27
    COMP-7 --> COMP-41
    COMP-5 --> COMP-4
    COMP-34 --> COMP-7
    COMP-50 --> COMP-49
    COMP-50 --> COMP-30
    COMP-25 --> COMP-14
    COMP-43 --> COMP-58
    COMP-19 --> COMP-41
    COMP-26 --> COMP-17
    COMP-29 --> COMP-27
    COMP-43 --> COMP-13
    COMP-60 --> COMP-47
    COMP-47 --> COMP-38
    COMP-10 --> COMP-54
    COMP-27 --> COMP-52
    COMP-27 --> COMP-54
    COMP-22 --> COMP-45
    COMP-45 --> COMP-39
    COMP-19 --> COMP-55
    COMP-22 --> COMP-28
    COMP-22 --> COMP-52
    COMP-5 --> COMP-60
    COMP-16 --> COMP-25
    COMP-12 --> COMP-17
    COMP-18 --> COMP-55
    COMP-46 --> COMP-53
    COMP-27 --> COMP-36
    COMP-28 --> COMP-38
    COMP-50 --> COMP-10
    COMP-46 --> COMP-50
    COMP-52 --> COMP-30
    COMP-58 --> COMP-32
    COMP-34 --> COMP-31
    COMP-34 --> COMP-6
    COMP-10 --> COMP-58
    COMP-10 --> COMP-27
    COMP-27 --> COMP-47
    COMP-36 --> COMP-53
    COMP-11 --> COMP-62
    COMP-36 --> COMP-50
    COMP-45 --> COMP-18
    COMP-6 --> COMP-48
    COMP-27 --> COMP-13
    COMP-59 --> COMP-60
    COMP-22 --> COMP-8
    COMP-50 --> COMP-57
    COMP-18 --> COMP-5
    COMP-41 --> COMP-32
    COMP-55 --> COMP-27
    COMP-53 --> COMP-31
    COMP-58 --> COMP-30
    COMP-35 --> COMP-28
    COMP-46 --> COMP-38
    COMP-11 --> COMP-28
    COMP-54 --> COMP-48
    COMP-35 --> COMP-52
    COMP-27 --> COMP-46
    COMP-53 --> COMP-55
    COMP-49 --> COMP-50
    COMP-11 --> COMP-52
    COMP-11 --> COMP-54
    COMP-24 --> COMP-56
    COMP-38 --> COMP-27
    COMP-14 --> COMP-25
    COMP-37 --> COMP-32
    COMP-41 --> COMP-43
    COMP-36 --> COMP-38
    COMP-41 --> COMP-30
    COMP-41 --> COMP-39
    COMP-48 --> COMP-55
    COMP-6 --> COMP-20
    COMP-33 --> COMP-60
    COMP-2 --> COMP-3
    COMP-44 --> COMP-55
    COMP-18 --> COMP-23
    COMP-29 --> COMP-60
    COMP-43 --> COMP-50
    COMP-37 --> COMP-43
    COMP-31 --> COMP-19
    COMP-2 --> COMP-4
    COMP-26 --> COMP-12
    COMP-37 --> COMP-49
    COMP-37 --> COMP-30
    COMP-41 --> COMP-18
    COMP-41 --> COMP-35
    COMP-56 --> COMP-62
    COMP-24 --> COMP-62
    COMP-55 --> COMP-4
    COMP-11 --> COMP-46
    COMP-16 --> COMP-60
    COMP-34 --> COMP-32
    COMP-50 --> COMP-28
    COMP-31 --> COMP-41
    COMP-50 --> COMP-52
    COMP-5 --> COMP-2
    COMP-4 --> COMP-2
    COMP-35 --> COMP-59
    COMP-6 --> COMP-34
    COMP-45 --> COMP-29
    COMP-18 --> COMP-30
    COMP-52 --> COMP-62
    COMP-37 --> COMP-35
    COMP-27 --> COMP-50
    COMP-22 --> COMP-53
    COMP-56 --> COMP-52
    COMP-56 --> COMP-54
    COMP-50 --> COMP-36
    COMP-24 --> COMP-54
    COMP-50 --> COMP-9
    COMP-55 --> COMP-60
    COMP-47 --> COMP-55
    COMP-26 --> COMP-55
    COMP-39 --> COMP-31
    COMP-57 --> COMP-31
    COMP-7 --> COMP-37
    COMP-50 --> COMP-47
    COMP-34 --> COMP-39
    COMP-54 --> COMP-34
    COMP-45 --> COMP-27
    COMP-46 --> COMP-19
    COMP-24 --> COMP-25
    COMP-19 --> COMP-35
    COMP-52 --> COMP-28
    COMP-28 --> COMP-55
    COMP-38 --> COMP-60
    COMP-52 --> COMP-54
    COMP-24 --> COMP-27
    COMP-12 --> COMP-55
    COMP-5 --> COMP-7
    COMP-24 --> COMP-14
    COMP-36 --> COMP-19
    COMP-16 --> COMP-17
    COMP-10 --> COMP-48
    COMP-53 --> COMP-43
    COMP-7 --> COMP-33
    COMP-53 --> COMP-30
    COMP-58 --> COMP-29
    COMP-7 --> COMP-56
    COMP-50 --> COMP-46
    COMP-34 --> COMP-18
    COMP-35 --> COMP-53
    COMP-46 --> COMP-41
    COMP-55 --> COMP-48
    COMP-48 --> COMP-43
    COMP-35 --> COMP-50
    COMP-58 --> COMP-28
    COMP-11 --> COMP-50
    COMP-19 --> COMP-56
    COMP-48 --> COMP-30
    COMP-49 --> COMP-34
    COMP-39 --> COMP-44
    COMP-19 --> COMP-26
    COMP-36 --> COMP-41
    COMP-46 --> COMP-55
    COMP-15 --> COMP-16
    COMP-18 --> COMP-26
    COMP-44 --> COMP-30
    COMP-5 --> COMP-31
    COMP-5 --> COMP-6
    COMP-4 --> COMP-6
    COMP-41 --> COMP-28
    COMP-53 --> COMP-35
    COMP-41 --> COMP-52
    COMP-36 --> COMP-55
    COMP-33 --> COMP-34
    COMP-26 --> COMP-23
    COMP-25 --> COMP-34
    COMP-19 --> COMP-42
    COMP-55 --> COMP-20
    COMP-41 --> COMP-36
    COMP-48 --> COMP-35
    COMP-43 --> COMP-19
    COMP-6 --> COMP-44
    COMP-24 --> COMP-4
    COMP-53 --> COMP-57
    COMP-37 --> COMP-45
    COMP-59 --> COMP-31
    COMP-19 --> COMP-62
    COMP-37 --> COMP-28
    COMP-12 --> COMP-23
    COMP-37 --> COMP-52
    COMP-39 --> COMP-32
    COMP-41 --> COMP-13
    COMP-57 --> COMP-32
    COMP-45 --> COMP-60
    COMP-50 --> COMP-53
    COMP-54 --> COMP-44
    COMP-37 --> COMP-36
    COMP-46 --> COMP-11
    COMP-8 --> COMP-60
    COMP-55 --> COMP-2
    COMP-47 --> COMP-43
    COMP-43 --> COMP-41
    COMP-47 --> COMP-49
    COMP-47 --> COMP-30
    COMP-58 --> COMP-59
    COMP-37 --> COMP-47
    COMP-10 --> COMP-34
    COMP-19 --> COMP-54
    COMP-27 --> COMP-19
    COMP-36 --> COMP-11
    COMP-56 --> COMP-50
    COMP-18 --> COMP-28
    COMP-33 --> COMP-31
    COMP-18 --> COMP-52
    COMP-39 --> COMP-43
    COMP-28 --> COMP-43
    COMP-22 --> COMP-19
    COMP-39 --> COMP-49
    COMP-34 --> COMP-29
    COMP-39 --> COMP-30
    COMP-57 --> COMP-30
    COMP-55 --> COMP-34
    COMP-7 --> COMP-27
    COMP-6 --> COMP-32
    COMP-12 --> COMP-30
    COMP-52 --> COMP-53
    COMP-34 --> COMP-45
    COMP-29 --> COMP-31
    COMP-48 --> COMP-42
    COMP-52 --> COMP-50
    COMP-37 --> COMP-46
    COMP-47 --> COMP-35
    COMP-19 --> COMP-14
    COMP-55 --> COMP-7
    COMP-27 --> COMP-41
    COMP-3 --> COMP-11
    COMP-29 --> COMP-55
    COMP-19 --> COMP-13
    COMP-18 --> COMP-8
    COMP-48 --> COMP-62
    COMP-18 --> COMP-15
    COMP-5 --> COMP-32
    COMP-22 --> COMP-41
    COMP-18 --> COMP-13
    COMP-39 --> COMP-18
    COMP-24 --> COMP-48
    COMP-45 --> COMP-38
    COMP-28 --> COMP-35
    COMP-28 --> COMP-10
    COMP-6 --> COMP-39
    COMP-53 --> COMP-28
    COMP-44 --> COMP-62
    COMP-58 --> COMP-53
    COMP-53 --> COMP-52
    COMP-22 --> COMP-55
    COMP-10 --> COMP-31
    COMP-35 --> COMP-19
    COMP-2 --> COMP-6
    COMP-31 --> COMP-56
    COMP-11 --> COMP-19
    COMP-48 --> COMP-28
    COMP-53 --> COMP-36
    COMP-19 --> COMP-22
    COMP-48 --> COMP-52
    COMP-48 --> COMP-54
    COMP-59 --> COMP-32
    COMP-54 --> COMP-39
    COMP-18 --> COMP-24
    COMP-55 --> COMP-31
    COMP-5 --> COMP-30
    COMP-28 --> COMP-57
    COMP-55 --> COMP-6
    COMP-41 --> COMP-53
    COMP-18 --> COMP-22
    COMP-44 --> COMP-28
    COMP-19 --> COMP-3
    COMP-41 --> COMP-50
    COMP-53 --> COMP-47
    COMP-6 --> COMP-18
    COMP-19 --> COMP-21
    COMP-48 --> COMP-36
    COMP-44 --> COMP-52
    COMP-44 --> COMP-54
    COMP-7 --> COMP-4
    COMP-24 --> COMP-20
    COMP-30 --> COMP-55
    COMP-35 --> COMP-41
    COMP-18 --> COMP-3
    COMP-53 --> COMP-13
    COMP-18 --> COMP-21
    COMP-11 --> COMP-41
    COMP-46 --> COMP-37
    COMP-12 --> COMP-26
    COMP-38 --> COMP-31
    COMP-59 --> COMP-49
    COMP-15 --> COMP-25
    COMP-37 --> COMP-53
    COMP-59 --> COMP-30
    COMP-54 --> COMP-18
    COMP-27 --> COMP-11
    COMP-35 --> COMP-55
    COMP-10 --> COMP-44
    COMP-31 --> COMP-62
    COMP-8 --> COMP-2
    COMP-33 --> COMP-32
    COMP-36 --> COMP-37
    COMP-37 --> COMP-50
    COMP-55 --> COMP-5
    COMP-28 --> COMP-42
    COMP-7 --> COMP-60
    COMP-41 --> COMP-38
    COMP-24 --> COMP-2
    COMP-23 --> COMP-55
    COMP-55 --> COMP-44
    COMP-46 --> COMP-33
    COMP-46 --> COMP-56
    COMP-25 --> COMP-16
    COMP-50 --> COMP-19
    COMP-28 --> COMP-62
    COMP-13 --> COMP-55
    COMP-49 --> COMP-37
    COMP-34 --> COMP-60
    COMP-19 --> COMP-50
    COMP-36 --> COMP-33
    COMP-16 --> COMP-23
    COMP-18 --> COMP-53
    COMP-47 --> COMP-28
    COMP-36 --> COMP-56
    COMP-31 --> COMP-54
    COMP-33 --> COMP-30
    COMP-33 --> COMP-39
    COMP-47 --> COMP-52
    COMP-18 --> COMP-50
    COMP-37 --> COMP-38
    COMP-25 --> COMP-39
    COMP-8 --> COMP-7
    COMP-47 --> COMP-36
    COMP-39 --> COMP-45
    COMP-39 --> COMP-28
    COMP-46 --> COMP-42
    COMP-29 --> COMP-30
    COMP-20 --> COMP-60
    COMP-57 --> COMP-28
    COMP-10 --> COMP-32
    COMP-24 --> COMP-7
    COMP-50 --> COMP-41
    COMP-39 --> COMP-52
    COMP-28 --> COMP-52
    COMP-49 --> COMP-33
    COMP-28 --> COMP-54
    COMP-57 --> COMP-52
    COMP-12 --> COMP-28
    COMP-12 --> COMP-52
    COMP-52 --> COMP-19
    COMP-46 --> COMP-62
    COMP-3 --> COMP-56
    COMP-33 --> COMP-18
    COMP-36 --> COMP-42
    COMP-39 --> COMP-36
    COMP-28 --> COMP-36
    COMP-55 --> COMP-32
    COMP-39 --> COMP-9
    COMP-25 --> COMP-18
    COMP-26 --> COMP-15
    COMP-17 --> COMP-25
    COMP-6 --> COMP-29
    COMP-26 --> COMP-13
    COMP-36 --> COMP-62
    COMP-28 --> COMP-47
    COMP-17 --> COMP-14
    COMP-28 --> COMP-58
    COMP-53 --> COMP-50
    COMP-10 --> COMP-49
    COMP-10 --> COMP-39
    COMP-39 --> COMP-13
    COMP-28 --> COMP-13
    COMP-57 --> COMP-13
    COMP-38 --> COMP-32
    COMP-43 --> COMP-56
    COMP-45 --> COMP-55
    COMP-52 --> COMP-41
    COMP-47 --> COMP-46
    COMP-48 --> COMP-53
    COMP-34 --> COMP-38
    COMP-24 --> COMP-31
    COMP-46 --> COMP-54
    COMP-24 --> COMP-6
    COMP-12 --> COMP-13
    COMP-8 --> COMP-55
    COMP-6 --> COMP-27
    COMP-54 --> COMP-29
    COMP-5 --> COMP-29
    COMP-55 --> COMP-49
    COMP-48 --> COMP-50
    COMP-55 --> COMP-30
    COMP-55 --> COMP-39
    COMP-15 --> COMP-60
    COMP-27 --> COMP-37
    COMP-26 --> COMP-24
```
