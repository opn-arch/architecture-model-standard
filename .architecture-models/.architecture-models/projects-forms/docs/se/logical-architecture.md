---
document: Logical Architecture
system: Projects (forms)
system_id: SYS-unknown
generated_at: 2026-08-18T12:32:29Z
generator_version: 0.3.0
model_hash: 0915ddc57676
edition: 3
---

# Logical Architecture: Projects (forms)

## Layer Structure

| Order | Layer | Technologies | Directories |
|-------|-------|-------------|-------------|
| 0 | infra | — | — |
| 0 | data | — | — |

## Component Allocation

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Boundfield (COMP-1) | service | 1 files | — |
| Fields (COMP-2) | service | 1 files | — |
| Forms (COMP-3) | service | 1 files | — |
| Formsets (COMP-4) | service | 1 files | — |
| Models (COMP-5) | service | 1 files | — |
| Renderers (COMP-6) | service | 1 files | — |
| Utils (COMP-7) | service | 1 files | — |
| Widgets (COMP-8) | service | 1 files | — |

## Inter-Component Interfaces

*No interfaces defined.*

## Dependency Graph

```mermaid
graph TD
    COMP-2["Fields"]
    COMP-5["Models"]
    COMP-2 --> COMP-5
    COMP-1["Boundfield"]
    COMP-4["Formsets"]
    COMP-1 --> COMP-4
    COMP-7["Utils"]
    COMP-8["Widgets"]
    COMP-7 --> COMP-8
    COMP-6["Renderers"]
    COMP-6 --> COMP-7
    COMP-2 --> COMP-7
    COMP-2 --> COMP-4
    COMP-3["Forms"]
    COMP-5 --> COMP-3
    COMP-3 --> COMP-6
    COMP-8 --> COMP-3
    COMP-3 --> COMP-2
    COMP-7 --> COMP-1
    COMP-8 --> COMP-6
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
    COMP-4 --> COMP-8
    COMP-7 --> COMP-4
    COMP-1 --> COMP-6
    COMP-1 --> COMP-2
    COMP-3 --> COMP-1
    COMP-2 --> COMP-3
    COMP-8 --> COMP-1
    COMP-2 --> COMP-6
    COMP-1 --> COMP-8
    COMP-5 --> COMP-1
    COMP-4 --> COMP-1
    COMP-3 --> COMP-5
    COMP-8 --> COMP-5
    COMP-2 --> COMP-8
    COMP-4 --> COMP-5
    COMP-3 --> COMP-7
    COMP-3 --> COMP-4
    COMP-5 --> COMP-7
    COMP-8 --> COMP-7
    COMP-8 --> COMP-4
    COMP-7 --> COMP-3
    COMP-5 --> COMP-4
    COMP-1 --> COMP-5
    COMP-4 --> COMP-7
    COMP-7 --> COMP-6
    COMP-7 --> COMP-2
    COMP-1 --> COMP-7
    COMP-2 --> COMP-1
```
