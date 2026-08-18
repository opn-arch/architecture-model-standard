---
document: Maintenance Manual
system: Src (manifest)
system_id: SYS-unknown
generated_at: 2026-08-18T20:06:07Z
generator_version: 0.3.0
model_hash: 43ce18da3e69
edition: 4
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
| Behavior | — | Scan Cache, Multi Scanner, Generator, Grouping, Interfaces, Recursive, Kt Scanner, Call Graph, Slicers, Blocks, Metrics | HIGH |
| Blocks | Body Hints, Generator, Grouping, Recursive, Display, Kt Scanner, Chains, Multi Scanner, Scan Cache, Interfaces, Metrics, Behavior, Protocol, Slicers, Ts Scanner, Call Graph | Multi Scanner, Grouping, Interfaces, Generator, Recursive, Kt Scanner, Slicers, Metrics, Scan Cache, Body Hints, Call Graph | HIGH |
| Body Hints | Blocks | Slicers, Blocks, Recursive, Kt Scanner, Call Graph, Scan Cache, Metrics, Multi Scanner, Generator, Grouping, Interfaces | HIGH |
| Call Graph | Protocol, Slicers, Ts Scanner, Kt Scanner, Body Hints, Generator, Grouping, Recursive, Display, Chains, Multi Scanner, Scan Cache, Behavior, Interfaces, Blocks, Metrics | Scan Cache, Multi Scanner, Generator, Grouping, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Metrics | HIGH |
| Chains | — | Generator, Grouping, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner | HIGH |
| Display | — | Generator, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner, Grouping, Interfaces | HIGH |
| Generator | Display, Chains, Interfaces, Scan Cache, Behavior, Blocks, Metrics, Protocol, Slicers, Ts Scanner, Call Graph, Kt Scanner, Body Hints, Grouping, Multi Scanner, Recursive | Interfaces, Slicers, Blocks, Metrics, Kt Scanner, Call Graph, Scan Cache, Multi Scanner, Grouping, Recursive | HIGH |
| Grouping | Chains, Interfaces, Blocks, Behavior, Slicers, Scan Cache, Metrics, Protocol, Ts Scanner, Call Graph, Recursive, Display, Kt Scanner, Body Hints, Generator, Multi Scanner | Interfaces, Slicers, Blocks, Recursive, Kt Scanner, Call Graph, Metrics, Scan Cache, Multi Scanner, Generator | HIGH |
| Interfaces | Generator, Grouping, Multi Scanner, Recursive, Chains, Scan Cache, Blocks, Behavior, Slicers, Metrics, Protocol, Ts Scanner, Call Graph, Display, Kt Scanner, Body Hints | Generator, Grouping, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner | HIGH |
| Kt Scanner | Ts Scanner, Recursive, Display, Body Hints, Generator, Grouping, Chains, Multi Scanner, Scan Cache, Interfaces, Blocks, Behavior, Slicers, Call Graph, Metrics, Protocol | Recursive, Call Graph, Slicers, Blocks, Metrics, Scan Cache, Multi Scanner, Generator, Grouping, Interfaces | HIGH |
| Metrics | Generator, Protocol, Ts Scanner, Recursive, Display, Kt Scanner, Body Hints, Grouping, Chains, Multi Scanner, Scan Cache, Interfaces, Blocks, Behavior, Slicers, Call Graph | Multi Scanner, Generator, Grouping, Recursive, Interfaces, Slicers, Blocks, Kt Scanner, Call Graph, Scan Cache | HIGH |
| Multi Scanner | Blocks, Metrics, Behavior, Slicers, Ts Scanner, Call Graph, Body Hints, Generator, Protocol, Recursive, Display, Kt Scanner, Grouping, Chains, Scan Cache, Interfaces | Interfaces, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Generator, Grouping | HIGH |
| Protocol | — | Call Graph, Metrics, Scan Cache, Multi Scanner, Generator, Grouping, Interfaces, Slicers, Blocks, Recursive, Kt Scanner | HIGH |
| Recursive | Display, Kt Scanner, Body Hints, Grouping, Chains, Multi Scanner, Scan Cache, Interfaces, Blocks, Metrics, Behavior, Slicers, Call Graph, Generator, Protocol, Ts Scanner | Kt Scanner, Interfaces, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner, Grouping, Generator | HIGH |
| Scan Cache | Behavior, Slicers, Ts Scanner, Call Graph, Body Hints, Generator, Protocol, Recursive, Display, Kt Scanner, Grouping, Chains, Multi Scanner, Blocks, Interfaces, Metrics | Generator, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Grouping, Metrics, Call Graph, Multi Scanner | HIGH |
| Slicers | Body Hints, Generator, Grouping, Recursive, Display, Kt Scanner, Chains, Multi Scanner, Scan Cache, Interfaces, Blocks, Metrics, Behavior, Protocol, Ts Scanner, Call Graph | Call Graph, Scan Cache, Multi Scanner, Grouping, Interfaces, Generator, Recursive, Kt Scanner, Blocks, Metrics | HIGH |
| Ts Scanner | — | Kt Scanner, Call Graph, Scan Cache, Metrics, Multi Scanner, Generator, Grouping, Interfaces, Slicers, Blocks, Recursive | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Behavior (src-manifest-COMP-16)

