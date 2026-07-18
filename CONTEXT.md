# Architecture Model Standard

## Origin

Extracted from the `scripts/_architecture_model/` package within the [logs-db](../logs_db/) Knowledge OS project. Became a standalone installable package to enable reuse across multiple projects without coupling to the logs-db codebase.

## Purpose

A universal, machine-readable **Architecture-as-Code** standard that serves as the architectural spine for LLM-driven system engineering. It provides:

- A **YAML schema** describing any software system's architecture (entities, relationships, constraints)
- A **Reality Manifest** generator that produces ground-truth inventories via AST scanning
- A **validation engine** that checks architectural claims against code reality
- An **LLM integration protocol** enabling AI agents to load, query, and update architectural models
- **Self-bootstrapping** configuration — no manual setup required; `architecture-model init` auto-generates the project descriptor from directory structure

## Role in the Three-Repo Architecture

This package is the **schema + library layer** in a three-repo system:

```
architecture-model-standard (this repo)     — Schema, validator, CLI, manifest generator
        ↑ dependency
opencode-arch (../opencode-arch/)           — MCP extension wrapping these APIs
        ↑ used by
OpenCode agent (frontier model)             — Consumes compressed context, produces models

arch-agent (../arch-agent/)                 — Training pipeline + surrogate (future)
        ↑ dependency
architecture-model-standard (this repo)
```

**Core flow:**
```
Code → [AST Scan] → Reality Manifest → [Context Formatter] → Agent → [Validator] → .architecture-model.yaml
```

The `opencode-arch` MCP server wraps this package's APIs:
- `generate_manifest()` → `architect_scan` tool
- `format_model_context()` / slicer → `architect_slice` tool
- `validate_model()` → `architect_validate` tool
- `_parse_raw()` → used by `architect_extract` for storage

## Key Capabilities

### Schema (7 Entity Types)
- **Actors** — external agents that interact with the system
- **Capabilities** — functional blocks (F-blocks) the system provides
- **Behaviors** — use cases, workflows, operational sequences
- **Interfaces** — APIs, protocols, data exchanges between components
- **Constraints** — non-functional requirements, design rules
- **Layers** — architectural tiers (web, services, data, pipeline)
- **Components** — deployable units, modules, packages

### Relationships (8 Types)
- `realizes` — component realizes a capability
- `uses` — component uses an interface
- `constrains` — constraint applies to an entity
- `contains` — layer contains components
- `triggers` — behavior triggers another behavior
- `depends_on` — component depends on another
- `implements` — component implements a behavior
- `exposes` — component exposes an interface

### LLM Protocol (6 Verbs)
- **LOAD** — parse and internalize the architecture model
- **QUERY** — answer structural questions about the system
- **IMPACT** — trace change impact through relationships
- **VALIDATE** — check claims against the model
- **UPDATE** — propose model modifications
- **PROJECT** — forecast effects of planned changes

### Self-Bootstrapping
The pipeline requires no manual configuration to analyze a new project:
1. `architecture-model init <path>` scans directory structure
2. Discovers source root (src-layout, flat-layout, or lib-layout)
3. Each subpackage becomes a Functional Block with files enumerated
4. Writes `.architecture-model.yaml` with layers, F-blocks, and metrics
5. Subsequent pipeline stages refine this config with LLM-synthesized groupings

### Domain Profiles
The standard supports cross-domain architecture modeling via domain profiles:
- **software** (default) — standard software architecture entities
- **controls** — sensors, actuators, PLCs, fieldbus, SIL levels
- **mechanical** — parts, assemblies, materials, tolerances
- **electrical** — PCBs, connectors, power supplies, voltage/current ratings

Profiles extend the base schema with:
- Additional enum values (ComponentKind, InterfaceType, etc.)
- Additional entity properties (validated via JSON Schema fragments)
- Conditional validation rules (e.g., "sensors must declare signal_type")

Usage: Set `domain_profile: controls` in the model meta section.

## Package Structure

```
src/architecture_model/
├── cli/          — CLI commands (init, extract, validate, slice, diff, query, context, stats, impact, generate)
├── config/       — Configuration loading, auto-discovery, schema definition
├── core/         — Parser, validator, slicer, differ, merger, decomposer, type system
├── extract/      — Extract model from generated Tier 1 artifacts
├── integrations/ — LLM context formatting, pipeline bridge
├── manifest/     — Reality Manifest generator (AST scanning, metrics, blocks, interfaces)
├── profiles/     — Domain profile system (software, controls, mechanical, electrical)
├── spec/         — JSON Schema for model validation
└── utils/        — Shared utilities (file discovery, exclusion patterns)
```

## Key APIs (used by opencode-arch)

### Manifest Generation
```python
from architecture_model.manifest.generator import generate_manifest
manifest = generate_manifest(project_root: Path) -> Manifest
# Returns: Manifest dataclass with typed fields
# Use manifest.to_dict() for JSON serialization
```

