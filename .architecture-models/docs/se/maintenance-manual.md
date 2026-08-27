---
document: Maintenance Manual
system: architecture-model-standard
system_id: SYS-unknown
generated_at: 2026-08-27T14:23:21Z
generator_version: 0.3.0
model_hash: 08abc716587d
edition: 9
---

# Maintenance Manual: architecture-model-standard

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Core (COMP-1) | library | foundation | 1 | 0 | 0 |
| Type System (COMP-1.1) | library | foundation | 1 | 0 | 0 |
| Validation (COMP-1.2) | library | foundation | 2 | 0 | 0 |
| Parser & Persistence (COMP-1.3) | library | foundation | 5 | 0 | 0 |
| Model Operations (COMP-1.4) | library | foundation | 8 | 0 | 0 |
| Quality Metrics (COMP-1.5) | library | foundation | 5 | 0 | 0 |
| Pipeline (COMP-2) | service | domain | 1 | 0 | 0 |
| Pipeline Coordination (COMP-2.1) | service | domain | 7 | 0 | 0 |
| Observation Stages (COMP-2.2) | service | domain | 4 | 0 | 0 |
| Allocation & Relation Stages (COMP-2.3) | service | domain | 4 | 0 | 0 |
| Specification & Contract Stages (COMP-2.4) | service | domain | 6 | 0 | 0 |
| Synthesis & Emit Stages (COMP-2.5) | service | domain | 7 | 0 | 0 |
| Manifest (COMP-3) | library | domain | 2 | 0 | 0 |
| Scanners (COMP-3.1) | library | domain | 8 | 0 | 0 |
| Graph & Analysis (COMP-3.2) | library | domain | 5 | 0 | 0 |
| Grouping & Generation (COMP-3.3) | library | domain | 6 | 0 | 0 |
| Documentation (COMP-4) | library | application | 1 | 0 | 0 |
| Core Doc Generators (COMP-4.1) | library | application | 11 | 0 | 0 |
| SE Document Suite (COMP-4.2) | library | application | 21 | 0 | 0 |
| Orchestration (COMP-5) | service | application | 1 | 0 | 0 |
| Enrichment (COMP-5.1) | service | application | 7 | 0 | 0 |
| Decomposition (COMP-5.2) | service | application | 6 | 0 | 0 |
| Extract (COMP-6) | library | domain | 5 | 0 | 0 |
| Authoring (COMP-7) | library | application | 3 | 0 | 0 |
| CLI (COMP-8) | service | interface | 5 | 0 | 0 |
| Configuration (COMP-9) | library | infrastructure | 6 | 0 | 0 |
| Export (COMP-10) | library | application | 3 | 0 | 0 |
| Pipeline Learning (COMP-11) | library | domain | 3 | 0 | 0 |
| Utilities (COMP-12) | library | infrastructure | 6 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Core | — | CLI | LOW |
| Type System | — | Pipeline Coordination, Allocation & Relation Stages, Core Doc Generators, Enrichment, Authoring | HIGH |
| Validation | — | Specification & Contract Stages | LOW |
| Parser & Persistence | — | Synthesis & Emit Stages, Export | MEDIUM |
| Model Operations | — | — | LOW |
| Quality Metrics | — | Decomposition | LOW |
| Pipeline | — | CLI | LOW |
| Pipeline Coordination | Type System | — | LOW |
| Observation Stages | Scanners | — | LOW |
| Allocation & Relation Stages | Type System | — | LOW |
| Specification & Contract Stages | Validation | — | LOW |
| Synthesis & Emit Stages | Parser & Persistence | — | LOW |
| Manifest | — | Enrichment, Authoring, CLI | MEDIUM |
| Scanners | Configuration | Observation Stages, Graph & Analysis, Extract | MEDIUM |
| Graph & Analysis | Scanners | Grouping & Generation | LOW |
| Grouping & Generation | Graph & Analysis | — | LOW |
| Documentation | — | CLI | LOW |
| Core Doc Generators | Type System | SE Document Suite | LOW |
| SE Document Suite | Core Doc Generators | — | LOW |
| Orchestration | — | CLI | LOW |
| Enrichment | Manifest, Type System | — | LOW |
| Decomposition | Quality Metrics | — | LOW |
| Extract | Scanners, Configuration | — | LOW |
| Authoring | Type System, Manifest | CLI | LOW |
| CLI | Core, Pipeline, Manifest, Documentation, Orchestration, Authoring | — | LOW |
| Configuration | — | Scanners, Extract, Pipeline Learning, Utilities | MEDIUM |
| Export | Parser & Persistence | — | LOW |
| Pipeline Learning | Configuration | — | LOW |
| Utilities | Configuration | — | LOW |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Core (COMP-1)

**Files:**
- `src/architecture_model/core/__init__.py`
**Downstream dependents (must re-test):** CLI

### Type System (COMP-1.1)

**Files:**
- `src/architecture_model/core/types.py`
**Downstream dependents (must re-test):** Pipeline Coordination, Allocation & Relation Stages, Core Doc Generators, Enrichment, Authoring

### Validation (COMP-1.2)

