# Deep Gap Analysis Report

**Repository:** /Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp
**Generated:** 2026-08-27 21:35:35 UTC

## Stage: infer

### Summary

| Metric | Value |
|--------|------:|
| pipeline_caps | 5 |
| llm_caps | 75 |
| pipeline_behaviors | 52 |
| llm_behaviors | 36 |

### Decision Chain

#### 1. `_infer_from_routes` (infer.py:265)

**Checks:** Check inventory.routes for URL patterns
**Result:** 0 routes found → SKIPPED
**Assessment:** ✅ Correct

#### 2. `_infer_from_triggers` (infer.py:300)

**Checks:** Scan imports for trigger keywords (websocket, grpc, celery, etc.)
**Result:** Found: ['proto']
**Assessment:** ✅ Correct

#### 3. `_infer_from_domain_modules` (infer.py:180)

**Checks:** Transform non-test, non-init module stems into capabilities
**Result:** 5 capabilities created
**Assessment:** ✅ Correct
**Entities created:** gRPC Services, Scripts, Src, CLI Runner, CLI Main, conftest, strip_sub_behaviors, generate_models_pdf, se_enrich, bench_enrichment, add_sub_behaviors, enrich_sub_behaviors, se_doc_model, regen_scorer, runner, cohesion, extractor, drift_tracker, slice_evaluator, cli, checkout, llm_predictor, report, patterns, monitoring, monitoring_checks, __main__, observe_types, synthesize_types, decompose_types, coordinator, global_learning, review_store, gap_report, lessons, contract_types, decompose, allocate_types, validate_types, regen_score, auto_correct, allocate, protocol, cache, specify_types, gates, stage_tracer, specify, synthesize, context_gen, validate, observe, relate_types, corrections, emit_types, requirements_derive, reconstruct_behaviors, infer, artifacts, gap_prompts, relate, llm_provider, learning, emit, contract, report, infer_types, gap_analysis, stage_review, validator, regen_readiness, cross_repo, confidence, budget, representativeness, compression, differ, coverage, types, visualize, review, parser, completeness, changelog, propagation, source_block_assign, cluster, corrections, detail_level, decomposer, slicer, source_block_quality, merger, regen_readiness, code_prompts, confidence, code_review, monitoring, coverage, dashboard, code_safety, orchestrator, update_summary, monitoring_checks, code_improver, model_feedback, loader, schema, interfaces, metrics, chains, scanner, slicers, behavior, multi_scanner, scan_cache, grouping, recursive, protocol, types, display, kt_scanner, generator, call_graph, body_hints, blocks, ts_scanner, discovery, behavior_spec, index, health, dependency_matrix, drift, icd, generator, diagrams, component_spec, integration_flows, system_design, visualize, main, parser, gate, store, use_case_inference, auto_enrich, decompose, enrich, capability_inference, enrichment_context, trigger_detection, deep_decompose, pipeline, compaction, behavior_flows, behavior_decompose, naming_context, from_code, from_artifacts, constraint_detector, table_parser, route_detector, schema, flatfiles, reference, operations_manual, interface_spec, functional_analysis, frontmatter, deployment_guide, logical_architecture, verification_validation, maintenance_manual, data_model, generator, changelog, api_reference, risk_assessment, artifact_traceability, cli_reference, use_cases, security_analysis, detect, requirements_analysis, conops, plugin_guide

#### 4. `_infer_behaviors` (infer.py:350)

**Checks:** Infer behaviors from route/CLI/handler patterns
**Result:** Pipeline: 52 behaviors, LLM: 36 behaviors
**Assessment:** ✅ Correct

### Entity Provenance

| Entity | Type | Created By | Naming Heuristic | Pipeline Name | LLM Alternative |
|--------|------|-----------|-----------------|--------------|----------------|
| gRPC Services | capability | `_infer_from_triggers` | `—` | gRPC Services | — |
| Scripts | capability | `_infer_from_domain_modules` | `stem.lstrip('_').replace('_', ' ').title()` | Scripts | Dev Simulation & Benchmarking |
| Src | capability | `_infer_from_domain_modules` | `stem.lstrip('_').replace('_', ' ').title()` | Src | Architecture Model Parsing & Serialization |
| CLI Runner | capability | `_infer_from_cli` | `'CLI ' + group_name.title()` | CLI Runner | Dev Simulation & Benchmarking |
| CLI Main | capability | `_infer_from_cli` | `'CLI ' + group_name.title()` | CLI Main | CLI Interface |

