# Component: Core (COMP-CORE)

**Status:** Status.ACTIVE
**Description:** Domain model types, parser, validator, slicer, differ, merger, coverage, confidence

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/core/types.py` | — | — |
| `src/architecture_model/core/parser.py` | — | — |
| `src/architecture_model/core/validator.py` | — | — |
| `src/architecture_model/core/slicer.py` | — | — |
| `src/architecture_model/core/differ.py` | — | — |
| `src/architecture_model/core/merger.py` | — | — |
| `src/architecture_model/core/coverage.py` | — | — |
| `src/architecture_model/core/confidence.py` | — | — |
| `src/architecture_model/core/compression.py` | — | — |
| `src/architecture_model/core/corrections.py` | — | — |
| `src/architecture_model/core/cluster.py` | — | — |
| `src/architecture_model/core/decomposer.py` | — | — |
| `src/architecture_model/core/representativeness.py` | — | — |
| `src/architecture_model/core/regen_readiness.py` | — | — |
| `src/architecture_model/core/source_block_assign.py` | — | — |
| `src/architecture_model/core/source_block_quality.py` | — | — |
| `src/architecture_model/core/test_affinity.py` | — | — |
| `src/architecture_model/core/visualize.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-PARSE | realizes | — |
| CAP-VALIDATE | realizes | — |
| CAP-SLICE | realizes | — |
| CAP-DIFF | realizes | — |
| CAP-COVERAGE | realizes | — |
| COMP-CONFIG (Config) | depends-on | — |
| IF-PYTHON-API | exposes | — |
| IF-YAML-SCHEMA | exposes | — |
| BEH-REGEN-SCORE | traces-to | — |
| CON-NO-LLM | constrained-by | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-CORE | contains | — |
| COMP-CLI (CLI) | depends-on | — |
| COMP-ORCHESTRATION (Orchestration) | depends-on | — |
| COMP-PIPELINE (Pipeline) | depends-on | — |
| COMP-EXTRACT (Extract) | depends-on | — |
| COMP-DOCS (Docs) | depends-on | — |
| COMP-EXPORT (Export) | depends-on | — |
| COMP-INTEGRATIONS (Integrations) | depends-on | — |
| COMP-AUTHORING (Authoring) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Manifest (COMP-MANIFEST)

**Status:** Status.ACTIVE
**Description:** Reality manifest generator: AST scanning, metrics, blocks, interfaces, body hints

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/manifest/__init__.py` | — | — |
| `src/architecture_model/manifest/types.py` | — | — |
| `src/architecture_model/manifest/protocol.py` | — | — |
| `src/architecture_model/manifest/scanner.py` | — | — |
| `src/architecture_model/manifest/generator.py` | — | — |
| `src/architecture_model/manifest/blocks.py` | — | — |
| `src/architecture_model/manifest/body_hints.py` | — | — |
| `src/architecture_model/manifest/interfaces.py` | — | — |
| `src/architecture_model/manifest/grouping.py` | — | — |
| `src/architecture_model/manifest/metrics.py` | — | — |
| `src/architecture_model/manifest/recursive.py` | — | — |
| `src/architecture_model/manifest/behavior.py` | — | — |
| `src/architecture_model/manifest/call_graph.py` | — | — |
| `src/architecture_model/manifest/chains.py` | — | — |
| `src/architecture_model/manifest/display.py` | — | — |
| `src/architecture_model/manifest/slicers.py` | — | — |
| `src/architecture_model/manifest/test_analyzer.py` | — | — |
| `src/architecture_model/manifest/scan_cache.py` | — | — |
| `src/architecture_model/manifest/kt_scanner.py` | — | — |
| `src/architecture_model/manifest/ts_scanner.py` | — | — |
| `src/architecture_model/manifest/multi_scanner.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-MANIFEST | realizes | — |
| COMP-CONFIG (Config) | depends-on | — |
| COMP-UTILS (Utils) | depends-on | — |
| IF-MANIFEST-JSON | exposes | — |
| CON-NO-LLM | constrained-by | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-MANIFEST | contains | — |
| COMP-CLI (CLI) | depends-on | — |
| COMP-ORCHESTRATION (Orchestration) | depends-on | — |
| COMP-PIPELINE (Pipeline) | depends-on | — |
| COMP-EXTRACT (Extract) | depends-on | — |
| COMP-DOCS (Docs) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Pipeline (COMP-PIPELINE)

