---
document: Functional Analysis
system: architecture-model-standard/Manifest
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:22Z
generator_version: 0.3.0
model_hash: 9cd52927cc1c
edition: 1
---

> **Model Completeness: D (45%)**
> Some sections may be empty due to missing model entities.
> - 1/1 components have no behavioral specification
> - No requirements defined
> - No actors defined → conops stakeholder section empty
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Functional Analysis: architecture-model-standard/Manifest

## Capability Inventory

| ID | Capability | Priority | Status | Description | Intent |
|----|-----------|----------|--------|-------------|--------|
| CAP-MANIFEST | Reality Manifest Generation | medium | ACTIVE | AST-scan source code to produce ground-truth inventory (modules, functions, classes, imports) | Provide a deterministic, AST-derived ground-truth representation of a codebase so that architecture models can be validated against code reality rather than relying on human-maintained documentation. |

## Measures of Effectiveness

| Capability | MOE |
|---|---|
| Reality Manifest Generation (CAP-MANIFEST) | Parses 100% of syntactically valid Python files without crash or silent data loss |
| Reality Manifest Generation (CAP-MANIFEST) | Produces identical manifest output for identical source input (deterministic) |
| Reality Manifest Generation (CAP-MANIFEST) | Extracts all public functions, classes, imports, and module-level constants from scanned files |

## Functional Decomposition

```mermaid
graph TD
    CAP-MANIFEST["Reality Manifest Generation"]
```

## Capability-Component Mapping

| Capability | Realized By | Component Kind |
|-----------|------------|----------------|
| Reality Manifest Generation | Manifest (COMP-MANIFEST) | library |

### Design Trade-offs

**Manifest** (COMP-MANIFEST):
- AST-only analysis (no type inference or runtime introspection) — fast and deterministic but misses dynamic patterns like monkey-patching or metaclass-generated APIs
- Single-pass file scanning vs. multi-pass — keeps memory usage low and speed high but cannot resolve circular import semantics
- Behavioral extraction is lightweight (call_order, guards) vs. full dataflow — provides useful signals for model enrichment without the complexity of inter-procedural analysis

## Behavioral Coverage

*No behaviors defined.*