## Stage: allocate

### Summary

| Metric | Value |
|--------|------:|
| pipeline_components | 16 |
| llm_components | 43 |
| all_infra | False |

### Decision Chain

#### 1. `layer_assignment` (allocate.py:120)

**Checks:** Assign layers based on file path keywords
**Result:** 16 components, 15 with keyword-suggested layers
**Assessment:** ✅ Correct

### Entity Provenance

| Entity | Type | Created By | Naming Heuristic | Pipeline Name | LLM Alternative |
|--------|------|-----------|-----------------|--------------|----------------|
| Scripts (core) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Scripts (core) | Scripts |
| Scripts (dev_simulation) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Scripts (dev_simulation) | DevSimulation |
| Src (core) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (core) | Monitoring |
| Src (pipeline) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (pipeline) | PipelineStages |
| Src (core) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (core) | CoreUtilities |
| Src (quality) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (quality) | Quality |
| Src (config) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (config) | Config |
| Src (manifest) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (manifest) | ManifestGenerator |
| Src (utils) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (utils) | Utils |
| Src (cli) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (cli) | CLIMain |
| Src (authoring) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (authoring) | Authoring |
| Src (persistence) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (persistence) | Persistence |
| Src (orchestration) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (orchestration) | Orchestration |
| Src (extract) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (extract) | Extract |
| Src (profiles) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (profiles) | Profiles |
| Src (export) | component | `_seed_from_capabilities` | `cap.name.replace(' Management', '')` | Src (export) | Export |

## Stage: relate

### Summary

| Metric | Value |
|--------|------:|
| total_relationships | 85 |

### Entity Provenance

