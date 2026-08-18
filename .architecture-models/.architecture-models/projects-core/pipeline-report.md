# Pipeline Report: Projects (core)

**Generated:** 2026-08-18T12:32:00Z
**Total Duration:** 4225ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 4144ms | 0 |
| infer | 97 | 2ms | 0 |
| allocate | 52 | 4ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 75ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 90 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 4144ms

### Deterministic Findings
- Discovered 97 modules
- 142 functions, 191 classes
- 113 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 97 | **Duration:** 2ms

### Deterministic Findings
- Inferred 77 capabilities
- 1 actors
- 52 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: BaseCache in projects/django/django/core/cache/backends/base.py has 36 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: Storage in projects/django/django/core/files/storage/base.py has 16 public methods — needs LLM analysis to identify key workflows and use cases
- complex_behavior: FileSystemStorage in projects/django/django/core/files/storage/filesystem.py has 16 public methods — needs LLM analysis to identify key workflows and use cases
- ambiguous_module: projects/django/django/core/files/locks.py has no clear capability affiliation
- ambiguous_module: projects/django/django/core/signals.py has no clear capability affiliation

## Stage: allocate
**Score:** 52 | **Duration:** 4ms

### Deterministic Findings
- 76 components
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
**Score:** 100 | **Duration:** 75ms

### Deterministic Findings
- 944 depends-on relationships
- 76 contains relationships
- 75 realizes relationships

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: specify
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 2 interfaces

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: validate
**Score:** 90 | **Duration:** 0ms

### Deterministic Findings
- Score: 90/100
- 3 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- generic_capability_name: Capability 'Web Routes' (CAP-1) has a generic name. LLM analysis could produce a more specific business-oriented name.