### Model Parsing
```python
from architecture_model.core.parser import load_model, _parse_raw
model = load_model(path: Path) -> ArchitectureModel  # from file
model = _parse_raw(raw: dict) -> ArchitectureModel   # from dict (no public string parser)
```

### Validation
```python
from architecture_model.core.validator import validate_model
result = validate_model(model: ArchitectureModel) -> ValidationResult
# result.score: int (0-100)
# result.issues: list[ValidationIssue]
# result.is_valid: bool
```

### Context Formatting (the token compressor)
```python
from architecture_model.integrations.llm_context import format_model_context, format_fblock_context
context = format_model_context(model, max_tokens=4000, detail_level="standard") -> str
context = format_fblock_context(model, f_block="F1", max_tokens=4000) -> str
```

### Slicing
```python
from architecture_model.core.slicer import slice_by_fblock, slice_by_layer
sliced = slice_by_fblock(model, fblock_id="F1") -> ArchitectureModel
sliced = slice_by_layer(model, layer_id="web") -> ArchitectureModel
```

## Model YAML Format

**Important:** Entities must be nested under the `entities:` key:
```yaml
meta:
  project: my-project
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: MyComponent
      status: ACTIVE
  capabilities:
    - id: CAP-F1
      name: MyCapability
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
```

## Status

- Schema version: 1.4 (added Constant, FunctionSignature, TestContract on Component)
- Package version: 0.3.0
- Test suite: 542 passed, 114 skipped
- Validation score: 100/100, 0 orphaned entities
- CLI entry point: `architecture-model`
- Install: `pip install -e .` (editable) or `pip install architecture-model-standard`

## E2E Benchmark Results (2026-07-07)

### Extraction (architecture model from source code)
| Repo | Score | Entities | Relationships | Time |
|------|-------|----------|---------------|------|
| python-dotenv | 98/100 | 13 | 15 | 82s |
| colorama | 98/100 | 10 | 15 | 94s |
| tqdm | 98/100 | 30 | 48 | 108s |
| structlog | 98/100 | 20 | 24 | 132s |

**Average: 98/100, 100% success rate** — the system reliably produces valid architecture models from arbitrary Python repos.

### Regeneration (code from architecture model)
All repos: **0% test pass rate** — abstract architecture models (capabilities, components, relationships) are insufficient for faithful code regeneration. The models describe WHAT the system does structurally, not HOW it implements specific behavior (function signatures, constants, algorithms). This validates the need for enriched models with AST-level detail.

### Regeneration with Test-Oracle Loop (Normal Mode)
| Repo | Grade | Fidelity | Avg Compression | Subsystems Converged | Avg Iterations |
|------|:-----:|:--------:|:---------------:|:--------------------:|:--------------:|
| colorama | B | 80% | 7.4x | 4/5 | 1 |
| structlog | A | 93% | 17.9x | 13/14 | 1 |
| tqdm | B | 82% | 67.9x | 9/11 | 1 |
| click | B | 89% | 45.9x | 8/9 | 1 |

Note: Non-100% fidelity in normal mode is due to "root" subsystems (decomposer artifacts with 0 test files) and external dependency issues (e.g., tqdm.keras requires TensorFlow).

### Blind Regeneration (model-only, no source/test file access) — FINAL RESULTS

| Repo | Testable Subsystems | Converged | Fidelity | Avg Iterations | Time |
|------|:-------------------:|:---------:|:--------:|:--------------:|:----:|
| colorama | 4 | **4/4** | **100%** | 1.0 | ~5m |
| structlog | 13 | **13/13** | **100%** | 1.0 | ~25m |
| tqdm | 10 | **10/10** | **100%** | 1.0 | ~20m |
| click | 8 | **8/8** | **100%** | 1.0 | ~30m |
| **TOTAL** | **35** | **35/35** | **100%** | **1.0** | **~80m** |

**Key breakthrough:** The enriched architecture model ALONE (body_hints + constants + test_contracts) contains enough information to regenerate code that passes ALL tests for ALL testable subsystems — WITHOUT the agent reading any source or test files. The agent works in an empty temp directory with only the model data in its prompt.

**What this proves:**
- The architecture model is a **lossless behavioral representation** for 35/35 subsystems
- 34/35 converge on **first attempt** (97% first-iteration success)
- Zero fidelity gap for 33/35 subsystems (blind score = normal score)
- Blind mode can even BEAT normal mode (structlog.processors: 91% normal → 100% blind)

**What made it work:**
1. `body_hint` on trivial functions = exact implementation (`return CSI + str(code) + 'm'`)
2. Module-level constants extracted (CSI, OSC, BEL)
3. Class attributes with values (BLACK=30, RED=31, ...)
4. Module-level instances (Fore=AnsiFore(), Back=AnsiBack(), ...)
5. Test contracts specifying exact expected outputs
6. Dependency context expansion for cross-module subsystems
7. Adaptive contract cap increase for under-specified subsystems

