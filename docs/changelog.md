# Changelog

All notable changes to the Architecture Model Standard package.

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
