# Pipeline Report: Projects (forms)

**Generated:** 2026-08-18T12:31:56Z
**Total Duration:** 4011ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 4011ms | 0 |
| infer | 100 | 0ms | 0 |
| allocate | 50 | 0ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 0ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 30 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 4011ms

### Deterministic Findings
- Discovered 8 modules
- 18 functions, 97 classes
- 22 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 100 | **Duration:** 0ms

### Deterministic Findings
- Inferred 21 capabilities
- 1 actors
- 20 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: BoundField in projects/django/django/forms/boundfield.py has 21 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: BaseForm in projects/django/django/forms/forms.py has 19 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: BaseFormSet in projects/django/django/forms/formsets.py has 27 public methods — needs LLM analysis to identify key workflows and use cases

## Stage: allocate
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 8 components
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
**Score:** 100 | **Duration:** 0ms

### Deterministic Findings
- 50 depends-on relationships
- 8 contains relationships
- 7 realizes relationships

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
