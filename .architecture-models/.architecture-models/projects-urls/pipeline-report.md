# Pipeline Report: Projects (urls)

**Generated:** 2026-08-18T12:32:12Z
**Total Duration:** 4061ms
**Stages:** 2

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 4061ms | 0 |
| infer | 100 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 4061ms

### Deterministic Findings
- Discovered 6 modules
- 29 functions, 16 classes
- 7 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 100 | **Duration:** 0ms

### Deterministic Findings
- Inferred 18 capabilities
- 1 actors
- 18 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: projects/django/django/urls/base.py has 10 public functions with 8 cross-calls — likely contains workflow patterns
