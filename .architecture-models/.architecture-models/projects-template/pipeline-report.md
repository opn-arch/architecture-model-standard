# Pipeline Report: Projects (template)

**Generated:** 2026-08-18T12:32:04Z
**Total Duration:** 3992ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 3988ms | 0 |
| infer | 100 | 0ms | 0 |
| allocate | 56 | 1ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 3ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 20 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 3988ms

### Deterministic Findings
- Discovered 24 modules
- 124 functions, 81 classes
- 51 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 100 | **Duration:** 0ms

### Deterministic Findings
- Inferred 33 capabilities
- 1 actors
- 18 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: projects/django/django/template/defaultfilters.py has 58 public functions with 11 cross-calls — likely contains workflow patterns

## Stage: allocate
**Score:** 56 | **Duration:** 1ms

### Deterministic Findings
- 17 components
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
**Score:** 100 | **Duration:** 3ms

### Deterministic Findings
- 110 depends-on relationships
- 17 realizes relationships
- 17 contains relationships

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
**Score:** 20 | **Duration:** 0ms

### Deterministic Findings
- Score: 20/100
- 17 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*
