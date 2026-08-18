---
document: Logical Architecture
system: Projects (views)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:32Z
generator_version: 0.3.0
model_hash: a4f321da275c
edition: 3
---

# Logical Architecture: Projects (views)

## Layer Structure

| Order | Layer | Technologies | Directories |
|-------|-------|-------------|-------------|
| 0 | web | — | — |
| 0 | infra | — | — |

## Component Allocation

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Csrf (COMP-15) | service | 4 files | — |
| Debug (COMP-16) | service | 2 files | — |
| Cache (COMP-17) | service | 1 files | — |
| Clickjacking (COMP-18) | service | 1 files | — |
| Csp (COMP-19) | service | 1 files | — |
| Http (COMP-20) | service | 1 files | — |
| Vary (COMP-21) | service | 1 files | — |
| Defaults (COMP-22) | service | 1 files | — |
| Dates (COMP-23) | service | 1 files | — |
| Detail (COMP-24) | service | 1 files | — |
| Edit (COMP-25) | service | 1 files | — |
| List (COMP-26) | service | 1 files | — |
| I18N (COMP-27) | service | 1 files | — |
| Static (COMP-28) | service | 1 files | — |
| Infrastructure (COMP-29) | service | 1 files | — |

## Inter-Component Interfaces

*No interfaces defined.*

## Dependency Graph

```mermaid
graph TD
    COMP-15["Csrf"]
    COMP-18["Clickjacking"]
    COMP-15 --> COMP-18
    COMP-20["Http"]
    COMP-17["Cache"]
    COMP-20 --> COMP-17
    COMP-26["List"]
    COMP-22["Defaults"]
    COMP-26 --> COMP-22
    COMP-16["Debug"]
    COMP-16 --> COMP-18
    COMP-28["Static"]
    COMP-16 --> COMP-28
    COMP-22 --> COMP-15
    COMP-24["Detail"]
    COMP-24 --> COMP-26
    COMP-21["Vary"]
    COMP-15 --> COMP-21
    COMP-23["Dates"]
    COMP-25["Edit"]
    COMP-23 --> COMP-25
    COMP-27["I18N"]
    COMP-27 --> COMP-26
    COMP-16 --> COMP-21
    COMP-20 --> COMP-16
    COMP-23 --> COMP-27
    COMP-20 --> COMP-15
    COMP-24 --> COMP-25
    COMP-27 --> COMP-25
    COMP-26 --> COMP-25
    COMP-23 --> COMP-24
    COMP-23 --> COMP-22
    COMP-24 --> COMP-27
    COMP-25 --> COMP-20
    COMP-19["Csp"]
    COMP-22 --> COMP-19
    COMP-26 --> COMP-27
    COMP-25 --> COMP-16
    COMP-16 --> COMP-17
    COMP-22 --> COMP-16
    COMP-27 --> COMP-24
    COMP-16 --> COMP-20
    COMP-25 --> COMP-15
    COMP-25 --> COMP-23
    COMP-24 --> COMP-22
    COMP-20 --> COMP-19
    COMP-27 --> COMP-22
    COMP-16 --> COMP-15
    COMP-29["Infrastructure"]
    COMP-22 --> COMP-29
    COMP-27 --> COMP-28
    COMP-26 --> COMP-28
    COMP-20 --> COMP-29
    COMP-17 --> COMP-20
    COMP-15 --> COMP-17
    COMP-17 --> COMP-16
    COMP-16 --> COMP-19
    COMP-15 --> COMP-20
    COMP-17 --> COMP-15
    COMP-15 --> COMP-16
    COMP-22 --> COMP-27
    COMP-23 --> COMP-28
    COMP-25 --> COMP-24
    COMP-25 --> COMP-22
    COMP-23 --> COMP-15
    COMP-25 --> COMP-26
    COMP-26 --> COMP-20
    COMP-24 --> COMP-28
    COMP-16 --> COMP-29
    COMP-16 --> COMP-22
    COMP-26 --> COMP-16
    COMP-24 --> COMP-15
    COMP-17 --> COMP-19
    COMP-27 --> COMP-15
    COMP-26 --> COMP-15
    COMP-26 --> COMP-23
    COMP-27 --> COMP-23
    COMP-22 --> COMP-18
    COMP-22 --> COMP-28
    COMP-15 --> COMP-19
    COMP-22 --> COMP-21
    COMP-28 --> COMP-20
    COMP-25 --> COMP-27
    COMP-21 --> COMP-17
    COMP-23 --> COMP-20
    COMP-20 --> COMP-18
    COMP-23 --> COMP-16
    COMP-20 --> COMP-21
    COMP-16 --> COMP-27
    COMP-17 --> COMP-29
    COMP-24 --> COMP-20
    COMP-27 --> COMP-20
    COMP-15 --> COMP-29
    COMP-24 --> COMP-16
    COMP-27 --> COMP-16
    COMP-22 --> COMP-17
    COMP-23 --> COMP-26
    COMP-24 --> COMP-23
    COMP-22 --> COMP-20
    COMP-17 --> COMP-18
    COMP-25 --> COMP-28
    COMP-17 --> COMP-21
    COMP-26 --> COMP-24
```
