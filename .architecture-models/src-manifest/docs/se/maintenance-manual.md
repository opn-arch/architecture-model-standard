---
document: Maintenance Manual
system: Src (manifest)
system_id: SYS-unknown
generated_at: 2026-08-19T17:00:10Z
generator_version: 0.3.0
model_hash: 43ce18da3e69
edition: 7
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
| Behavior | — | Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics | HIGH |
| Blocks | Display, Behavior, Ts Scanner, Generator, Protocol, Slicers, Chains, Metrics, Recursive, Body Hints, Call Graph, Kt Scanner, Grouping, Interfaces, Multi Scanner, Scan Cache | Call Graph, Scan Cache, Body Hints, Generator, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics | HIGH |
| Body Hints | Blocks | Grouping, Metrics, Interfaces, Call Graph, Multi Scanner, Scan Cache, Blocks, Kt Scanner, Generator, Slicers, Recursive | HIGH |
| Call Graph | Scan Cache, Blocks, Metrics, Behavior, Protocol, Body Hints, Chains, Grouping, Recursive, Interfaces, Kt Scanner, Multi Scanner, Display, Ts Scanner, Generator, Slicers | Grouping, Interfaces, Recursive, Multi Scanner, Metrics, Blocks, Scan Cache, Generator, Slicers, Kt Scanner | HIGH |
| Chains | — | Recursive, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Interfaces | HIGH |
| Display | — | Blocks, Kt Scanner, Generator, Slicers, Recursive, Grouping, Metrics, Interfaces, Call Graph, Multi Scanner, Scan Cache | HIGH |
| Generator | Grouping, Interfaces, Kt Scanner, Multi Scanner, Display, Blocks, Behavior, Ts Scanner, Protocol, Slicers, Scan Cache, Chains, Metrics, Recursive, Body Hints, Call Graph | Scan Cache, Blocks, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Call Graph | HIGH |
| Grouping | Body Hints, Call Graph, Recursive, Interfaces, Kt Scanner, Multi Scanner, Display, Ts Scanner, Generator, Protocol, Slicers, Scan Cache, Blocks, Chains, Metrics, Behavior | Generator, Slicers, Kt Scanner, Interfaces, Recursive, Call Graph, Multi Scanner, Metrics, Blocks, Scan Cache | HIGH |
| Interfaces | Recursive, Body Hints, Call Graph, Kt Scanner, Multi Scanner, Grouping, Generator, Scan Cache, Display, Blocks, Behavior, Ts Scanner, Protocol, Slicers, Chains, Metrics | Generator, Slicers, Recursive, Grouping, Call Graph, Multi Scanner, Metrics, Blocks, Scan Cache, Kt Scanner | HIGH |
| Kt Scanner | Multi Scanner, Grouping, Display, Ts Scanner, Generator, Slicers, Scan Cache, Blocks, Behavior, Protocol, Body Hints, Chains, Metrics, Recursive, Interfaces, Call Graph | Generator, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Slicers | HIGH |
| Metrics | Protocol, Body Hints, Chains, Recursive, Call Graph, Kt Scanner, Multi Scanner, Grouping, Interfaces, Display, Generator, Slicers, Scan Cache, Blocks, Behavior, Ts Scanner | Recursive, Call Graph, Multi Scanner, Blocks, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Interfaces | HIGH |
| Multi Scanner | Slicers, Chains, Metrics, Recursive, Body Hints, Call Graph, Kt Scanner, Grouping, Interfaces, Generator, Protocol, Scan Cache, Display, Blocks, Behavior, Ts Scanner | Slicers, Kt Scanner, Generator, Interfaces, Recursive, Grouping, Metrics, Call Graph, Scan Cache, Blocks | HIGH |
| Protocol | — | Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Multi Scanner, Interfaces, Recursive | HIGH |
| Recursive | Chains, Metrics, Interfaces, Call Graph, Kt Scanner, Multi Scanner, Grouping, Display, Ts Scanner, Generator, Slicers, Scan Cache, Blocks, Behavior, Protocol, Body Hints | Interfaces, Grouping, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner | HIGH |
| Scan Cache | Generator, Slicers, Blocks, Behavior, Ts Scanner, Protocol, Body Hints, Chains, Metrics, Recursive, Call Graph, Kt Scanner, Multi Scanner, Grouping, Interfaces, Display | Call Graph, Slicers, Kt Scanner, Generator, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Blocks | HIGH |
| Slicers | Multi Scanner, Grouping, Interfaces, Generator, Scan Cache, Display, Blocks, Behavior, Ts Scanner, Protocol, Chains, Metrics, Recursive, Body Hints, Call Graph, Kt Scanner | Multi Scanner, Scan Cache, Blocks, Kt Scanner, Generator, Recursive, Grouping, Metrics, Interfaces, Call Graph | HIGH |
| Ts Scanner | — | Blocks, Scan Cache, Kt Scanner, Generator, Slicers, Recursive, Grouping, Interfaces, Call Graph, Multi Scanner, Metrics | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Behavior (src-manifest-COMP-16)

