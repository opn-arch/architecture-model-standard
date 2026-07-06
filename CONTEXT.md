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

## Package Structure

```
src/architecture_model/
├── cli/          — CLI commands (init, extract, validate, slice, diff, query, context, stats, impact, generate)
├── config/       — Configuration loading, auto-discovery, schema definition
├── core/         — Parser, validator, slicer, differ, merger, decomposer, type system
├── extract/      — Extract model from generated Tier 1 artifacts
├── integrations/ — LLM context formatting, pipeline bridge
├── manifest/     — Reality Manifest generator (AST scanning, metrics, blocks, interfaces)
└── spec/         — JSON Schema for model validation
```

## Key APIs (used by opencode-arch)

### Manifest Generation
```python
from architecture_model.manifest.generator import generate_manifest
manifest = generate_manifest(project_root: Path) -> dict
# Returns: {project_root, modules, metrics, functional_blocks, ...}
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

- Schema version: 1.3
- Package version: 0.3.0
- Test suite: 271 passed, 106 skipped
- Validation score: 100/100, 0 orphaned entities
- CLI entry point: `architecture-model`
- Install: `pip install -e .` (editable) or `pip install architecture-model-standard`

## Development Instructions

- Always run tests with: `pytest tests/ -v --ignore=tests/test_config_loader.py` (pre-existing failure)
- Training module has been moved to `arch-agent` repo — do not add training code here
- This is the schema-only open standard — keep it focused on parse/validate/slice/format
- The `opencode-arch` package depends on this — API changes need coordination

## Related Repos

| Repo | Path | Purpose | Tests |
|------|------|---------|-------|
| architecture-model-standard | (this repo) | Schema, validator, CLI, manifest | 271 passed |
| opencode-arch | `../opencode-arch/` | MCP extension (token broker) | 28 passed |
| arch-agent | `../arch-agent/` | Training pipeline + surrogate | 574 passed |