| Entity | Type | Created By | Naming Heuristic | Pipeline Name | LLM Alternative |
|--------|------|-----------|-----------------|--------------|----------------|
| COMP-2-1 realizes CAP-2 | relationship | `realizes_derivation` | `—` | COMP-2-1 realizes CAP-2 | — |
| COMP-2-2 realizes CAP-2 | relationship | `realizes_derivation` | `—` | COMP-2-2 realizes CAP-2 | — |
| COMP-3-1 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-1 realizes CAP-3 | — |
| COMP-3-2 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-2 realizes CAP-3 | — |
| COMP-3-3 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-3 realizes CAP-3 | — |
| COMP-3-4 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-4 realizes CAP-3 | — |
| COMP-3-5 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-5 realizes CAP-3 | — |
| COMP-3-6 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-6 realizes CAP-3 | — |
| COMP-3-7 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-7 realizes CAP-3 | — |
| COMP-3-8 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-8 realizes CAP-3 | — |
| COMP-3-9 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-9 realizes CAP-3 | — |
| COMP-3-10 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-10 realizes CAP-3 | — |
| COMP-3-11 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-11 realizes CAP-3 | — |
| COMP-3-12 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-12 realizes CAP-3 | — |
| COMP-3-13 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-13 realizes CAP-3 | — |
| COMP-3-14 realizes CAP-3 | relationship | `realizes_derivation` | `—` | COMP-3-14 realizes CAP-3 | — |
| COMP-3-1 depends-on COMP-3-2 | relationship | `import_edge_analysis` | `—` | COMP-3-1 depends-on COMP-3-2 | — |
| COMP-3-9 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-3-9 depends-on COMP-3-3 | — |
| COMP-3-1 depends-on COMP-3-9 | relationship | `import_edge_analysis` | `—` | COMP-3-1 depends-on COMP-3-9 | — |
| COMP-3-12 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-3-12 depends-on COMP-3-3 | — |
| COMP-3-4 depends-on COMP-3-6 | relationship | `import_edge_analysis` | `—` | COMP-3-4 depends-on COMP-3-6 | — |
| COMP-3-12 depends-on COMP-3-4 | relationship | `import_edge_analysis` | `—` | COMP-3-12 depends-on COMP-3-4 | — |
| COMP-3-4 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-3-4 depends-on COMP-3-1 | — |
| COMP-2-1 depends-on COMP-3-6 | relationship | `import_edge_analysis` | `—` | COMP-2-1 depends-on COMP-3-6 | — |
| COMP-3-12 depends-on COMP-3-9 | relationship | `import_edge_analysis` | `—` | COMP-3-12 depends-on COMP-3-9 | — |
| COMP-3-2 depends-on COMP-3-11 | relationship | `import_edge_analysis` | `—` | COMP-3-2 depends-on COMP-3-11 | — |
| COMP-3-1 depends-on COMP-3-11 | relationship | `import_edge_analysis` | `—` | COMP-3-1 depends-on COMP-3-11 | — |
| COMP-3-5 depends-on COMP-3-13 | relationship | `import_edge_analysis` | `—` | COMP-3-5 depends-on COMP-3-13 | — |
| COMP-3-6 uses COMP-3-7 | relationship | `import_edge_analysis` | `—` | COMP-3-6 uses COMP-3-7 | — |
| COMP-3-4 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-3-4 depends-on COMP-3-3 | — |
| COMP-2-1 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-2-1 depends-on COMP-3-1 | — |
| COMP-3-6 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-3-6 depends-on COMP-3-1 | — |
| COMP-3-8 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-3-8 depends-on COMP-3-3 | — |
| COMP-2-1 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-2-1 depends-on COMP-3-3 | — |
| COMP-3-6 depends-on COMP-3-5 | relationship | `import_edge_analysis` | `—` | COMP-3-6 depends-on COMP-3-5 | — |
| COMP-2-1 depends-on COMP-3-4 | relationship | `import_edge_analysis` | `—` | COMP-2-1 depends-on COMP-3-4 | — |
| COMP-3-11 depends-on COMP-3-6 | relationship | `import_edge_analysis` | `—` | COMP-3-11 depends-on COMP-3-6 | — |
| COMP-3-6 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-3-6 depends-on COMP-3-3 | — |
| COMP-3-6 depends-on COMP-3-4 | relationship | `import_edge_analysis` | `—` | COMP-3-6 depends-on COMP-3-4 | — |
| COMP-2-1 depends-on COMP-3-9 | relationship | `import_edge_analysis` | `—` | COMP-2-1 depends-on COMP-3-9 | — |
| COMP-3-5 uses COMP-3-7 | relationship | `import_edge_analysis` | `—` | COMP-3-5 uses COMP-3-7 | — |
| COMP-3-11 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-3-11 depends-on COMP-3-1 | — |
| COMP-3-6 depends-on COMP-3-2 | relationship | `import_edge_analysis` | `—` | COMP-3-6 depends-on COMP-3-2 | — |
| COMP-3-10 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-3-10 depends-on COMP-3-1 | — |
| COMP-3-2 depends-on COMP-2-2 | relationship | `import_edge_analysis` | `—` | COMP-3-2 depends-on COMP-2-2 | — |
| COMP-3-11 depends-on COMP-3-5 | relationship | `import_edge_analysis` | `—` | COMP-3-11 depends-on COMP-3-5 | — |
| COMP-3-1 depends-on COMP-2-2 | relationship | `import_edge_analysis` | `—` | COMP-3-1 depends-on COMP-2-2 | — |
| COMP-3-12 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-3-12 depends-on COMP-3-1 | — |
| COMP-3-11 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-3-11 depends-on COMP-3-3 | — |
| COMP-3-11 depends-on COMP-3-4 | relationship | `import_edge_analysis` | `—` | COMP-3-11 depends-on COMP-3-4 | — |
| COMP-2-1 depends-on COMP-3-11 | relationship | `import_edge_analysis` | `—` | COMP-2-1 depends-on COMP-3-11 | — |
| COMP-3-1 depends-on COMP-3-8 | relationship | `import_edge_analysis` | `—` | COMP-3-1 depends-on COMP-3-8 | — |
| COMP-3-12 depends-on COMP-3-13 | relationship | `import_edge_analysis` | `—` | COMP-3-12 depends-on COMP-3-13 | — |
| COMP-3-2 depends-on COMP-3-6 | relationship | `import_edge_analysis` | `—` | COMP-3-2 depends-on COMP-3-6 | — |
| COMP-3-11 depends-on COMP-3-2 | relationship | `import_edge_analysis` | `—` | COMP-3-11 depends-on COMP-3-2 | — |
| COMP-3-11 depends-on COMP-3-9 | relationship | `import_edge_analysis` | `—` | COMP-3-11 depends-on COMP-3-9 | — |
| COMP-3-1 depends-on COMP-3-6 | relationship | `import_edge_analysis` | `—` | COMP-3-1 depends-on COMP-3-6 | — |
| COMP-3-2 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-3-2 depends-on COMP-3-1 | — |
| COMP-3-3 depends-on COMP-3-6 | relationship | `import_edge_analysis` | `—` | COMP-3-3 depends-on COMP-3-6 | — |
| COMP-3-3 uses COMP-3-7 | relationship | `import_edge_analysis` | `—` | COMP-3-3 uses COMP-3-7 | — |
| COMP-3-9 depends-on COMP-3-6 | relationship | `import_edge_analysis` | `—` | COMP-3-9 depends-on COMP-3-6 | — |
| COMP-3-3 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-3-3 depends-on COMP-3-1 | — |
| COMP-3-9 depends-on COMP-3-1 | relationship | `import_edge_analysis` | `—` | COMP-3-9 depends-on COMP-3-1 | — |
| COMP-3-12 depends-on COMP-3-6 | relationship | `import_edge_analysis` | `—` | COMP-3-12 depends-on COMP-3-6 | — |
| COMP-3-2 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-3-2 depends-on COMP-3-3 | — |
| COMP-3-1 depends-on COMP-3-4 | relationship | `import_edge_analysis` | `—` | COMP-3-1 depends-on COMP-3-4 | — |
| COMP-3-1 depends-on COMP-3-3 | relationship | `import_edge_analysis` | `—` | COMP-3-1 depends-on COMP-3-3 | — |
| COMP-3-3 depends-on COMP-3-4 | relationship | `import_edge_analysis` | `—` | COMP-3-3 depends-on COMP-3-4 | — |
| COMP-3-12 depends-on COMP-3-5 | relationship | `import_edge_analysis` | `—` | COMP-3-12 depends-on COMP-3-5 | — |
| LAYER-DATA contains COMP-2-1 | relationship | `layer_grouping` | `—` | LAYER-DATA contains COMP-2-1 | — |
| LAYER-DATA contains COMP-2-2 | relationship | `layer_grouping` | `—` | LAYER-DATA contains COMP-2-2 | — |
| LAYER-WEB contains COMP-3-1 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-1 | — |
| LAYER-WEB contains COMP-3-2 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-2 | — |
| LAYER-WEB contains COMP-3-3 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-3 | — |
| LAYER-WEB contains COMP-3-4 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-4 | — |
| LAYER-WEB contains COMP-3-5 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-5 | — |
| LAYER-WEB contains COMP-3-6 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-6 | — |
| LAYER-WEB contains COMP-3-7 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-7 | — |
| LAYER-WEB contains COMP-3-8 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-8 | — |
| LAYER-WEB contains COMP-3-9 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-9 | — |
| LAYER-WEB contains COMP-3-10 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-10 | — |
| LAYER-WEB contains COMP-3-11 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-11 | — |
| LAYER-WEB contains COMP-3-12 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-12 | — |
| LAYER-WEB contains COMP-3-13 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-13 | — |
| LAYER-WEB contains COMP-3-14 | relationship | `layer_grouping` | `—` | LAYER-WEB contains COMP-3-14 | — |

