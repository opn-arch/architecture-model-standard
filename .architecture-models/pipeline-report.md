# Pipeline Report: architecture-model-standard

**Generated:** 2026-08-18T23:36:29Z
**Total Duration:** 39206ms
**Stages:** 9

## LLM Summary

| Metric | Value |
|--------|-------|
| Total Calls | 8 |
| Total Tokens | 0 (prompt: 0, completion: 0) |
| Models Used | unknown |
| Cache Hits | 0/8 |
| Total LLM Duration | 17,977ms |

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 6998ms | 0 |
| infer | 67 | 2ms | 5 |
| allocate | 75 | 0ms | 3 |
| contract | 100 | 1ms | 0 |
| relate | 100 | 235ms | 0 |
| specify | 50 | 0ms | 0 |
| decompose | 100.0 | 0ms | 0 |
| validate | 80 | 0ms | 0 |
| synthesize | 100.0 | 31970ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 6998ms

### Deterministic Findings
- Discovered 348 modules
- 1274 functions, 504 classes
- 635 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- dynamic_import: Dynamic import in src/architecture_model/pipeline/cache.py:73
- dynamic_import: Dynamic import in src/architecture_model/docs/se/generator.py:72

## Stage: infer
**Score:** 67 | **Duration:** 2ms

### Deterministic Findings
- Inferred 6 capabilities
- 1 actors
- 25 behaviors

### LLM Calls (5)

#### 1. Given a software component with these files: routes, suggest a specific, descriptive name (2-4 words (2,116ms)
- **Tokens:** 0 prompt (0 context) → 0 completion = 0 total
- **Result:** 1 items produced (confidence: 0.70)

#### 2. Given a software component with these files: package_group, suggest a specific, descriptive name (2- (2,109ms)
- **Tokens:** 0 prompt (0 context) → 0 completion = 0 total
- **Result:** 1 items produced (confidence: 0.70)

#### 3. Given a software component with these files: package_group, suggest a specific, descriptive name (2- (2,322ms)
- **Tokens:** 0 prompt (0 context) → 0 completion = 0 total
- **Result:** 1 items produced (confidence: 0.70)

#### 4. Given a software component with these files: cli_pattern, suggest a specific, descriptive name (2-4  (2,019ms)
- **Tokens:** 0 prompt (0 context) → 0 completion = 0 total
- **Result:** 1 items produced (confidence: 0.70)

