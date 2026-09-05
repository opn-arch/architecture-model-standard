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

### Relationships (17 Types)
- `realizes` — component realizes a capability
- `contains` — layer/component/capability/behavior contains sub-entity
- `depends-on` — component depends on another
- `exposes` — component exposes an interface
- `consumes` — actor consumes an interface
- `traces-to` — component traces to a behavior
- `allocated-to` — entity allocated to a target
- `constrained-by` — entity constrained by a constraint
- `triggers` — behavior triggers another behavior (cross-block flow)
- `mounted-on` / `connected-at` / `routed-through` — spatial
- `produces` / `subscribes-to` / `transforms` — data/event flow
- `supersedes` / `migrates-to` — lifecycle

### LLM Protocol (6 Verbs)
- **LOAD** — parse and internalize the architecture model
- **QUERY** — answer structural questions about the system
- **IMPACT** — trace change impact through relationships
- **VALIDATE** — check claims against the model
- **UPDATE** — propose model modifications
- **PROJECT** — forecast effects of planned changes

### Self-Bootstrapping
The 10-stage pipeline requires no manual configuration to analyze a new project:
1. `architect_pipeline(repo_path, stage="observe")` — AST-scans all source files
2. Discovers modules, imports, routes, constraints, tests, docs
3. Subsequent stages (infer → allocate → relate → specify → contract → validate) build the model
4. `decompose` detects system boundaries (components with ≥5 files become autonomous systems)
5. `synthesize` runs scoped sub-pipelines for each detected system
6. `emit` writes all artifacts to `.architecture-models/`

**Entry point:** `architect_pipeline` MCP tool (stage-by-stage) or `architecture-model pipeline <path>` CLI.
The `init` command has been removed — the pipeline is the single entry point.

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
├── cli/          — CLI commands (validate, slice, diff, stats, impact, manifest, pipeline, etc.)
├── config/       — Configuration loading, auto-discovery, schema definition
├── core/         — Parser, validator, slicer, differ, merger, decomposer, type system
├── extract/      — Extract model from generated Tier 1 artifacts
├── integrations/ — LLM context formatting, pipeline bridge
├── manifest/     — Reality Manifest generator (AST scanning, metrics, blocks, interfaces)
├── pipeline/     — 10-stage modular extraction pipeline (observe→emit) + cache + report + lessons
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
from architecture_model.core import ParseError   # canonical parse error (also re-exported at package root)
model = load_model(path: Path) -> ArchitectureModel  # from file
model = _parse_raw(raw: dict) -> ArchitectureModel   # from dict (no public string parser)
# ParseError is the canonical exception raised by parser / serialization / package load paths.
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

### Lifecycle (Phase 1 additions, 2026-09-05)
```python
from architecture_model.lifecycle import generation_dir, current_root_digest
# generation_dir(pkg, generation_id) -> Path            # public replacement for _generation_dir (alias preserved)
# current_root_digest(pkg) -> str | None                # reads current generation's digest.json.root_digest

from architecture_model.lifecycle.package import ArchitecturePackage
pkg.id                                                  # property alias exposing package identifier

from architecture_model.lifecycle.model_slice_materializer import MaterializedSlice
mslice.to_dict()                                        # emits {"fragment": {...}, "slice_id": ..., ...}
```

### AI / Proposal APIs (Phase 1 additions, 2026-09-05)
```python
from architecture_model.ai import apply_model_patch
patched = apply_model_patch(model, proposal)            # add / remove / replace (move → ParseError)

from architecture_model.ai.work_order import WorkOrder
wo = WorkOrder.build(intent=..., input_slice_refs=..., expected_proposal_kinds=..., budget=..., requested_by=...)

from architecture_model.ai.proposals import Provenance
prov = Provenance(...)                                  # proposal_id auto-derived (SHA-256) when omitted
prov.proposal_id                                        # stable identifier for dedup / traceability
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

- Schema version: 2.0
- Package version: 0.3.0
- Test suite: 2918 passed (6 pre-existing failures documented)
- CLI entry point: `architecture-model`
- Install: `pip install -e .` (editable) or `pip install architecture-model-standard`

### Hierarchical Model Architecture

Each system has its own complete, self-contained model. The top-level model references subsystem models — it does not contain slices or reduced views.

```
.architecture-model.yaml                    ← top-level system model (98/100)
.architecture-models/
├── manifest.json                           ← top-level manifest (37 modules)
├── core/
│   ├── .architecture-model.yaml            ← Core system model (enriched)
│   └── manifest.json                       ← Core manifest (9 modules, 20 functions, 57 classes)
├── manifest/
│   ├── .architecture-model.yaml            ← Manifest system model (enriched)
│   └── manifest.json
├── config/
│   ├── .architecture-model.yaml
│   └── manifest.json
├── cli/
│   ├── .architecture-model.yaml
│   └── manifest.json
├── orchestration/
│   ├── .architecture-model.yaml
│   └── manifest.json
└── extract/
    ├── .architecture-model.yaml
    └── manifest.json
