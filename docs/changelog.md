# Changelog

All notable changes to the Architecture Model Standard package.

---

## [0.2.0] - 2026-07-05

### MPC Training Loop

The major addition is the **Model-Predictive Control (MPC) training loop** — a self-improving extraction system that uses oracle feedback to train a local surrogate model.

**Core Training Pipeline:**
- Surrogate model (qwen2.5:7b default) generates architecture extractions
- Oracle (remote LLM) scores extractions against ground truth
- DPO preference pairs generated from Best-of-N sampling
- LoRA fine-tuning adapts surrogate toward oracle quality
- Pareto convergence tracking (multi-objective loss vector)
- Budget-capped oracle calls with automatic decrement

**Extraction Improvements:**
- Multi-pass extraction with AST-guided context
- Precision guidance + few-shot examples in extraction prompts
- SelfCritiqueRefiner for oracle gap-targeted re-extraction
- PromptEvolver with self-reflective meta-learning
- Deterministic + semantic relationship generation
- Behavior-to-capability `realizes` relationships and orphan behavior `allocated-to`

**Evaluation & Scoring:**
- CoverageScorer replaces InterfaceEnforcer (manifest-derived scoring)
- Semantic matching in loss signal (not ID-based)
- Pareto objectives enriched with CoverageScorer signals
- Composite confidence signal replaces naive heuristic
- Dropped `reconstruction_fidelity` from LossVector

**Context Building:**
- OracleContextBuilder with manifest summary + code slices (20% budget cap)
- Smart file ranking for large repos (ContextBuilder improvement)
- Block-level dependency matrix injection
- Test analysis integrated into extraction context

**Model Configuration:**
- ModelConfig registry with 3 tested models
- Multi-adapter LoRA training targets (`resolve_training_targets()`, `train_all()`)
- Configurable model swap via benchmark script

**Validation & Testing:**
- BackwardValidator for docs/tests/structural validation
- Multi-repo validation harness with backward testing
- TestRunner and TestAnalyzer for repo test suite integration
- End-to-end integration test for surrogate training plumbing
- Best-of-N DPO preference pair unit tests (495 lines)

**Core Enhancements:**
- `ArchitectureModel.to_dict()` and `to_yaml()` serialization
- Status normalization maps non-standard values to valid enum
- Facade-pattern imports resolved through `__init__.py` re-exports

**Infrastructure:**
- Training SQLite database (`data/training.db`, 856K)
- Implementation plans in `.opencode/plans/`
- Multi-repo test results tracking (`results/`)

**Bug Fixes:**
- Strip markdown fences from LLM responses before YAML parse
- Generalize context builder + enum normalization
- Remove convergence_history dual-write
- Fix ID-based entity matching (prevent sequential ID collision)
- Serialize models with `to_yaml()` instead of `str()`

### Pipeline Test Results (2026-07-05)

Re-tested against the package itself (now with training/ subpackage):

| Stage | Result |
|-------|--------|
| Ingest | 120 files (with EXCLUDE_DIRS fix) |
| Seed | 101 modules with code intelligence (AST analysis) |
| Synthesize | 9 subsystems, 8 interfaces, 7 states, 9 requirements |
| Manifest | 8 F-blocks (7 active, F7 dormant), 108 Python files |
| Artifacts | 27 MBSE documents generated |
| PDF | 27 rendered (PlantUML SVG + Mermaid JS via headless Chrome) |
| Validation | 55 PASS, 0 FAIL, 20 SKIP |

### Known Issues Resolved
- Ollama `/v1/chat/completions` 404: confirmed working (was transient)
- Artifact generation for external projects no longer hallucinates host-project content (manifest loaded from correct output dir)

### Known Issues
- Seed classification hangs when called within pipeline context (DB session conflict)
- `logical-architecture` artifact scores 40/100 (missing: Component Diagram, Technology Stack, API Layer)

---

## [0.1.0] - 2026-07-02

### Initial Release (Extraction from logs-db)

**Package Extraction (Phase 3):**
- Extracted from `logs-db/scripts/_architecture_model/` into standalone package
- pyproject.toml with hatchling build system
- CLI entry point: `architecture-model` (9 subcommands)
- All internal imports rewritten to absolute `architecture_model.*` paths
- Installed as editable dependency in logs-db's venv
- Two logs-db consumers updated: `_pipeline_manifest.py` (shim), `_pipeline_artifacts.py` (guarded import)

**Core Features:**
- Architecture Model YAML schema (7 entity types, 8 relationship types)
- Model parser, validator (100/100 score), slicer, differ
- Reality Manifest generator (AST scanning, metrics, F-blocks, interfaces)
- Architecture extractor (from Tier 1 artifacts back to model)
- LLM integration: context formatting, pipeline bridge (`enrich_manifest_slice`), query engine
- JSON Schema for model validation (`spec/schema.json`)

**Auto-Discovery & Init:**
- `architecture-model init <path>` — auto-generates `.architecture-model.yaml`
- Source root detection: src-layout, flat-layout, lib-layout
- F-block discovery from subpackage directories
- Description extraction from `__init__.py` docstrings
- Layer derivation from F-block directories
- Metric discovery from common directory patterns
- `write_config()` with auto-generation header and round-trip serialization

**Pipeline Integration:**
- `get_config(root)` — loads config or auto-discovers (recommended entry point)
- Synthesize bridge: `_write_architecture_config()` auto-refines config after LLM synthesis
- Merge strategy: replaces auto-discovered blocks with LLM-synthesized; preserves manual
- `cmd_manifest` resolves project root from `source_config.opencode_dir` in DB
- `display.py` handles projects without standard metrics dynamically

**Test Suite:**
- 34 unit tests (standalone, no external dependencies)
- 140 total tests with integration fixtures (skip gracefully when project data unavailable)
- `pytest.mark.skipif` guards for integration tests

**Documentation:**
- `docs/specification.md` — full schema specification
- `docs/llm-protocol.md` — LLM integration protocol (6 verbs)
- `docs/project-descriptor.md` — config file format
- `docs/architecture-decisions.md` — 8 ADRs
- `docs/integration-guide.md` — pipeline integration reference
- `CONTEXT.md` — project purpose and role in Knowledge OS

---

## Pipeline Test Results (2026-07-02)

Tested against the package itself as a target project:

| Stage | Result |
|-------|--------|
| Ingest | 157 files ingested |
| Seed | 31 modules with code intelligence (AST analysis) |
| Synthesize | 7 subsystems, 7 interfaces, 7 states, 10 requirements |
| Manifest | 7 F-blocks (6 active, 1 dormant), 37 Python files, 20 modules |
| Artifacts | 27 MBSE documents generated |
| PDF | 5 Tier 1 artifacts rendered with graphics (PlantUML SVG + Mermaid JS) |

### Known Issues
- Ollama `/v1/chat/completions` returns 404 intermittently during seed stage (non-blocking — AST analysis still succeeds)
- Artifact generation times out at 10min for all 27 docs (individual generation works fine)
- F7 (Spec) block is `dormant` — contains only `schema.json`, no `.py` files
