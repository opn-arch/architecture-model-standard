# Pipeline Report: Src (pipeline)

**Generated:** 2026-08-18T23:36:13Z
**Total Duration:** 3958ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 3950ms | 0 |
| infer | 100 | 0ms | 0 |
| allocate | 57 | 1ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 7ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 0 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 3950ms

### Deterministic Findings
- Discovered 33 modules
- 84 functions, 68 classes
- 79 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- dynamic_import: Dynamic import in src/architecture_model/pipeline/cache.py:73

## Stage: infer
**Score:** 100 | **Duration:** 0ms

### Deterministic Findings
- Inferred 47 capabilities
- 1 actors
- 18 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: allocate
**Score:** 57 | **Duration:** 1ms

### Deterministic Findings
- 21 components
- File coverage: 10000%
- 0 unallocated files

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: contract
**Score:** 0 | **Duration:** 0ms

### Deterministic Findings
- 0 contracts

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: relate
**Score:** 100 | **Duration:** 7ms

### Deterministic Findings
- 140 depends-on relationships
- 21 realizes relationships
- 21 contains relationships

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: specify
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 0 interfaces

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: validate
**Score:** 0 | **Duration:** 0ms

### Deterministic Findings
- Score: 0/100
- 27 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*