**Files:**
- `src/architecture_model/manifest/behavior.py`
**Downstream dependents (must re-test):** Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics

### Blocks (src-manifest-COMP-17)

**Files:**
- `src/architecture_model/manifest/__init__.py`
- `src/architecture_model/manifest/blocks.py`
- `src/architecture_model/manifest/types.py`
**Downstream dependents (must re-test):** Call Graph, Scan Cache, Body Hints, Generator, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics

### Body Hints (src-manifest-COMP-18)

**Files:**
- `src/architecture_model/manifest/body_hints.py`
**Downstream dependents (must re-test):** Grouping, Metrics, Interfaces, Call Graph, Multi Scanner, Scan Cache, Blocks, Kt Scanner, Generator, Slicers, Recursive

### Call Graph (src-manifest-COMP-19)

**Files:**
- `src/architecture_model/manifest/call_graph.py`
**Downstream dependents (must re-test):** Grouping, Interfaces, Recursive, Multi Scanner, Metrics, Blocks, Scan Cache, Generator, Slicers, Kt Scanner

### Chains (src-manifest-COMP-20)

**Files:**
- `src/architecture_model/manifest/chains.py`
**Downstream dependents (must re-test):** Recursive, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Interfaces

### Display (src-manifest-COMP-21)

**Files:**
- `src/architecture_model/manifest/display.py`
**Downstream dependents (must re-test):** Blocks, Kt Scanner, Generator, Slicers, Recursive, Grouping, Metrics, Interfaces, Call Graph, Multi Scanner, Scan Cache

### Generator (src-manifest-COMP-22)

**Files:**
- `src/architecture_model/manifest/generator.py`
**Downstream dependents (must re-test):** Scan Cache, Blocks, Slicers, Kt Scanner, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Call Graph

### Grouping (src-manifest-COMP-23)

**Files:**
- `src/architecture_model/manifest/grouping.py`
**Downstream dependents (must re-test):** Generator, Slicers, Kt Scanner, Interfaces, Recursive, Call Graph, Multi Scanner, Metrics, Blocks, Scan Cache

### Interfaces (src-manifest-COMP-24)

**Files:**
- `src/architecture_model/manifest/interfaces.py`
**Downstream dependents (must re-test):** Generator, Slicers, Recursive, Grouping, Call Graph, Multi Scanner, Metrics, Blocks, Scan Cache, Kt Scanner

### Kt Scanner (src-manifest-COMP-25)

**Files:**
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/scanner.py`
**Downstream dependents (must re-test):** Generator, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Slicers

### Metrics (src-manifest-COMP-26)

**Files:**
- `src/architecture_model/manifest/metrics.py`
**Downstream dependents (must re-test):** Recursive, Call Graph, Multi Scanner, Blocks, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Interfaces

### Multi Scanner (src-manifest-COMP-27)

**Files:**
- `src/architecture_model/manifest/multi_scanner.py`
**Downstream dependents (must re-test):** Slicers, Kt Scanner, Generator, Interfaces, Recursive, Grouping, Metrics, Call Graph, Scan Cache, Blocks

### Protocol (src-manifest-COMP-28)

**Files:**
- `src/architecture_model/manifest/protocol.py`
**Downstream dependents (must re-test):** Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner, Grouping, Multi Scanner, Interfaces, Recursive

### Recursive (src-manifest-COMP-29)

**Files:**
- `src/architecture_model/manifest/recursive.py`
**Downstream dependents (must re-test):** Interfaces, Grouping, Multi Scanner, Metrics, Blocks, Call Graph, Scan Cache, Generator, Slicers, Kt Scanner

### Scan Cache (src-manifest-COMP-30)

**Files:**
- `src/architecture_model/manifest/scan_cache.py`
**Downstream dependents (must re-test):** Call Graph, Slicers, Kt Scanner, Generator, Interfaces, Recursive, Grouping, Multi Scanner, Metrics, Blocks

### Slicers (src-manifest-COMP-32)

**Files:**
- `src/architecture_model/manifest/slicers.py`
**Downstream dependents (must re-test):** Multi Scanner, Scan Cache, Blocks, Kt Scanner, Generator, Recursive, Grouping, Metrics, Interfaces, Call Graph

### Ts Scanner (src-manifest-COMP-33)

**Files:**
- `src/architecture_model/manifest/ts_scanner.py`
**Downstream dependents (must re-test):** Blocks, Scan Cache, Kt Scanner, Generator, Slicers, Recursive, Grouping, Interfaces, Call Graph, Multi Scanner, Metrics

## Known Constraints

*No constraint allocations defined.*
