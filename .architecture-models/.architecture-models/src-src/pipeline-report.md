# Pipeline Report: Src (src)

**Generated:** 2026-08-18T12:31:34Z
**Total Duration:** 4264ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 4199ms | 0 |
| infer | 99 | 2ms | 0 |
| allocate | 53 | 3ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 60ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 0 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 4199ms

### Deterministic Findings
- Discovered 102 modules
- 576 functions, 184 classes
- 173 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- dynamic_import: Dynamic import in src/architecture_model/pipeline/cache.py:66

## Stage: infer
**Score:** 99 | **Duration:** 2ms

### Deterministic Findings
- Inferred 95 capabilities
- 1 actors
- 19 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: src/architecture_model/export/flatfiles.py has 11 public functions with 10 cross-calls — likely contains workflow patterns
- ambiguous_module: src/architecture_model/__main__.py has no clear capability affiliation

## Stage: allocate
**Score:** 53 | **Duration:** 3ms

### Deterministic Findings
- 72 components
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
**Score:** 100 | **Duration:** 60ms

### Deterministic Findings
- 981 depends-on relationships
- 72 realizes relationships
- 72 contains relationships

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: specify
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 1 interfaces

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: validate
**Score:** 0 | **Duration:** 0ms

### Deterministic Findings
- Score: 0/100
- 24 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- generic_capability_name: Capability 'Web Routes' (CAP-1) has a generic name. LLM analysis could produce a more specific business-oriented name.
