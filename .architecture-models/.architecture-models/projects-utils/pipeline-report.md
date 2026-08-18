# Pipeline Report: Projects (utils)

**Generated:** 2026-08-18T12:32:08Z
**Total Duration:** 4091ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 4076ms | 0 |
| infer | 95 | 1ms | 0 |
| allocate | 50 | 1ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 13ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 25 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 4076ms

### Deterministic Findings
- Discovered 46 modules
- 267 functions, 71 classes
- 62 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 95 | **Duration:** 1ms

### Deterministic Findings
- Inferred 58 capabilities
- 1 actors
- 19 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: TimeFormat in projects/django/django/utils/dateformat.py has 15 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: DateFormat in projects/django/django/utils/dateformat.py has 24 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: projects/django/django/utils/autoreload.py has 15 public functions with 7 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/utils/cache.py has 10 public functions with 3 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/utils/encoding.py has 12 public functions with 6 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/utils/formats.py has 11 public functions with 13 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/utils/html.py has 13 public functions with 7 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/utils/http.py has 17 public functions with 3 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/utils/inspect.py has 10 public functions with 3 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/utils/timezone.py has 15 public functions with 14 cross-calls — likely contains workflow patterns
- complex_behavior: projects/django/django/utils/translation/trans_real.py has 22 public functions with 19 cross-calls — likely contains workflow patterns
- ambiguous_module: projects/django/django/utils/copy.py has no clear capability affiliation
- ambiguous_module: projects/django/django/utils/dates.py has no clear capability affiliation

## Stage: allocate
**Score:** 50 | **Duration:** 1ms

### Deterministic Findings
- 43 components
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
**Score:** 100 | **Duration:** 13ms

### Deterministic Findings
- 1199 depends-on relationships
- 43 realizes relationships
- 43 contains relationships

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
**Score:** 25 | **Duration:** 0ms

### Deterministic Findings
- Score: 25/100
- 16 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*
