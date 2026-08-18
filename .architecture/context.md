# Architecture Context: architecture-model-standard

**Score:** 80/100 | **Valid:** True

## Capabilities
- **Web Routes** (CAP-1): HTTP routing (18 endpoints)
- **gRPC Services** (CAP-2): gRPC service definitions and handlers
- **Scripts** (CAP-3): Package group with 16 modules
- **Src** (CAP-4): Package group with 105 modules
- **CLI Main** (CAP-5): CLI commands in src/architecture_model/cli/main.py
- **CLI Runner** (CAP-6): CLI commands in scripts/dev_simulation/runner.py

## Actors
- **API Consumer** (system)

## Components
- **Scripts (core)** (COMP-3-1) [data]: scripts/add_sub_behaviors.py, scripts/bench_enrichment.py, scripts/enrich_sub_behaviors.py, scripts/generate_models_pdf.py, scripts/se_enrich.py (+1 more)
- **Scripts (dev_simulation)** (COMP-3-2) [data]: scripts/dev_simulation/checkout.py, scripts/dev_simulation/cli.py, scripts/dev_simulation/cohesion.py, scripts/dev_simulation/drift_tracker.py, scripts/dev_simulation/extractor.py (+5 more)
- **Src (core)** (COMP-4-1) [web]: src/architecture_model/__init__.py, src/architecture_model/__main__.py, src/architecture_model/monitoring.py, src/architecture_model/monitoring_checks.py, src/architecture_model/patterns.py
- **Src (pipeline)** (COMP-4-2) [web]: src/architecture_model/pipeline/__init__.py, src/architecture_model/pipeline/allocate.py, src/architecture_model/pipeline/allocate_types.py, src/architecture_model/pipeline/artifacts.py, src/architecture_model/pipeline/cache.py (+28 more)
- **Src (core)** (COMP-4-3) [web]: src/architecture_model/core/cluster.py, src/architecture_model/core/completeness.py, src/architecture_model/core/compression.py, src/architecture_model/core/confidence.py, src/architecture_model/core/corrections.py (+13 more)
- **Src (config)** (COMP-4-4) [web]: src/architecture_model/config/__init__.py, src/architecture_model/config/loader.py, src/architecture_model/config/schema.py
- **Src (manifest)** (COMP-4-5) [web]: src/architecture_model/manifest/__init__.py, src/architecture_model/manifest/behavior.py, src/architecture_model/manifest/blocks.py, src/architecture_model/manifest/body_hints.py, src/architecture_model/manifest/call_graph.py (+15 more)
- **Src (utils)** (COMP-4-6) [web]: src/architecture_model/utils/discovery.py
- **Src (cli)** (COMP-4-7) [web]: src/architecture_model/cli/main.py, src/architecture_model/cli/visualize.py
- **Src (authoring)** (COMP-4-8) [web]: src/architecture_model/authoring/gate.py, src/architecture_model/authoring/parser.py
- **Src (persistence)** (COMP-4-9) [web]: src/architecture_model/persistence/__init__.py, src/architecture_model/persistence/store.py
- **Src (orchestration)** (COMP-4-10) [web]: src/architecture_model/orchestration/auto_enrich.py, src/architecture_model/orchestration/behavior_decompose.py, src/architecture_model/orchestration/behavior_flows.py, src/architecture_model/orchestration/capability_inference.py, src/architecture_model/orchestration/compaction.py (+8 more)
- **Src (extract)** (COMP-4-11) [web]: src/architecture_model/extract/constraint_detector.py, src/architecture_model/extract/from_artifacts.py, src/architecture_model/extract/from_code.py, src/architecture_model/extract/route_detector.py, src/architecture_model/extract/table_parser.py
- **Src (profiles)** (COMP-4-12) [web]: src/architecture_model/profiles/schema.py
- **Src (export)** (COMP-4-13) [web]: src/architecture_model/export/flatfiles.py, src/architecture_model/export/reference.py

File coverage: 100% | Boundary coherence: 51%

## Relationships
- contains: 15
- depends-on: 41
- realizes: 15
- uses: 3

## Metrics
- Modules: 342
- Routes: 18
- Test files: 175
- Docs: 30