**Files:**
- `src/architecture_model/core/validator.py`
- `src/architecture_model/spec/__init__.py`
**Downstream dependents (must re-test):** Specification & Contract Stages

### Parser & Persistence (COMP-1.3)

**Files:**
- `src/architecture_model/core/parser.py`
- `src/architecture_model/core/compression.py`
- `src/architecture_model/core/merger.py`
- `src/architecture_model/persistence/__init__.py`
- `src/architecture_model/persistence/store.py`
**Downstream dependents (must re-test):** Synthesis & Emit Stages, Export

### Model Operations (COMP-1.4)

**Files:**
- `src/architecture_model/core/slicer.py`
- `src/architecture_model/core/differ.py`
- `src/architecture_model/core/coverage.py`
- `src/architecture_model/core/cluster.py`
- `src/architecture_model/core/source_block_assign.py`
- `src/architecture_model/core/source_block_quality.py`
- `src/architecture_model/core/representativeness.py`
- `src/architecture_model/core/test_affinity.py`

### Quality Metrics (COMP-1.5)

**Files:**
- `src/architecture_model/core/confidence.py`
- `src/architecture_model/core/regen_readiness.py`
- `src/architecture_model/core/corrections.py`
- `src/architecture_model/core/decomposer.py`
- `src/architecture_model/core/visualize.py`
**Downstream dependents (must re-test):** Decomposition

### Pipeline (COMP-2)

**Files:**
- `src/architecture_model/pipeline/__init__.py`
**Downstream dependents (must re-test):** CLI

### Pipeline Coordination (COMP-2.1)

**Files:**
- `src/architecture_model/pipeline/coordinator.py`
- `src/architecture_model/pipeline/protocol.py`
- `src/architecture_model/pipeline/cache.py`
- `src/architecture_model/pipeline/context_gen.py`
- `src/architecture_model/pipeline/report.py`
- `src/architecture_model/pipeline/artifacts.py`
- `src/architecture_model/pipeline/corrections.py`

### Observation Stages (COMP-2.2)

**Files:**
- `src/architecture_model/pipeline/observe.py`
- `src/architecture_model/pipeline/observe_types.py`
- `src/architecture_model/pipeline/infer.py`
- `src/architecture_model/pipeline/infer_types.py`

### Allocation & Relation Stages (COMP-2.3)

**Files:**
- `src/architecture_model/pipeline/allocate.py`
- `src/architecture_model/pipeline/allocate_types.py`
- `src/architecture_model/pipeline/relate.py`
- `src/architecture_model/pipeline/relate_types.py`

### Specification & Contract Stages (COMP-2.4)

**Files:**
- `src/architecture_model/pipeline/specify.py`
- `src/architecture_model/pipeline/specify_types.py`
- `src/architecture_model/pipeline/contract.py`
- `src/architecture_model/pipeline/contract_types.py`
- `src/architecture_model/pipeline/validate.py`
- `src/architecture_model/pipeline/validate_types.py`

### Synthesis & Emit Stages (COMP-2.5)

**Files:**
- `src/architecture_model/pipeline/decompose.py`
- `src/architecture_model/pipeline/decompose_types.py`
- `src/architecture_model/pipeline/synthesize.py`
- `src/architecture_model/pipeline/synthesize_types.py`
- `src/architecture_model/pipeline/emit.py`
- `src/architecture_model/pipeline/emit_types.py`
- `src/architecture_model/pipeline/regen_score.py`

### Manifest (COMP-3)

**Files:**
- `src/architecture_model/manifest/__init__.py`
- `src/architecture_model/manifest/types.py`
**Downstream dependents (must re-test):** Enrichment, Authoring, CLI

### Scanners (COMP-3.1)

**Files:**
- `src/architecture_model/manifest/scanner.py`
- `src/architecture_model/manifest/multi_scanner.py`
- `src/architecture_model/manifest/ts_scanner.py`
- `src/architecture_model/manifest/kt_scanner.py`
- `src/architecture_model/manifest/body_hints.py`
- `src/architecture_model/manifest/metrics.py`
- `src/architecture_model/manifest/scan_cache.py`
- `src/architecture_model/manifest/protocol.py`
**Downstream dependents (must re-test):** Observation Stages, Graph & Analysis, Extract

### Graph & Analysis (COMP-3.2)

**Files:**
- `src/architecture_model/manifest/call_graph.py`
- `src/architecture_model/manifest/interfaces.py`
- `src/architecture_model/manifest/behavior.py`
- `src/architecture_model/manifest/chains.py`
- `src/architecture_model/manifest/test_analyzer.py`
**Downstream dependents (must re-test):** Grouping & Generation

### Grouping & Generation (COMP-3.3)

**Files:**
- `src/architecture_model/manifest/grouping.py`
- `src/architecture_model/manifest/generator.py`
- `src/architecture_model/manifest/recursive.py`
- `src/architecture_model/manifest/blocks.py`
- `src/architecture_model/manifest/slicers.py`
- `src/architecture_model/manifest/display.py`

### Documentation (COMP-4)

**Files:**
- `src/architecture_model/docs/__init__.py`
**Downstream dependents (must re-test):** CLI

