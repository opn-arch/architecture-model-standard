# Pipeline Report: System-of-Systems

**Generated:** 2026-08-11T17:18:22Z
**Total Duration:** 3294ms
**Stages:** 8

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 3108ms | 0 |
| infer | 87 | 1ms | 0 |
| allocate | 100 | 18ms | 0 |
| contract | 76 | 1ms | 0 |
| relate | 100 | 166ms | 0 |
| specify | 50 | 0ms | 0 |
| decompose | 100.0 | 0ms | 0 |
| validate | 80 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 3108ms

### Deterministic Findings
- Discovered 305 modules
- 1132 functions, 457 classes
- 0 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- dynamic_import: Dynamic import in src/architecture_model/pipeline/cache.py:66

## Stage: infer
**Score:** 87 | **Duration:** 1ms

### Deterministic Findings
- Inferred 44 capabilities
- 1 actors
- 0 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- ambiguous_module: src/architecture_model/patterns.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/__main__.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/coordinator.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/lessons.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/cache.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/context_gen.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/emit_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/artifacts.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/emit.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/report.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/compression.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/source_block_assign.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/cluster.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/interfaces.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/metrics.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/chains.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/scanner.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/slicers.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/multi_scanner.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/scan_cache.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/display.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/kt_scanner.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/generator.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/blocks.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/ts_scanner.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/authoring/gate.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/use_case_inference.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/capability_inference.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/enrichment_context.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/trigger_detection.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/compaction.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/behavior_decompose.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/naming_context.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/from_code.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/from_artifacts.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/constraint_detector.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/route_detector.py has no clear capability affiliation

## Stage: allocate
**Score:** 100 | **Duration:** 18ms

### Deterministic Findings
- 47 components
- File coverage: 10000%
- 0 unallocated files

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: contract
**Score:** 76 | **Duration:** 1ms

### Deterministic Findings
- 121 contracts

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: relate
**Score:** 100 | **Duration:** 166ms

### Deterministic Findings
- 482 depends-on relationships
- 47 contains relationships
- 46 realizes relationships

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: specify
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 13 interfaces

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: decompose
**Score:** 100.0 | **Duration:** 0ms

### Deterministic Findings
- 4 systems
- 43 inline components
- 482 inter-system edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: validate
**Score:** 80 | **Duration:** 0ms

### Deterministic Findings
- Score: 80/100
- 4 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*