**Files:**
- `src/architecture_model/manifest/behavior.py`
**Downstream dependents (must re-test):** Scan Cache, Multi Scanner, Generator, Grouping, Interfaces, Recursive, Kt Scanner, Call Graph, Slicers, Blocks, Metrics

### Blocks (src-manifest-COMP-17)

**Files:**
- `src/architecture_model/manifest/__init__.py`
- `src/architecture_model/manifest/blocks.py`
- `src/architecture_model/manifest/types.py`
**Downstream dependents (must re-test):** Multi Scanner, Grouping, Interfaces, Generator, Recursive, Kt Scanner, Slicers, Metrics, Scan Cache, Body Hints, Call Graph

### Body Hints (src-manifest-COMP-18)

**Files:**
- `src/architecture_model/manifest/body_hints.py`
**Downstream dependents (must re-test):** Slicers, Blocks, Recursive, Kt Scanner, Call Graph, Scan Cache, Metrics, Multi Scanner, Generator, Grouping, Interfaces

### Call Graph (src-manifest-COMP-19)

**Files:**
- `src/architecture_model/manifest/call_graph.py`
**Downstream dependents (must re-test):** Scan Cache, Multi Scanner, Generator, Grouping, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Metrics

### Chains (src-manifest-COMP-20)

**Files:**
- `src/architecture_model/manifest/chains.py`
**Downstream dependents (must re-test):** Generator, Grouping, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner

### Display (src-manifest-COMP-21)

**Files:**
- `src/architecture_model/manifest/display.py`
**Downstream dependents (must re-test):** Generator, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner, Grouping, Interfaces

### Generator (src-manifest-COMP-22)

**Files:**
- `src/architecture_model/manifest/generator.py`
**Downstream dependents (must re-test):** Interfaces, Slicers, Blocks, Metrics, Kt Scanner, Call Graph, Scan Cache, Multi Scanner, Grouping, Recursive

### Grouping (src-manifest-COMP-23)

**Files:**
- `src/architecture_model/manifest/grouping.py`
**Downstream dependents (must re-test):** Interfaces, Slicers, Blocks, Recursive, Kt Scanner, Call Graph, Metrics, Scan Cache, Multi Scanner, Generator

### Interfaces (src-manifest-COMP-24)

**Files:**
- `src/architecture_model/manifest/interfaces.py`
**Downstream dependents (must re-test):** Generator, Grouping, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner

### Kt Scanner (src-manifest-COMP-25)

**Files:**
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/scanner.py`
**Downstream dependents (must re-test):** Recursive, Call Graph, Slicers, Blocks, Metrics, Scan Cache, Multi Scanner, Generator, Grouping, Interfaces

### Metrics (src-manifest-COMP-26)

**Files:**
- `src/architecture_model/manifest/metrics.py`
**Downstream dependents (must re-test):** Multi Scanner, Generator, Grouping, Recursive, Interfaces, Slicers, Blocks, Kt Scanner, Call Graph, Scan Cache

### Multi Scanner (src-manifest-COMP-27)

**Files:**
- `src/architecture_model/manifest/multi_scanner.py`
**Downstream dependents (must re-test):** Interfaces, Recursive, Kt Scanner, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Generator, Grouping

### Protocol (src-manifest-COMP-28)

**Files:**
- `src/architecture_model/manifest/protocol.py`
**Downstream dependents (must re-test):** Call Graph, Metrics, Scan Cache, Multi Scanner, Generator, Grouping, Interfaces, Slicers, Blocks, Recursive, Kt Scanner

### Recursive (src-manifest-COMP-29)

**Files:**
- `src/architecture_model/manifest/recursive.py`
**Downstream dependents (must re-test):** Kt Scanner, Interfaces, Slicers, Blocks, Metrics, Call Graph, Scan Cache, Multi Scanner, Grouping, Generator

### Scan Cache (src-manifest-COMP-30)

**Files:**
- `src/architecture_model/manifest/scan_cache.py`
**Downstream dependents (must re-test):** Generator, Recursive, Kt Scanner, Interfaces, Slicers, Blocks, Grouping, Metrics, Call Graph, Multi Scanner

### Slicers (src-manifest-COMP-32)

**Files:**
- `src/architecture_model/manifest/slicers.py`
**Downstream dependents (must re-test):** Call Graph, Scan Cache, Multi Scanner, Grouping, Interfaces, Generator, Recursive, Kt Scanner, Blocks, Metrics

### Ts Scanner (src-manifest-COMP-33)

**Files:**
- `src/architecture_model/manifest/ts_scanner.py`
**Downstream dependents (must re-test):** Kt Scanner, Call Graph, Scan Cache, Metrics, Multi Scanner, Generator, Grouping, Interfaces, Slicers, Blocks, Recursive

## Known Constraints

*No constraint allocations defined.*