### Core Doc Generators (COMP-4.1)

**Files:**
- `src/architecture_model/docs/generator.py`
- `src/architecture_model/docs/component_spec.py`
- `src/architecture_model/docs/icd.py`
- `src/architecture_model/docs/dependency_matrix.py`
- `src/architecture_model/docs/health.py`
- `src/architecture_model/docs/drift.py`
- `src/architecture_model/docs/diagrams.py`
- `src/architecture_model/docs/index.py`
- `src/architecture_model/docs/behavior_spec.py`
- `src/architecture_model/docs/integration_flows.py`
- `src/architecture_model/docs/system_design.py`
**Downstream dependents (must re-test):** SE Document Suite

### SE Document Suite (COMP-4.2)

**Files:**
- `src/architecture_model/docs/se/__init__.py`
- `src/architecture_model/docs/se/generator.py`
- `src/architecture_model/docs/se/frontmatter.py`
- `src/architecture_model/docs/se/detect.py`
- `src/architecture_model/docs/se/conops.py`
- `src/architecture_model/docs/se/functional_analysis.py`
- `src/architecture_model/docs/se/logical_architecture.py`
- `src/architecture_model/docs/se/requirements_analysis.py`
- `src/architecture_model/docs/se/use_cases.py`
- `src/architecture_model/docs/se/verification_validation.py`
- `src/architecture_model/docs/se/interface_spec.py`
- `src/architecture_model/docs/se/operations_manual.py`
- `src/architecture_model/docs/se/maintenance_manual.py`
- `src/architecture_model/docs/se/risk_assessment.py`
- `src/architecture_model/docs/se/security_analysis.py`
- `src/architecture_model/docs/se/data_model.py`
- `src/architecture_model/docs/se/deployment_guide.py`
- `src/architecture_model/docs/se/api_reference.py`
- `src/architecture_model/docs/se/cli_reference.py`
- `src/architecture_model/docs/se/changelog.py`
- *...and 1 more files*

### Orchestration (COMP-5)

**Files:**
- `src/architecture_model/orchestration/__init__.py`
**Downstream dependents (must re-test):** CLI

### Enrichment (COMP-5.1)

**Files:**
- `src/architecture_model/orchestration/enrich.py`
- `src/architecture_model/orchestration/auto_enrich.py`
- `src/architecture_model/orchestration/enrichment_context.py`
- `src/architecture_model/orchestration/capability_inference.py`
- `src/architecture_model/orchestration/trigger_detection.py`
- `src/architecture_model/orchestration/use_case_inference.py`
- `src/architecture_model/orchestration/naming_context.py`

### Decomposition (COMP-5.2)

**Files:**
- `src/architecture_model/orchestration/decompose.py`
- `src/architecture_model/orchestration/deep_decompose.py`
- `src/architecture_model/orchestration/behavior_decompose.py`
- `src/architecture_model/orchestration/behavior_flows.py`
- `src/architecture_model/orchestration/compaction.py`
- `src/architecture_model/orchestration/pipeline.py`

### Extract (COMP-6)

**Files:**
- `src/architecture_model/extract/from_code.py`
- `src/architecture_model/extract/from_artifacts.py`
- `src/architecture_model/extract/route_detector.py`
- `src/architecture_model/extract/constraint_detector.py`
- `src/architecture_model/extract/table_parser.py`

### Authoring (COMP-7)

**Files:**
- `src/architecture_model/authoring/__init__.py`
- `src/architecture_model/authoring/parser.py`
- `src/architecture_model/authoring/gate.py`
**Downstream dependents (must re-test):** CLI

### CLI (COMP-8)

**Files:**
- `src/architecture_model/__init__.py`
- `src/architecture_model/__main__.py`
- `src/architecture_model/cli/__init__.py`
- `src/architecture_model/cli/main.py`
- `src/architecture_model/cli/visualize.py`

### Configuration (COMP-9)

**Files:**
- `src/architecture_model/config/__init__.py`
- `src/architecture_model/config/loader.py`
- `src/architecture_model/config/schema.py`
- `src/architecture_model/profiles/__init__.py`
- `src/architecture_model/profiles/builtins/__init__.py`
- `src/architecture_model/profiles/schema.py`
**Downstream dependents (must re-test):** Scanners, Extract, Pipeline Learning, Utilities

### Export (COMP-10)

**Files:**
- `src/architecture_model/export/__init__.py`
- `src/architecture_model/export/flatfiles.py`
- `src/architecture_model/export/reference.py`

### Pipeline Learning (COMP-11)

**Files:**
- `src/architecture_model/pipeline/global_learning.py`
- `src/architecture_model/pipeline/learning.py`
- `src/architecture_model/pipeline/lessons.py`

### Utilities (COMP-12)

**Files:**
- `src/architecture_model/utils/__init__.py`
- `src/architecture_model/utils/discovery.py`
- `src/architecture_model/monitoring.py`
- `src/architecture_model/monitoring_checks.py`
- `src/architecture_model/patterns.py`
- `src/architecture_model/data/__init__.py`

## Known Constraints

*No constraint allocations defined.*