**Status:** Status.ACTIVE
**Description:** 7-stage modular extraction pipeline with DAG coordinator and learning store

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/pipeline/__init__.py` | — | — |
| `src/architecture_model/pipeline/protocol.py` | — | — |
| `src/architecture_model/pipeline/coordinator.py` | — | — |
| `src/architecture_model/pipeline/observe.py` | — | — |
| `src/architecture_model/pipeline/observe_types.py` | — | — |
| `src/architecture_model/pipeline/infer.py` | — | — |
| `src/architecture_model/pipeline/infer_types.py` | — | — |
| `src/architecture_model/pipeline/allocate.py` | — | — |
| `src/architecture_model/pipeline/allocate_types.py` | — | — |
| `src/architecture_model/pipeline/relate.py` | — | — |
| `src/architecture_model/pipeline/relate_types.py` | — | — |
| `src/architecture_model/pipeline/specify.py` | — | — |
| `src/architecture_model/pipeline/specify_types.py` | — | — |
| `src/architecture_model/pipeline/contract.py` | — | — |
| `src/architecture_model/pipeline/contract_types.py` | — | — |
| `src/architecture_model/pipeline/validate.py` | — | — |
| `src/architecture_model/pipeline/validate_types.py` | — | — |
| `src/architecture_model/pipeline/learning.py` | — | — |
| `src/architecture_model/pipeline/artifacts.py` | — | — |
| `src/architecture_model/pipeline/context_gen.py` | — | — |
| `src/architecture_model/pipeline/corrections.py` | — | — |
| `src/architecture_model/pipeline/regen_score.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-PIPELINE | realizes | — |
| CAP-REGEN | realizes | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |
| IF-PIPELINE-ARTIFACTS | exposes | — |
| BEH-PIPELINE | traces-to | — |
| CON-NO-LLM | constrained-by | — |
| CON-PERF | constrained-by | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-PIPELINE | contains | — |
| COMP-CLI (CLI) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Orchestration (COMP-ORCHESTRATION)

**Status:** Status.ACTIVE
**Description:** High-level workflows: enrichment, decomposition, behavior flows, capability inference

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/orchestration/__init__.py` | — | — |
| `src/architecture_model/orchestration/auto_enrich.py` | — | — |
| `src/architecture_model/orchestration/behavior_decompose.py` | — | — |
| `src/architecture_model/orchestration/behavior_flows.py` | — | — |
| `src/architecture_model/orchestration/capability_inference.py` | — | — |
| `src/architecture_model/orchestration/compaction.py` | — | — |
| `src/architecture_model/orchestration/decompose.py` | — | — |
| `src/architecture_model/orchestration/deep_decompose.py` | — | — |
| `src/architecture_model/orchestration/enrich.py` | — | — |
| `src/architecture_model/orchestration/enrichment_context.py` | — | — |
| `src/architecture_model/orchestration/full_extraction.py` | — | — |
| `src/architecture_model/orchestration/naming_context.py` | — | — |
| `src/architecture_model/orchestration/pipeline.py` | — | — |
| `src/architecture_model/orchestration/trigger_detection.py` | — | — |
| `src/architecture_model/orchestration/use_case_inference.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-ENRICH | realizes | — |
| CAP-DECOMPOSE | realizes | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| BEH-ENRICH | traces-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-ORCHESTRATION | contains | — |
| COMP-CLI (CLI) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: CLI (COMP-CLI)

**Status:** Status.ACTIVE
**Description:** Command-line interface: argparse setup, command handlers, visualization

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/cli/__init__.py` | — | — |
| `src/architecture_model/cli/main.py` | — | — |
| `src/architecture_model/cli/visualize.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-CORE (Core) | depends-on | — |
| COMP-ORCHESTRATION (Orchestration) | depends-on | — |
| COMP-PIPELINE (Pipeline) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |
| IF-CLI | exposes | — |
| BEH-INIT | traces-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-CLI | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Extract (COMP-EXTRACT)