## Stage: specify

### Summary

| Metric | Value |
|--------|------:|
| pipeline_interfaces | 17 |
| llm_interfaces | 52 |

### Entity Provenance

| Entity | Type | Created By | Naming Heuristic | Pipeline Name | LLM Alternative |
|--------|------|-----------|-----------------|--------------|----------------|
| runner CLI | interface | `cli_pattern` | `—` | runner CLI | dev_simulation CLI |
| main CLI | interface | `cli_pattern` | `—` | main CLI | cli.main CLI |
| Src (cli) API | interface | `unknown` | `—` | Src (cli) API | cli.main CLI |
| Scripts (core) API | interface | `unknown` | `—` | Scripts (core) API | add_sub_behaviors CLI |
| Src (core) API | interface | `unknown` | `—` | Src (core) API | architecture_model __main__ entrypoint |
| Src (pipeline) API | interface | `unknown` | `—` | Src (pipeline) API | pipeline.coordinator API |
| Src (core) API | interface | `unknown` | `—` | Src (core) API | core.types DataModels |
| Src (quality) API | interface | `unknown` | `—` | Src (quality) API | quality.orchestrator API |
| Src (config) API | interface | `unknown` | `—` | Src (config) API | config.loader API |
| Src (manifest) API | interface | `unknown` | `—` | Src (manifest) API | manifest.scanner API |
| Src (utils) API | interface | `unknown` | `—` | Src (utils) API | utils.discovery API |
| GateResult API | interface | `unknown` | `—` | GateResult API | authoring.gate API |
| ProjectSnapshot API | interface | `unknown` | `—` | ProjectSnapshot API | persistence.store API |
| Src (orchestration) API | interface | `unknown` | `—` | Src (orchestration) API | orchestration.pipeline API |
| RouteInfo API | interface | `unknown` | `—` | RouteInfo API | extract.from_code API |
| Src (profiles) API | interface | `unknown` | `—` | Src (profiles) API | profiles.schema DataModels |
| ExportResult API | interface | `unknown` | `—` | ExportResult API | export.flatfiles API |