#### 5. Given a software component with these files: cli_pattern, suggest a specific, descriptive name (2-4  (2,068ms)
- **Tokens:** 0 prompt (0 context) → 0 completion = 0 total
- **Result:** 1 items produced (confidence: 0.70)

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: scripts/test_enriched_round_trip.py has 11 public functions with 9 cross-calls — likely contains workflow patterns
- complex_behavior: scripts/test_round_trip.py has 14 public functions with 13 cross-calls — likely contains workflow patterns
- complex_behavior: scripts/test_decomposed_round_trip.py has 10 public functions with 9 cross-calls — likely contains workflow patterns
- complex_behavior: src/architecture_model/export/flatfiles.py has 11 public functions with 10 cross-calls — likely contains workflow patterns
- ambiguous_module: scripts/strip_sub_behaviors.py has no clear capability affiliation
- ambiguous_module: scripts/generate_models_pdf.py has no clear capability affiliation
- ambiguous_module: scripts/se_enrich.py has no clear capability affiliation
- ambiguous_module: scripts/bench_enrichment.py has no clear capability affiliation
- ambiguous_module: scripts/add_sub_behaviors.py has no clear capability affiliation
- ambiguous_module: scripts/enrich_sub_behaviors.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/patterns.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/monitoring.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/monitoring_checks.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/__main__.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/observe_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/synthesize_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/decompose_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/coordinator.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/global_learning.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/lessons.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/contract_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/decompose.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/allocate_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/validate_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/regen_score.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/allocate.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/protocol.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/cache.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/specify_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/specify.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/synthesize.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/context_gen.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/validate.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/observe.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/relate_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/corrections.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/emit_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/requirements_derive.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/infer.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/artifacts.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/relate.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/learning.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/emit.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/contract.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/report.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/pipeline/infer_types.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/validator.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/regen_readiness.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/confidence.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/representativeness.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/compression.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/differ.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/coverage.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/visualize.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/parser.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/completeness.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/source_block_assign.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/cluster.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/corrections.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/decomposer.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/slicer.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/source_block_quality.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/core/merger.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/config/loader.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/config/schema.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/interfaces.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/metrics.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/chains.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/scanner.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/slicers.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/behavior.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/multi_scanner.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/scan_cache.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/grouping.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/recursive.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/protocol.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/display.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/kt_scanner.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/generator.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/call_graph.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/body_hints.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/blocks.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/manifest/ts_scanner.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/utils/discovery.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/cli/visualize.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/authoring/parser.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/authoring/gate.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/persistence/store.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/use_case_inference.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/auto_enrich.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/decompose.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/enrich.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/capability_inference.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/enrichment_context.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/trigger_detection.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/deep_decompose.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/pipeline.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/compaction.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/behavior_flows.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/behavior_decompose.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/orchestration/naming_context.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/from_code.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/from_artifacts.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/constraint_detector.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/table_parser.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/extract/route_detector.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/profiles/schema.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/export/flatfiles.py has no clear capability affiliation
- ambiguous_module: src/architecture_model/export/reference.py has no clear capability affiliation
- ambiguous_module: scripts/dev_simulation/regen_scorer.py has no clear capability affiliation
- ambiguous_module: scripts/dev_simulation/cohesion.py has no clear capability affiliation
- ambiguous_module: scripts/dev_simulation/extractor.py has no clear capability affiliation
- ambiguous_module: scripts/dev_simulation/drift_tracker.py has no clear capability affiliation
- ambiguous_module: scripts/dev_simulation/slice_evaluator.py has no clear capability affiliation
- ambiguous_module: scripts/dev_simulation/checkout.py has no clear capability affiliation
- ambiguous_module: scripts/dev_simulation/llm_predictor.py has no clear capability affiliation
- ambiguous_module: scripts/dev_simulation/report.py has no clear capability affiliation

## Stage: allocate
**Score:** 75 | **Duration:** 0ms

### Deterministic Findings
- 15 components
- File coverage: 10000%
- 0 unallocated files

### LLM Calls (3)

#### 1. Given a software component containing files: [src/architecture_model/__init__.py, src/architecture_m (3,196ms)
- **Tokens:** 0 prompt (0 context) → 0 completion = 0 total
- **Result:** 1 items produced (confidence: 0.70)

#### 2. Given a software component containing files: [src/architecture_model/core/cluster.py, src/architectu (2,162ms)
- **Tokens:** 0 prompt (0 context) → 0 completion = 0 total
- **Result:** 1 items produced (confidence: 0.70)

#### 3. Given a software component containing files: [src/architecture_model/cli/main.py, src/architecture_m (1,985ms)
- **Tokens:** 0 prompt (0 context) → 0 completion = 0 total
- **Result:** 1 items produced (confidence: 0.70)

### Diagnostics
*(none)*

## Stage: contract
**Score:** 100 | **Duration:** 1ms

### Deterministic Findings
- 142 contracts

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: relate
**Score:** 100 | **Duration:** 235ms

### Deterministic Findings
- 41 depends-on relationships
- 15 realizes relationships
- 15 contains relationships
- 3 uses relationships

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

## Stage: decompose
**Score:** 100.0 | **Duration:** 0ms

### Deterministic Findings
- 8 systems
- 7 inline components
- 42 inter-system edges

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

### Uncertainties
- generic_capability_name: Capability 'Web Routes' (CAP-1) has a generic name. LLM analysis could produce a more specific business-oriented name.

## Stage: synthesize
**Score:** 100.0 | **Duration:** 31970ms

### Deterministic Findings
*(none)*

### LLM Calls
*(none)*

### Diagnostics
*(none)*