**Status:** Status.ACTIVE
**Description:** Model extraction from code/artifacts: route detection, constraint detection

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/extract/__init__.py` | — | — |
| `src/architecture_model/extract/from_code.py` | — | — |
| `src/architecture_model/extract/from_artifacts.py` | — | — |
| `src/architecture_model/extract/route_detector.py` | — | — |
| `src/architecture_model/extract/constraint_detector.py` | — | — |
| `src/architecture_model/extract/table_parser.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-EXTRACT | realizes | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |
| COMP-CONFIG (Config) | depends-on | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-CORE | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Docs (COMP-DOCS)

**Status:** Status.ACTIVE
**Description:** Documentation generators: component specs, ICDs, diagrams, health reports

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/docs/__init__.py` | — | — |
| `src/architecture_model/docs/behavior_spec.py` | — | — |
| `src/architecture_model/docs/component_spec.py` | — | — |
| `src/architecture_model/docs/dependency_matrix.py` | — | — |
| `src/architecture_model/docs/diagrams.py` | — | — |
| `src/architecture_model/docs/drift.py` | — | — |
| `src/architecture_model/docs/generator.py` | — | — |
| `src/architecture_model/docs/health.py` | — | — |
| `src/architecture_model/docs/icd.py` | — | — |
| `src/architecture_model/docs/index.py` | — | — |
| `src/architecture_model/docs/integration_flows.py` | — | — |
| `src/architecture_model/docs/system_design.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-DOCS | realizes | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-ORCHESTRATION | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Export (COMP-EXPORT)

**Status:** Status.ACTIVE
**Description:** Flat file export for mobile AI: concat sub-models, docs, diagrams, skills

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/export/__init__.py` | — | — |
| `src/architecture_model/export/flatfiles.py` | — | — |
| `src/architecture_model/export/reference.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-EXPORT | realizes | — |
| COMP-CORE (Core) | depends-on | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Config (COMP-CONFIG)

**Status:** Status.ACTIVE
**Description:** Project configuration: auto-discovery, schema definition, file loading

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/config/__init__.py` | — | — |
| `src/architecture_model/config/loader.py` | — | — |
| `src/architecture_model/config/schema.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-CONFIG | realizes | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |
| COMP-CLI (CLI) | depends-on | — |
| COMP-PIPELINE (Pipeline) | depends-on | — |
| COMP-EXTRACT (Extract) | depends-on | — |
| COMP-CORE (Core) | depends-on | — |
| COMP-MANIFEST (Manifest) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Authoring (COMP-AUTHORING)

**Status:** Status.ACTIVE
**Description:** Forward authoring: parse requirements into models, development gate checks

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/authoring/__init__.py` | — | — |
| `src/architecture_model/authoring/parser.py` | — | — |
| `src/architecture_model/authoring/gate.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-AUTHOR | realizes | — |
| COMP-CORE (Core) | depends-on | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-ORCHESTRATION | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Utils (COMP-UTILS)

**Status:** Status.ACTIVE
**Description:** Shared utilities: file discovery, exclusion patterns

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/utils/__init__.py` | — | — |
| `src/architecture_model/utils/discovery.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |
| COMP-MANIFEST (Manifest) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Profiles (COMP-PROFILES)

**Status:** Status.ACTIVE
**Description:** Domain profile system: schema extensions for controls, mechanical, electrical

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/profiles/__init__.py` | — | — |
| `src/architecture_model/profiles/schema.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-PROFILES | realizes | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Monitoring (COMP-MONITORING)

**Status:** Status.ACTIVE
**Description:** Runtime monitoring and health checks

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/monitoring.py` | — | — |
| `src/architecture_model/monitoring_checks.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Persistence (COMP-PERSISTENCE)

**Status:** Status.ACTIVE
**Description:** Vector store for architecture model storage

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/persistence/__init__.py` | — | — |
| `src/architecture_model/persistence/store.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Integrations (COMP-INTEGRATIONS)

**Status:** Status.ACTIVE
**Description:** LLM context formatting, pipeline bridge for MCP consumption

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/integrations/__init__.py` | — | — |
| `src/architecture_model/integrations/llm_context.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-CORE (Core) | depends-on | — |
| BEH-LLM-LOAD | traces-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-ORCHESTRATION | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%
