---
document: Logical Architecture
system: architecture-model-standard/Core
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: 3f3196a55536
edition: 1
---

# Logical Architecture: architecture-model-standard/Core

## Layer Structure

*No layers defined.*

## Component Allocation

### LYR-CORE

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Core (COMP-CORE) | library | 18 files | — |

*Intent:* Provide the foundational type system and deterministic operations that every other subsystem depends on, ensuring a single source of truth for model structure and semantics.

*Trade-offs:*
- Richness vs. parse speed — 1186-line types.py covers all schema variants but increases import time
- Strict typing vs. extensibility — dataclass fields enforce schema but make adding new entity types a multi-file change
- Determinism vs. intelligence — no LLM calls means coverage/confidence metrics are heuristic-based approximations


## Inter-Component Interfaces

| Interface | Type | Protocol | Provider | Consumer |
|-----------|------|----------|----------|----------|
| Python API | library | — | — | — |
| YAML Model Schema | file | — | — | — |

## Dependency Graph

```mermaid
graph TD
```
