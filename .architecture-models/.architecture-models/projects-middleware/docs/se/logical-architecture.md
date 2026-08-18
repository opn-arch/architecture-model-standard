---
document: Logical Architecture
system: Projects (middleware)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:28Z
generator_version: 0.3.0
model_hash: ad0657be9014
edition: 3
---

# Logical Architecture: Projects (middleware)

## Layer Structure

| Order | Layer | Technologies | Directories |
|-------|-------|-------------|-------------|
| 0 | infra | — | — |

## Component Allocation

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Cache (COMP-1) | service | 1 files | — |
| Clickjacking (COMP-2) | service | 1 files | — |
| Common (COMP-3) | service | 1 files | — |
| Csp (COMP-4) | service | 1 files | — |
| Csrf (COMP-5) | service | 1 files | — |
| Gzip (COMP-6) | service | 1 files | — |
| Http (COMP-7) | service | 1 files | — |
| Locale (COMP-8) | service | 1 files | — |
| Security (COMP-9) | service | 1 files | — |

## Inter-Component Interfaces

*No interfaces defined.*

## Dependency Graph

```mermaid
graph TD
    COMP-1["Cache"]
    COMP-9["Security"]
    COMP-1 --> COMP-9
    COMP-2["Clickjacking"]
    COMP-5["Csrf"]
    COMP-2 --> COMP-5
    COMP-4["Csp"]
    COMP-1 --> COMP-4
    COMP-7["Http"]
    COMP-8["Locale"]
    COMP-7 --> COMP-8
    COMP-9 --> COMP-1
    COMP-6["Gzip"]
    COMP-6 --> COMP-7
    COMP-6 --> COMP-4
    COMP-6 --> COMP-9
    COMP-9 --> COMP-5
    COMP-2 --> COMP-7
    COMP-2 --> COMP-4
    COMP-2 --> COMP-9
    COMP-3["Common"]
    COMP-5 --> COMP-3
    COMP-3 --> COMP-6
    COMP-8 --> COMP-3
    COMP-3 --> COMP-2
    COMP-7 --> COMP-1
    COMP-8 --> COMP-6
    COMP-9 --> COMP-7
    COMP-9 --> COMP-4
    COMP-5 --> COMP-6
    COMP-4 --> COMP-3
    COMP-5 --> COMP-2
    COMP-4 --> COMP-6
    COMP-7 --> COMP-5
    COMP-4 --> COMP-2
    COMP-8 --> COMP-2
    COMP-3 --> COMP-8
    COMP-1 --> COMP-3
    COMP-5 --> COMP-8
    COMP-7 --> COMP-9
    COMP-4 --> COMP-8
    COMP-7 --> COMP-4
    COMP-1 --> COMP-6
    COMP-1 --> COMP-2
    COMP-6 --> COMP-3
    COMP-3 --> COMP-1
    COMP-2 --> COMP-3
    COMP-8 --> COMP-1
    COMP-2 --> COMP-6
    COMP-6 --> COMP-2
    COMP-1 --> COMP-8
    COMP-5 --> COMP-1
    COMP-4 --> COMP-1
    COMP-6 --> COMP-8
    COMP-3 --> COMP-5
    COMP-9 --> COMP-3
    COMP-8 --> COMP-5
    COMP-9 --> COMP-6
    COMP-2 --> COMP-8
    COMP-9 --> COMP-2
    COMP-3 --> COMP-9
    COMP-4 --> COMP-5
    COMP-3 --> COMP-7
    COMP-3 --> COMP-4
    COMP-5 --> COMP-7
    COMP-8 --> COMP-7
    COMP-5 --> COMP-9
    COMP-8 --> COMP-4
    COMP-8 --> COMP-9
    COMP-7 --> COMP-3
    COMP-5 --> COMP-4
    COMP-1 --> COMP-5
    COMP-4 --> COMP-7
    COMP-9 --> COMP-8
    COMP-4 --> COMP-9
    COMP-7 --> COMP-6
    COMP-6 --> COMP-1
    COMP-7 --> COMP-2
    COMP-6 --> COMP-5
    COMP-1 --> COMP-7
    COMP-2 --> COMP-1
```
