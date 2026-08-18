---
document: Logical Architecture
system: Projects (template)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:30Z
generator_version: 0.3.0
model_hash: 7f71c642a524
edition: 3
---

# Logical Architecture: Projects (template)

## Layer Structure

| Order | Layer | Technologies | Directories |
|-------|-------|-------------|-------------|
| 0 | infra | — | — |

## Component Allocation

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Autoreload (COMP-15) | service | 1 files | — |
| Django (COMP-16) | service | 6 files | — |
| Dummy (COMP-17) | service | 1 files | — |
| Jinja2 (COMP-18) | service | 1 files | — |
| Context (COMP-19) | service | 2 files | — |
| Defaultfilters (COMP-21) | service | 1 files | — |
| Defaulttags (COMP-22) | service | 1 files | — |
| Engine (COMP-23) | service | 1 files | — |
| Exceptions (COMP-24) | service | 1 files | — |
| Library (COMP-25) | service | 1 files | — |
| Loader (COMP-26) | service | 2 files | — |
| App Directories (COMP-28) | service | 1 files | — |
| Cached (COMP-29) | service | 1 files | — |
| Filesystem (COMP-30) | service | 1 files | — |
| Locmem (COMP-31) | service | 1 files | — |
| Response (COMP-32) | service | 1 files | — |
| Smartif (COMP-33) | service | 1 files | — |

## Inter-Component Interfaces

*No interfaces defined.*

## Dependency Graph

```mermaid
graph TD
    COMP-28["App Directories"]
    COMP-25["Library"]
    COMP-28 --> COMP-25
    COMP-15["Autoreload"]
    COMP-18["Jinja2"]
    COMP-15 --> COMP-18
    COMP-29["Cached"]
    COMP-17["Dummy"]
    COMP-29 --> COMP-17
    COMP-15 --> COMP-25
    COMP-23["Engine"]
    COMP-19["Context"]
    COMP-23 --> COMP-19
    COMP-21["Defaultfilters"]
    COMP-15 --> COMP-21
    COMP-23 --> COMP-25
    COMP-30["Filesystem"]
    COMP-30 --> COMP-21
    COMP-16["Django"]
    COMP-16 --> COMP-21
    COMP-29 --> COMP-16
    COMP-21 --> COMP-16
    COMP-31["Locmem"]
    COMP-31 --> COMP-15
    COMP-33["Smartif"]
    COMP-28 --> COMP-33
    COMP-29 --> COMP-15
    COMP-29 --> COMP-23
    COMP-24["Exceptions"]
    COMP-28 --> COMP-24
    COMP-26["Loader"]
    COMP-26 --> COMP-25
    COMP-22["Defaulttags"]
    COMP-28 --> COMP-22
    COMP-23 --> COMP-24
    COMP-22 --> COMP-19
    COMP-25 --> COMP-16
    COMP-32["Response"]
    COMP-31 --> COMP-32
    COMP-22 --> COMP-16
    COMP-29 --> COMP-19
    COMP-28 --> COMP-21
    COMP-22 --> COMP-33
    COMP-21 --> COMP-25
    COMP-30 --> COMP-15
    COMP-30 --> COMP-23
    COMP-31 --> COMP-16
    COMP-18 --> COMP-32
    COMP-16 --> COMP-15
    COMP-16 --> COMP-23
    COMP-19 --> COMP-16
    COMP-31 --> COMP-23
    COMP-29 --> COMP-33
    COMP-17 --> COMP-32
    COMP-29 --> COMP-24
    COMP-18 --> COMP-16
    COMP-29 --> COMP-22
    COMP-15 --> COMP-32
    COMP-31 --> COMP-26
    COMP-32 --> COMP-16
    COMP-30 --> COMP-32
    COMP-29 --> COMP-26
    COMP-16 --> COMP-32
    COMP-18 --> COMP-15
    COMP-18 --> COMP-23
    COMP-22 --> COMP-25
    COMP-15 --> COMP-17
    COMP-17 --> COMP-16
    COMP-16 --> COMP-19
    COMP-31 --> COMP-19
    COMP-17 --> COMP-15
    COMP-17 --> COMP-23
    COMP-29 --> COMP-18
    COMP-15 --> COMP-16
    COMP-31 --> COMP-25
    COMP-30 --> COMP-16
    COMP-29 --> COMP-25
    COMP-18 --> COMP-26
    COMP-25 --> COMP-24
    COMP-28 --> COMP-15
    COMP-29 --> COMP-21
    COMP-15 --> COMP-23
    COMP-16 --> COMP-33
    COMP-17 --> COMP-26
    COMP-16 --> COMP-24
    COMP-31 --> COMP-33
    COMP-18 --> COMP-19
    COMP-31 --> COMP-24
    COMP-16 --> COMP-22
    COMP-26 --> COMP-16
    COMP-30 --> COMP-26
    COMP-16 --> COMP-26
    COMP-31 --> COMP-22
    COMP-28 --> COMP-32
    COMP-17 --> COMP-19
    COMP-17 --> COMP-25
    COMP-18 --> COMP-33
    COMP-15 --> COMP-19
    COMP-30 --> COMP-19
    COMP-22 --> COMP-21
    COMP-18 --> COMP-24
    COMP-30 --> COMP-25
    COMP-16 --> COMP-25
    COMP-28 --> COMP-16
    COMP-18 --> COMP-22
    COMP-17 --> COMP-33
    COMP-31 --> COMP-21
    COMP-17 --> COMP-24
    COMP-23 --> COMP-16
    COMP-28 --> COMP-23
    COMP-32 --> COMP-26
    COMP-15 --> COMP-33
    COMP-17 --> COMP-22
    COMP-30 --> COMP-33
    COMP-15 --> COMP-24
    COMP-30 --> COMP-24
    COMP-15 --> COMP-22
    COMP-30 --> COMP-22
    COMP-18 --> COMP-25
    COMP-28 --> COMP-26
    COMP-15 --> COMP-26
    COMP-18 --> COMP-21
    COMP-26 --> COMP-24
    COMP-29 --> COMP-32
    COMP-28 --> COMP-30
    COMP-17 --> COMP-21
    COMP-28 --> COMP-19
```
