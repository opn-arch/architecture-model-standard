---
document: Maintenance Manual
system: Src (manifest)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:56Z
generator_version: 0.3.0
model_hash: 43ce18da3e69
edition: 14
---

> **Model Completeness: F (25%)**
> Some sections may be empty due to missing model entities.
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> - 17/17 components missing description/responsibilities
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: Src (manifest)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Behavior (src-manifest-COMP-16) | service | — | 1 | 0 | 0 |
| Blocks (src-manifest-COMP-17) | service | — | 3 | 0 | 0 |
| Body Hints (src-manifest-COMP-18) | service | — | 1 | 0 | 0 |
| Call Graph (src-manifest-COMP-19) | service | — | 1 | 0 | 0 |
| Chains (src-manifest-COMP-20) | service | — | 1 | 0 | 0 |
| Display (src-manifest-COMP-21) | service | — | 1 | 0 | 0 |
| Generator (src-manifest-COMP-22) | service | — | 1 | 0 | 0 |
| Grouping (src-manifest-COMP-23) | service | — | 1 | 0 | 0 |
| Interfaces (src-manifest-COMP-24) | service | — | 1 | 0 | 0 |
| Kt Scanner (src-manifest-COMP-25) | service | — | 2 | 0 | 0 |
| Metrics (src-manifest-COMP-26) | service | — | 1 | 0 | 0 |
| Multi Scanner (src-manifest-COMP-27) | service | — | 1 | 0 | 0 |
| Protocol (src-manifest-COMP-28) | service | — | 1 | 0 | 0 |
| Recursive (src-manifest-COMP-29) | service | — | 1 | 0 | 0 |
| Scan Cache (src-manifest-COMP-30) | service | — | 1 | 0 | 0 |
| Slicers (src-manifest-COMP-32) | service | — | 1 | 0 | 0 |
| Ts Scanner (src-manifest-COMP-33) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Behavior | — | Blocks, Interfaces, Kt Scanner, Metrics, Multi Scanner, Grouping, Generator, Recursive, Scan Cache, Slicers, Call Graph | HIGH |
| Blocks | Scan Cache, Interfaces, Behavior, Kt Scanner, Call Graph, Generator, Metrics, Ts Scanner, Slicers, Display, Chains, Body Hints, Grouping, Recursive, Multi Scanner, Protocol | Interfaces, Kt Scanner, Metrics, Multi Scanner, Grouping, Generator, Recursive, Body Hints, Scan Cache, Slicers, Call Graph | HIGH |
| Body Hints | Blocks | Grouping, Generator, Recursive, Scan Cache, Slicers, Call Graph, Blocks, Interfaces, Kt Scanner, Metrics, Multi Scanner | HIGH |
| Call Graph | Grouping, Chains, Body Hints, Scan Cache, Recursive, Interfaces, Multi Scanner, Protocol, Generator, Blocks, Metrics, Ts Scanner, Slicers, Behavior, Display, Kt Scanner | Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Recursive, Scan Cache, Slicers | HIGH |
| Chains | — | Interfaces, Kt Scanner, Grouping, Generator, Multi Scanner, Slicers, Call Graph, Recursive, Scan Cache, Blocks, Metrics | HIGH |
| Display | — | Scan Cache, Slicers, Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive | HIGH |
| Generator | Grouping, Chains, Body Hints, Scan Cache, Recursive, Interfaces, Call Graph, Multi Scanner, Protocol, Blocks, Metrics, Ts Scanner, Slicers, Behavior, Display, Kt Scanner | Metrics, Blocks, Interfaces, Kt Scanner, Multi Scanner, Grouping, Call Graph, Recursive, Scan Cache, Slicers | HIGH |
| Grouping | Chains, Body Hints, Recursive, Multi Scanner, Protocol, Blocks, Metrics, Scan Cache, Interfaces, Behavior, Kt Scanner, Call Graph, Generator, Ts Scanner, Slicers, Display | Generator, Multi Scanner, Call Graph, Recursive, Scan Cache, Slicers, Metrics, Blocks, Interfaces, Kt Scanner | HIGH |
| Interfaces | Chains, Blocks, Scan Cache, Recursive, Behavior, Call Graph, Multi Scanner, Protocol, Generator, Metrics, Ts Scanner, Slicers, Display, Kt Scanner, Body Hints, Grouping | Metrics, Blocks, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive, Scan Cache, Slicers | HIGH |
| Kt Scanner | Multi Scanner, Chains, Blocks, Scan Cache, Recursive, Interfaces, Behavior, Call Graph, Protocol, Generator, Metrics, Ts Scanner, Slicers, Display, Body Hints, Grouping | Blocks, Metrics, Multi Scanner, Interfaces, Grouping, Generator, Scan Cache, Slicers, Call Graph, Recursive | HIGH |
| Metrics | Scan Cache, Recursive, Interfaces, Call Graph, Multi Scanner, Protocol, Generator, Blocks, Ts Scanner, Slicers, Behavior, Display, Kt Scanner, Grouping, Chains, Body Hints | Blocks, Interfaces, Kt Scanner, Grouping, Generator, Multi Scanner, Slicers, Call Graph, Recursive, Scan Cache | HIGH |
| Multi Scanner | Grouping, Chains, Blocks, Scan Cache, Recursive, Interfaces, Behavior, Kt Scanner, Call Graph, Protocol, Generator, Metrics, Ts Scanner, Slicers, Display, Body Hints | Kt Scanner, Metrics, Interfaces, Grouping, Generator, Scan Cache, Slicers, Call Graph, Recursive, Blocks | HIGH |
| Protocol | — | Metrics, Interfaces, Kt Scanner, Grouping, Generator, Multi Scanner, Slicers, Call Graph, Recursive, Scan Cache, Blocks | HIGH |
| Recursive | Body Hints, Grouping, Chains, Blocks, Scan Cache, Behavior, Interfaces, Call Graph, Multi Scanner, Protocol, Generator, Metrics, Ts Scanner, Slicers, Display, Kt Scanner | Metrics, Interfaces, Kt Scanner, Grouping, Generator, Multi Scanner, Slicers, Call Graph, Scan Cache, Blocks | HIGH |
| Scan Cache | Display, Body Hints, Grouping, Multi Scanner, Chains, Blocks, Recursive, Interfaces, Behavior, Kt Scanner, Call Graph, Protocol, Generator, Metrics, Ts Scanner, Slicers | Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive, Slicers | HIGH |
| Slicers | Ts Scanner, Display, Chains, Body Hints, Grouping, Recursive, Multi Scanner, Protocol, Blocks, Metrics, Scan Cache, Interfaces, Behavior, Kt Scanner, Call Graph, Generator | Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive, Scan Cache | HIGH |
| Ts Scanner | — | Slicers, Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive, Scan Cache | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Behavior (src-manifest-COMP-16)

