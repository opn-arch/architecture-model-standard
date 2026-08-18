# Pipeline Report: Projects (views)

**Generated:** 2026-08-18T12:32:21Z
**Total Duration:** 4002ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 4000ms | 0 |
| infer | 94 | 0ms | 0 |
| allocate | 55 | 0ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 2ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 30 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 4000ms

### Deterministic Findings
- Discovered 19 modules
- 43 functions, 53 classes
- 10 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 94 | **Duration:** 0ms

### Deterministic Findings
- Inferred 28 capabilities
- 1 actors
- 35 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- ambiguous_module: projects/django/django/views/decorators/gzip.py has no clear capability affiliation

## Stage: allocate
**Score:** 55 | **Duration:** 0ms

### Deterministic Findings
- 15 components
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
**Score:** 100 | **Duration:** 2ms

### Deterministic Findings
- 88 depends-on relationships
- 15 contains relationships
- 14 realizes relationships

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
**Score:** 30 | **Duration:** 0ms

### Deterministic Findings
- Score: 30/100
- 15 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*
