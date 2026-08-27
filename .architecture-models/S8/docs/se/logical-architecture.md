---
document: Logical Architecture
system: architecture-model-standard/Extract
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: 2241722504ec
edition: 1
---

> **Model Completeness: F (15%)**
> Some sections may be empty due to missing model entities.
> - 1/1 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - No actors defined → conops stakeholder section empty
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Logical Architecture: architecture-model-standard/Extract

## Layer Structure

*No layers defined.*

## Component Allocation

### LYR-CORE

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Extract (COMP-EXTRACT) | library | 6 files | — |

*Intent:* Provide the code-to-model backward pass that derives architecture entities and relationships from AST scanning, import graphs, and project configuration

*Trade-offs:*
- AST-only analysis misses runtime-dynamic registrations vs. static completeness is simpler and faster
- Single-pass extraction vs. iterative refinement — speed over precision for initial model
- Python-only AST support vs. multi-language — focused quality over broad coverage


## Inter-Component Interfaces

*No interfaces defined.*

## Dependency Graph

```mermaid
graph TD
```
