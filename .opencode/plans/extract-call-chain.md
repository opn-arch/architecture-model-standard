# Pipeline Internal Call Chain Reference

Traced via subagent analysis of all 9 pipeline stages.

## OBSERVE
`run()` → `_is_excluded()` for file filtering → `_scan_module()` per file (AST parse → `_extract_function()`, `_extract_class()`, `_extract_constants()`, `_extract_imports()`) → `_resolve_import_edges()` (bulk, builds name_to_path mapping) → `_detect_routes()` → `_detect_constraints()` → `_find_test_files()` → `_find_docs()` → code quality via `analyze_source()`.

**Naming**: module path = relative file path.
**Quality scoring**: `analyze_source()` from `quality/code_review.py`, defaults to 0 on failure.

## INFER
`run()` → Strategy 1: `_infer_from_routes()` (URL prefix → Title Case + " Management") → Strategy 1b: `_infer_from_triggers()` (websocket/grpc/scheduler) → Strategy 2: `_infer_from_domain_modules()` (**Naming**: `stem.lstrip("_").replace("_", " ").title()` — file stem becomes capability name) → Strategy 3: `_infer_from_cli()` ("CLI " + stem) → Strategy 4: `_infer_infrastructure_capabilities()` → `_infer_default_actors()` → `_infer_behaviors()` (route handlers, CLI commands, handler classes, workflows) → **NEW**: `_infer_library_behaviors()` (5 patterns: API entry points, context managers, lifecycle pairs, processing chains, factory/builder).

**Key**: `_is_non_source_module()` filters tests/conftest/setup/__init__.
**Thresholds**: min_funcs=3, min_classes=2 (default); min_funcs=1, min_classes=1 (scoped).
**Large repo**: >50 source modules → package-level grouping via `_infer_capabilities_by_package()`.

## ALLOCATE
`run()` → `_detect_project_type()` (**NEW**: scans imports for web/CLI frameworks, defaults to "library") → `_seed_from_capabilities()` (**Naming**: `cap.name.replace(" Management", "")` → component name) → `_assign_by_import_affinity()` (ImportEdge scoring) → infra catch-all → `_split_oversized()` (>12 files) → `_merge_undersized()` → `_infer_layer()` (**ENHANCED**: now per-file voting with `_LAYER_KEYWORDS` dict, default based on project_type).

## RELATE
`run()` → realizes (from capability_id + word overlap matching) → depends-on/uses (import substring matching via `_pick_relationship_type()` — "uses" if target is utility) → contains (layer→component grouping) → exposes (route→component) → constrained-by.

## SPECIFY
`run()` → REST interfaces (route grouping) → CLI interfaces (click/typer/argparse detection) → Library API interfaces (cross-component symbol consumption via ImportEdge analysis) → fallback interfaces.
**Naming**: now uses `_name_library_interface()` (**NEW**: dominant class → component name → module stem → fallback).

## CONTRACT
`run()` → `_match_target()` (5 strategies: exact stem, component name, substring×2, reverse substring) → `_match_by_directory()` fallback.
**Note**: `_find_test_files()` in observe already strips `test_` prefix to produce `target`. Also added `_find_tests_for_scope()` (**NEW**) for scoped sub-pipelines.

## VALIDATE
5 checks: capability realization, orphan detection, file coverage (<95%→warning), boundary coherence (<50%→info), confidence-driven uncertainties. Score: `100 - errors*20 - warnings*5`.

## DECOMPOSE
`run()` → per-component: `len(files) >= 5` → autonomous system, else inline. `len(files) >= 8` → `_decompose_component()` (cluster by directory).

## SYNTHESIZE
`run()` → per full system: `_decide_stages()` (≥8 files→full pipeline, <8→abbreviated) → scoped pipeline run → `_build_system_model_yaml()` → `_build_sos_model()`.

## LLM Refinement System

**Flow**: Heuristic stage runs → `refine_with_llm()` called → `build_reinfer_prompt()` (from `gap_prompts.py`) → LLM re-infers from scratch → `normalize_llm_output()` maps LLM schema to pipeline format → `extract_stage_data()` converts heuristic output → `diff_stage_outputs()` diffs the two → apply renames/additions/layer corrections → return refined `StageResult`.

**Per-stage refinement**:
- **infer**: `apply_renames()` on capabilities (threshold 0.5), `apply_additions_infer()` adds LLM-only capabilities+behaviors with `origin="llm_inferred"`
- **allocate**: `apply_renames()` on components, `apply_layer_corrections()` always applies LLM layer (via name similarity matching), NO add/remove of components
- **relate**: `apply_additions_relate()` adds LLM-only relationships (deduplicates by from_id+to_id pair), NO removal of import-based relationships
- **specify**: `apply_renames()` on interfaces

**Coordinator integration**: In `coordinator.py`, `_maybe_refine()` is called after `stage.run()` but before `_evaluate_gates()` for stages in `_LLM_REFINABLE_STAGES = {"infer", "allocate", "relate", "specify"}`. For refined stages, `_evaluate_gates()` skips the separate LLM review (avoids redundant LLM call).

**Schema normalization** (critical): LLM returns different field names than pipeline expects:
- relate: LLM gives `from`/`to`/`type` → normalized to `from_id`/`to_id`/`rel_type`
- specify: LLM gives `type` → normalized to `interface_type`
- infer: LLM gives `source_file` (singular) → kept as-is (extract_stage_data uses `source_files` plural)