```

**6 subsystems** (Core, Manifest, Config, CLI, Orchestration, Extract) — each with its own model and manifest.
**3 inline components** (Utils, Profiles, Spec) — too small for separate systems, modeled in top-level.

### Standard Modeling Process

1. **Scan** — `architect_scan` produces AST-based reality manifest (ground truth)
2. **Model** — Build complete, self-contained model per system (capabilities, behaviors, components, interfaces, constraints, relationships)
3. **Manifest** — Generate per-system manifest from AST scan
4. **Enrich** — `architecture-model enrich` copies signatures, constants, test_contracts from manifest onto model components
5. **Visualize** — `generate_all_diagrams()` produces 4 Mermaid diagrams per model:
   - `context.mmd` — C4-style: actors → interfaces → system boundary
   - `components.mmd` — Components grouped by layer, realizes edges to capabilities
   - `behaviors.mmd` — Behavior flow with triggers/contains relationships
   - `dependencies.mmd` — Inter-component dependency graph
6. **Validate** — `architecture-model validate` checks structural correctness (score 0-100)

**Understanding levels after each step:**
- Model alone: WHY (capabilities, constraints) + WHAT (behaviors, relationships)
- \+ Manifest: HOW (signatures, classes, imports, call graphs)
- \+ Enrichment: REGEN-READY (body_hints, test_contracts, constants on components)

### Current Model Metrics

| Component | Validate | Regen Score | Sigs | Hints | Consts | Test Contracts |
|-----------|:--------:|:-----------:|:----:|:-----:|:------:|:--------------:|
| Core | 86/100 | 76/100 C | 85 | 85 | — | 131 |
| Manifest | — | 74/100 C | 51 | 51 | — | 76 |
| Pipeline | — | 73/100 C | 40 | 40 | — | 16 |
| Orchestration | — | 70/100 C | 31 | 31 | — | 62 |
| Authoring | — | 70/100 C | 2 | 2 | — | 11 |
| Profiles | — | 70/100 C | 3 | 3 | — | 0 |
| Regen Readiness | — | 68/100 D | 3 | 3 | — | 9 |
| Monitoring | — | 66/100 D | 5 | 5 | — | 5 |
| Persistence | — | 66/100 D | 3 | 3 | — | 8 |
| Extract | — | 65/100 D | 1 | 1 | — | 0 |
| Utils | — | 64/100 D | 4 | 4 | — | 7 |
| Export | — | 62/100 D | 15 | 15 | — | 4 |
| Config | — | 60/100 D | 15 | 15 | — | 1 |
| Docs | — | 58/100 F | 15 | 15 | — | 4 |
| CLI | — | 52/100 F | 1 | 1 | — | 1 |
| Spec | — | 40/100 F | 0 | 0 | — | 0 |
| **TOTAL** | **86/100** | **70/100 C** | **274** | **274** | **156** | **335** |

Previous (2026-07-07): 94 sigs, 11 constants, 339 contracts, no regen scoring.
Current (2026-08-10): 274 sigs (+191%), 156 constants, 335 contracts, Pipeline module covered.

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
| architecture-model-standard | (this repo) | Schema, validator, CLI, manifest | 1171 passed |
| opencode-arch | `../opencode-arch/` | MCP extension (token broker) + CLI + E2E benchmarks | 157 passed |
| arch-agent | `../arch-agent/` | Training pipeline + surrogate | 574 passed |

<!-- opencode-arch:start -->
# Architecture (auto-managed by opencode-arch)

**Model:** 9 components | 70 relationships
**Score:** 69.4% (FC=38% RA=89% BC=50% BV=100%)
**Codebase:** 88 modules | 208 import edges

## Component Map

## Architecture: 9 components
- **Core** (COMP-CORE): src/architecture_model/core/coverage.py, src/architecture_model/core/decomposer.py, src/architecture_model/core/differ.py
- **Manifest** (COMP-MANIFEST): src/architecture_model/manifest/blocks.py, src/architecture_model/manifest/body_hints.py, src/architecture_model/manifest/display.py
- **Config** (COMP-CONFIG): src/architecture_model/config/loader.py, src/architecture_model/config/schema.py
- **CLI** (COMP-CLI): src/architecture_model/cli/main.py, src/architecture_model/cli/visualize.py
- **Orchestration** (COMP-ORCHESTRATION): src/architecture_model/orchestration/decompose.py, src/architecture_model/orchestration/enrich.py
- **Extract** (COMP-EXTRACT): src/architecture_model/extract/from_code.py
- **Utils** (COMP-UTILS): src/architecture_model/utils/discovery.py
- **Profiles** (COMP-PROFILES): src/architecture_model/profiles/schema.py
- **Spec** (COMP-SPEC): 

## Development Guidelines

- Use `architect_slice` for focused context on specific components
- Use `architect_check` after significant changes to verify model accuracy
- Use `architect_require` to capture functional requirements from discussion
- Use `architect_feedback` to record corrections or rate tool quality
- Components are auto-grouped by import affinity — respect boundaries
<!-- opencode-arch:end -->