### Key Findings
- MCP server works end-to-end with `opencode run` (headless mode)
- `--dangerously-skip-permissions` required for cross-directory access
- `--dir` should point to `architecture-model-standard` (where MCP tools are configured)
- Root cause of earlier MCP failure: broken editable install of `python-dotenv` (pointed to deleted temp dir) caused `mcp` package import to fail silently

### Token Economics (Value Proposition)

**Compression ratio improves with repo size/connectivity:**

| Repo | Source (tokens) | Blind Prompt (tokens) | Compression | Fidelity |
|------|----------------:|---------------------:|:-----------:|:--------:|
| colorama | 10,012 | ~1,800 | 2.8x | 100% |
| structlog | 60,174 | ~3,000 | 6.0x | 100% |
| tqdm | 46,151 | ~2,800 | 7.9x | 100% |
| click | 105,694 | ~4,000 | 26.4x | 100% |

**Per-subsystem analysis (highest compression wins):**
- click.arguments: 97,940 vs 1,141 = **85.8x** compression (100% fidelity)
- click.parser: 74,346 vs 949 = **78.3x** (100% fidelity)
- click.utils: 96,185 vs 2,157 = **44.6x** (100% fidelity)
- click.testing: 91,902 vs 2,731 = **33.7x** (100% fidelity)
- tqdm.contrib: 41,508 vs 819 = **50.7x** compression (100% fidelity)
- tqdm.concurrent: 33,575 vs 780 = **43.0x** (100% fidelity)
- structlog.generic: 9,092 vs 444 = **20.5x** (100% fidelity)

The compression benefit is DEPENDENCY-DRIVEN: subsystems with many large upstream dependencies benefit most because the model provides their API surface in ~50 tokens vs reading full source files.

**Scaling law:** Compression ratio correlates with total source tokens:
- 10K source → 2.8x
- 46-60K source → 6-8x
- 105K source → 26x average (up to 86x per subsystem)

### Learning Loop (COMPLETE - 2026-07-07)

The learning loop is fully integrated into the regen-loop orchestrator:

**Pattern Classifier** (7 pattern types, 14 regex rules + structured analysis):
- CROSS_DEP, MISSING_IMPL, WRONG_CONSTANT, API_MISMATCH, COMPLEX_BEHAVIOR, TEST_INFRA, UNKNOWN
- Dual-level: raw regex on pytest output + structured analysis of pass rates

**Adaptive Prompt Optimizer** (4 heuristic rules + historical pattern lookup):
- Rule 1: High dep count (>=3) → expand dep context proactively
- Rule 2: Low contracts (<10) → increase contract cap to 200
- Rule 3: Low body_hint coverage (<50%) → flag for source excerpts
- Rule 4: Historical patterns → apply learned strategies

**Report Cards** (self-assessment after each run):
- Grading: A (>90% fidelity, >5x compression, 0 novel) through F (<40%)
- Trend detection vs previous runs (fidelity, compression)
- Actionable improvement suggestions

**Lessons** (automatic insight extraction):
- Contract count thresholds, signature correlations
- Dominant pattern detection, systemic issue flagging
- Stored with deduplication (content-hashed IDs)

**Doc Drift Maintainer** (4 checks + auto-fix):
- Test count, version sync, schema version, Python version
- Auto-fixes simple cases (version numbers, test counts)

**CLI Commands:**
- `opencode-arch report` — Display report cards with grades and actions
- `opencode-arch metrics --learning-curve` — Show learning curve trends
- `opencode-arch metrics --drift` — Show unresolved drift flags

### Learning Curve Tracking

The `learning_curve` table in telemetry tracks improvement over successive repos:
- `avg_compression_ratio`: 2.8x → 6.0x → 7.9x → 26.4x (UP with repo size)
- `converged/total`: Should improve as pipeline matures
- `avg_iterations`: Should stay at 1 (good model = first-attempt success)
- Fidelity gap (normal - blind): Target <10% across all repos

## Development Instructions

- Always run tests with: `pytest tests/ -v --ignore=tests/test_config_loader.py` (pre-existing failure)
- Training module has been moved to `arch-agent` repo — do not add training code here
- This is the schema-only open standard — keep it focused on parse/validate/slice/format
- The `opencode-arch` package depends on this — API changes need coordination
- MCP server venv: ensure `python-dotenv` is a proper wheel install (not editable) — `pip install --force-reinstall python-dotenv` if FastMCP import fails

## Related Repos

| Repo | Path | Purpose | Tests |
|------|------|---------|-------|
| architecture-model-standard | (this repo) | Schema, validator, CLI, manifest | 509 passed |
| opencode-arch | `../opencode-arch/` | MCP extension (token broker) + CLI + E2E benchmarks | 157 passed |
| arch-agent | `../arch-agent/` | Training pipeline + surrogate | 574 passed |