## Stage: contract

### Summary

| Metric | Value |
|--------|------:|
| matched | 175 |
| unmatched | 0 |
| total | 175 |

### Decision Chain

#### 1. `contract_matching` (contract.py:50)

**Checks:** Match test contracts to components by file path
**Result:** 175 matched, 0 unmatched out of 175
**Assessment:** ✅ Correct

## Stage: validate

### Summary

| Metric | Value |
|--------|------:|
| score | 85 |
| issues | 3 |

### Decision Chain

#### 1. `validate_model` (validate.py:30)

**Checks:** Structural validation of the architecture model
**Result:** Score: 85/100, 3 issues
**Assessment:** ✅ Correct

---

# Gap Analysis Report

**Repository:** /Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp
**Generated:** 2026-08-27 21:35:35 UTC

## Executive Summary

- **Stages analyzed:** 6
- **Total gaps:** 487
- **Naming chains:** 2
- **Propagation traces:** 0

## Per-Stage Comparison

| Stage | Added | Removed | Renamed | Quality Delta |
|-------|------:|--------:|--------:|--------------:|
| infer | 71 | 18 | 40 | +0.0 |
| allocate | 27 | 0 | 16 | +0.0 |
| relate | 41 | 0 | 0 | +0.0 |
| specify | 52 | 0 | 0 | +0.0 |
| contract | 222 | 0 | 0 | +0.0 |
| validate | 0 | 0 | 0 | +0.0 |

## Renamed Entities

### Stage: infer

