# architecture-model-standard

A universal, machine-readable Architecture-as-Code standard for LLM-driven system engineering.

## Overview

The Architecture Model Standard defines a YAML schema (v1.4) for capturing software system architecture — entities, relationships, constraints — in a format that is human-editable, git-diffable, and optimized for LLM token budgets. It serves as the architectural spine between raw code analysis and artifact generation: code is scanned into a Reality Manifest, parsed into a structured architecture model, and projected as compact context for LLM-driven code generation.

```
Code --> [AST Scan] --> Reality Manifest --> [Architecture Model] --> LLM Context --> Code Generation
```

## Installation

```bash
pip install architecture-model-standard
```

Python 3.11+ required.

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### CLI Usage

Initialize a project descriptor by scanning directory structure:

```bash
architecture-model init /path/to/project
```

Validate the model and report a consistency score:

```bash
architecture-model validate .architecture-model.yaml
```

### Python API

```python
from architecture_model import (
    load_model,
    validate_model,
    generate_manifest,
    format_model_context,
    slice_by_fblock,
    slice_by_layer,
)

# Load and validate a model
model = load_model("path/to/.architecture-model.yaml")
result = validate_model(model)
print(f"Score: {result.score}/100, Valid: {result.is_valid}")

# Generate a reality manifest from source code
manifest = generate_manifest("/path/to/project")

# Format model as compressed LLM context
context = format_model_context(model, max_tokens=4000, detail_level="standard")

# Slice model by functional block or layer
sliced = slice_by_fblock(model, fblock_id="F1")
```

## Schema Reference

### Entity Types

The schema defines seven entity types representing architectural building blocks:

| Type | ID Pattern | Description |
|------|-----------|-------------|
| Actors | `A-01`, `external-*` | External users or systems that interact with the system |
| Capabilities | `CAP-F1` | High-level functional groupings (F-blocks) the system provides |
| Behaviors | `BEH-01`, `UC-01` | Observable system actions, use cases, operational sequences |
| Interfaces | `IFC-01`, `intf-*` | APIs, protocols, and data exchange contracts between components |
| Constraints | `CON-01` | Non-functional requirements, quality attributes, design rules |
| Layers | `*-layer` | Logical architecture tiers (web, services, data, pipeline) |
| Components | `COMP-*` | Deployable units, modules, and packages that realize capabilities |

Every entity carries a `status` field: `ACTIVE`, `PLANNED`, or `DORMANT`.

### Relationship Types

Eight relationship types connect entities:

| Type | Semantics | Typical Direction |
|------|-----------|-------------------|
| `realizes` | Implementation relationship | Component --> Capability |
| `uses` | Service consumption | Component --> Interface |
| `constrains` | Quality constraint application | Constraint --> Entity |
| `contains` | Composition/ownership | Layer --> Component |
| `triggers` | Behavioral sequencing | Behavior --> Behavior |
| `depends_on` | Runtime dependency | Component --> Component |
| `implements` | Behavioral implementation | Component --> Behavior |
| `exposes` | Service provision | Component --> Interface |

## LLM Protocol

The model achieves approximately 14:1 compression versus full artifact text while preserving all structural relationships. Six protocol verbs define interactions between the model and LLMs:

| Verb | Purpose |
|------|---------|
| **LOAD** | Serialize model (or slice) into compact text for prompt injection. Supports `minimal` (~250 tokens), `standard` (~1,100 tokens), and `full` (~2,500 tokens) detail levels. |
| **QUERY** | Answer structural questions via graph traversal on relationship edges. No LLM inference required. |
| **IMPACT** | Trace change effects through relationships — given an entity, determine all affected entities and artifacts at configurable traversal depth. |
| **VALIDATE** | Check model invariants and report a consistency score (0-100) with categorized issues. |
| **UPDATE** | After generating or modifying an artifact, extract new entities and relationships and propose model changes in diff format. |
| **PROJECT** | Combine a model slice with a manifest slice into a single context block optimized for a specific artifact's regeneration. |

Integration example:

```python
from architecture_model.integrations.pipeline_bridge import enrich_manifest_slice

# Prepend model context before manifest data in artifact generation prompts
prompt_context = enrich_manifest_slice(manifest, "icd", project_root)
```

## CLI Reference

The `architecture-model` CLI provides commands for the full model lifecycle:

| Command | Description |
|---------|-------------|
| `init <path>` | Scan directory structure and generate `.architecture-model.yaml` |
| `extract <artifacts-dir>` | Build architecture model from markdown artifacts |
| `validate <model.yaml>` | Check invariants, report score (0-100) |
| `slice <model.yaml> --fblock F3` | Extract a focused subset of the model by functional block |
| `diff <old.yaml> <new.yaml>` | Structural comparison between two model versions |
| `query <model.yaml> "question"` | Answer structural questions via graph traversal |
| `context <model.yaml> --artifact icd` | Generate LLM context optimized for a specific artifact |
| `stats <model.yaml>` | Report entity and relationship counts |
| `impact <model.yaml> CAP-F1` | Trace change impact through relationships |
| `generate` | Test-guided code generation from architecture models |

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

## Documentation

Detailed documentation is available in the `docs/` directory:

- [Specification](docs/specification.md) — Full schema specification (entity types, relationship types, validation rules, YAML format conventions)
- [LLM Protocol](docs/llm-protocol.md) — Integration protocol (6 verbs, slicing strategy, token budget management, integration patterns)

## Development

Install in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest tests/ --ignore=tests/test_config_loader.py
```

## Status

| Item | Value |
|------|-------|
| Schema version | 1.4 |
| Package version | 0.3.0 |
| Python | 3.11+ |
| Test suite | 402 tests passing |
| Entity types | 7 |
| Relationship types | 8 |
| LLM protocol verbs | 6 |
| CLI commands | 10 |