**Files:**
- `src/architecture_model/manifest/behavior.py`
**Downstream dependents (must re-test):** Blocks, Interfaces, Kt Scanner, Metrics, Multi Scanner, Grouping, Generator, Recursive, Scan Cache, Slicers, Call Graph

### Blocks (src-manifest-COMP-17)

**Files:**
- `src/architecture_model/manifest/__init__.py`
- `src/architecture_model/manifest/blocks.py`
- `src/architecture_model/manifest/types.py`
**Downstream dependents (must re-test):** Interfaces, Kt Scanner, Metrics, Multi Scanner, Grouping, Generator, Recursive, Body Hints, Scan Cache, Slicers, Call Graph

### Body Hints (src-manifest-COMP-18)

**Files:**
- `src/architecture_model/manifest/body_hints.py`
**Downstream dependents (must re-test):** Grouping, Generator, Recursive, Scan Cache, Slicers, Call Graph, Blocks, Interfaces, Kt Scanner, Metrics, Multi Scanner

### Call Graph (src-manifest-COMP-19)

**Files:**
- `src/architecture_model/manifest/call_graph.py`
**Downstream dependents (must re-test):** Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Recursive, Scan Cache, Slicers

### Chains (src-manifest-COMP-20)

**Files:**
- `src/architecture_model/manifest/chains.py`
**Downstream dependents (must re-test):** Interfaces, Kt Scanner, Grouping, Generator, Multi Scanner, Slicers, Call Graph, Recursive, Scan Cache, Blocks, Metrics