| Deterministic Name | LLM Name | Similarity |
|-------------------|----------|:----------:|
| gRPC Services | CLI Interface | 0.46 |
| Scripts | TypeScript Scanning | 0.54 |
| CLI Runner | Capability Inference | 0.47 |
| CLI Main | Pipeline Caching | 0.50 |
| CLI: Test Guided Round Trip | LLM-Assisted Review and Correction | 0.43 |
| CLI: Test Enriched Round Trip | Model Enrichment from Source Code | 0.45 |
| CLI: Test Multi Repo | Coverage and Representativeness Reporting | 0.39 |
| CLI: Test Round Trip | Test Contract Matching | 0.48 |
| CLI: Test Decomposed Round Trip | Hierarchical Model Decomposition | 0.48 |
| CLI: Runner | Gap Analysis and Re-inference | 0.35 |
| CLI: Main | Confidence Computation | 0.45 |
| Run Benchmark Runner | Learning Store Persistence and Retrieval | 0.37 |
| Run Phase2 Llm Predictor | Route and Constraint Detection | 0.37 |
| Load Patterns Patterns | Pattern Classification of Components | 0.41 |
| Load Reviews Review Store | Authoring Model from Requirements Doc | 0.32 |
| Build Reinfer Prompt Gap Prompts | Behavior Reconstruction from Code | 0.40 |
| Create Reinfer Prompt | Code Improvement Planning | 0.39 |
| Create Llm Callback Llm Provider | Round-Trip Testing Against Oracle Models | 0.33 |
| Create Llm Callback | Cross-Repo Consistency Check | 0.38 |
| Build Naming Chains Gap Analysis | Code Scanning and Manifest Generation | 0.41 |
| Run Gap Analysis Gap Analysis | Component Spec and ICD Generation | 0.35 |
| Create Naming Chains | Pipeline Caching and Resumption | 0.43 |
| Build Review Prompt Stage Review | Development Gate Evaluation | 0.47 |
| Build Semantic Review Prompt Stage Review | PDF Report Generation | 0.39 |
| Create Review Prompt | Recursive Decomposition of Large Systems | 0.30 |
| Create Semantic Review Prompt | Observe-Infer-Allocate-Specify-Relate-Synthesize Pipeline | 0.33 |
| Load Block Model Parser | Compact Mode Pipeline Execution | 0.41 |
| Load Model Parser | System Detection and SoS Model Building | 0.36 |
| Load Corrections Corrections | Model Validation and Scoring | 0.46 |
| Load Config Loader | Config Discovery and Auto-Configuration | 0.35 |
| Build Block Chains Chains | Multi-Language Source Scanning | 0.40 |
| Build Cross Block Chains Chains | Quality Loop Iteration | 0.34 |
| Create Block Chains | Model Slicing by Block/Layer/Status | 0.33 |
| Create Components From Manifest Grouping | SE Document Generation | 0.39 |
| Create Components From Manifest | Export to Flat Files and Markdown | 0.31 |
| Load Or Generate Manifest Generator | Diagram and Visualization Generation | 0.37 |
| Load Project Store | Full Pipeline Execution | 0.34 |
| Create Behaviors From Manifest Auto Enrich | Behavior Flow Tracing and CRUD Summarization | 0.37 |
| Build Behavior Entry Map Trigger Detection | Model Diffing Between Versions | 0.33 |
| Run Pipeline Pipeline | Artifact Writing and Emit | 0.30 |

### Stage: allocate

| Deterministic Name | LLM Name | Similarity |
|-------------------|----------|:----------:|
| Scripts (core) | Scripts | 0.67 |
| Scripts (dev_simulation) | DevSimulation | 0.70 |
| Src (core) | TestCore | 0.56 |
| Src (pipeline) | TestPipeline | 0.69 |
| Src (core) | CoreTypes | 0.42 |
| Src (quality) | Quality | 0.70 |
| Src (config) | Config | 0.67 |
| Src (manifest) | TestManifest | 0.69 |
| Src (utils) | Utils | 0.62 |
| Src (cli) | TestCLI | 0.50 |
| Src (authoring) | Authoring | 0.75 |
| Src (persistence) | Persistence | 0.79 |
| Src (orchestration) | Orchestration | 0.81 |
| Src (extract) | Extract | 0.70 |
| Src (profiles) | Profiles | 0.73 |
| Src (export) | Export | 0.67 |

## Naming Chains

| Source | allocate (det/llm) | infer (det/llm) | specify (det/llm) | Generic |
|--------|------------|------------|------------|:-------:|
| scripts/add_sub_behaviors.py | Scripts (dev_simulation) / DevSimulation | Scripts / — | runner CLI / dev_simulation.drift_tracker API | no |
| src/architecture_model/__init__.py | Src (export) / TestE2E | Src / — | ExportResult API / export.reference API | no |

## Recommendations

1. 56 renamed entit(ies) — LLM naming diverges from deterministic; review naming heuristics