### Display (src-manifest-COMP-21)

**Files:**
- `src/architecture_model/manifest/display.py`
**Downstream dependents (must re-test):** Scan Cache, Slicers, Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive

### Generator (src-manifest-COMP-22)

**Files:**
- `src/architecture_model/manifest/generator.py`
**Downstream dependents (must re-test):** Metrics, Blocks, Interfaces, Kt Scanner, Multi Scanner, Grouping, Call Graph, Recursive, Scan Cache, Slicers

### Grouping (src-manifest-COMP-23)

**Files:**
- `src/architecture_model/manifest/grouping.py`
**Downstream dependents (must re-test):** Generator, Multi Scanner, Call Graph, Recursive, Scan Cache, Slicers, Metrics, Blocks, Interfaces, Kt Scanner

### Interfaces (src-manifest-COMP-24)

**Files:**
- `src/architecture_model/manifest/interfaces.py`
**Downstream dependents (must re-test):** Metrics, Blocks, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive, Scan Cache, Slicers

### Kt Scanner (src-manifest-COMP-25)

**Files:**
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/scanner.py`
**Downstream dependents (must re-test):** Blocks, Metrics, Multi Scanner, Interfaces, Grouping, Generator, Scan Cache, Slicers, Call Graph, Recursive

### Metrics (src-manifest-COMP-26)

**Files:**
- `src/architecture_model/manifest/metrics.py`
**Downstream dependents (must re-test):** Blocks, Interfaces, Kt Scanner, Grouping, Generator, Multi Scanner, Slicers, Call Graph, Recursive, Scan Cache

### Multi Scanner (src-manifest-COMP-27)

**Files:**
- `src/architecture_model/manifest/multi_scanner.py`
**Downstream dependents (must re-test):** Kt Scanner, Metrics, Interfaces, Grouping, Generator, Scan Cache, Slicers, Call Graph, Recursive, Blocks

### Protocol (src-manifest-COMP-28)

**Files:**
- `src/architecture_model/manifest/protocol.py`
**Downstream dependents (must re-test):** Metrics, Interfaces, Kt Scanner, Grouping, Generator, Multi Scanner, Slicers, Call Graph, Recursive, Scan Cache, Blocks

### Recursive (src-manifest-COMP-29)

**Files:**
- `src/architecture_model/manifest/recursive.py`
**Downstream dependents (must re-test):** Metrics, Interfaces, Kt Scanner, Grouping, Generator, Multi Scanner, Slicers, Call Graph, Scan Cache, Blocks

### Scan Cache (src-manifest-COMP-30)

**Files:**
- `src/architecture_model/manifest/scan_cache.py`
**Downstream dependents (must re-test):** Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive, Slicers

### Slicers (src-manifest-COMP-32)

**Files:**
- `src/architecture_model/manifest/slicers.py`
**Downstream dependents (must re-test):** Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive, Scan Cache

### Ts Scanner (src-manifest-COMP-33)

**Files:**
- `src/architecture_model/manifest/ts_scanner.py`
**Downstream dependents (must re-test):** Slicers, Metrics, Blocks, Interfaces, Kt Scanner, Generator, Multi Scanner, Grouping, Call Graph, Recursive, Scan Cache

## Known Constraints

*No constraint allocations defined.*
