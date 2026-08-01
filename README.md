# architecture-model-standard

The open standard for architecture-as-code. Like OpenAPI, but for system architecture.

## Overview

Define your software architecture in YAML — entities, relationships, layers, constraints — in a format that is human-editable, git-diffable, and optimized for LLM token budgets. One command scans your codebase, produces a structured model, and compresses it into ~4000 tokens of dense context for AI-driven development.

```
Code --> [AST Scan] --> Reality Manifest --> [Architecture Model] --> LLM Context (50x compression)
```

**Key value:** A 50K-line codebase compressed to ~4000 tokens while preserving all structural relationships. Your AI coding tool understands your architecture without reading every file.

## Installation

```bash
pip install architecture-model-standard
```

Python 3.11+ required. For JS/TS projects, also see [@arch-model/scanner-js](#jsts-scanner).

## Quick Start

### One-Command Bootstrap

```bash
# Scan project, generate config, run pipeline, produce docs — all in one shot
architecture-model init /path/to/project

# Output:
#   .architecture-model.yaml          (config)
#   .architecture-models/              (manifests per F-block)
#   .architecture-models/docs/         (component specs, ICD, health report)
#
#   --- Token Savings ---
#   Source code: ~12,500 tokens (50,000 bytes)
#   Model:       ~250 tokens (1,000 bytes)
#   Compression: 50.0x (12,250 tokens saved)
```

For config-only (no pipeline): `architecture-model init . --config-only`

### Validate

```bash
architecture-model validate .architecture-model.yaml
```

### Generate Docs

```bash
architecture-model docs /path/to/project
# Produces: component specs, dependency matrix, ICD, health report
```

### Python API

```python
from architecture_model import (
    load_model,
    validate_model,
    generate_manifest,
    format_model_context,
    slice_by_fblock,
)
from architecture_model.core.compression import compute_compression_stats

# Load and validate a model
model = load_model("path/to/.architecture-model.yaml")
result = validate_model(model)
print(f"Score: {result.score}/100, Valid: {result.is_valid}")

# Generate a reality manifest from source code
manifest = generate_manifest("/path/to/project")

# Format model as compressed LLM context (token arbitrage)
context = format_model_context(model, max_tokens=4000, detail_level="standard")

# Slice model by functional block
sliced = slice_by_fblock(model, fblock_id="F1")

# See your token savings
stats = compute_compression_stats(Path("/path/to/project"))
print(f"Compression: {stats['compression_ratio']}x")
```

### AI Tool Integration

Works with any MCP-compatible tool. See [docs/integrations/](docs/integrations/) for setup guides:

| Tool | Method |
|------|--------|
| **OpenCode** | Built-in MCP (`opencode mcp add`) |
| **Cursor** | [MCP config](docs/integrations/cursor-mcp.md) + [.cursorrules](docs/integrations/.cursorrules) |
| **Cline** | [MCP config](docs/integrations/cline-mcp.md) |
| **Continue** | [MCP config](docs/integrations/continue-mcp.md) |

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

| Command | Description |
|---------|-------------|
| `init <path>` | **Full bootstrap** — scan, config, pipeline, docs, show token savings |
| `init <path> --config-only` | Only generate `.architecture-model.yaml` config |
| `validate <model.yaml>` | Check invariants, report score (0-100) |
| `docs <path>` | Generate component specs, ICD, dependency matrix, health report |
| `manifest <path>` | Generate reality manifest (AST scan) |
| `slice <model.yaml> --fblock F3` | Extract focused subset by F-block |
| `diff <old.yaml> <new.yaml>` | Structural comparison between model versions |
| `stats <model.yaml>` | Entity/relationship counts + compression ratio |
| `impact <model.yaml> CAP-F1` | Trace change impact through relationships |
| `decompose <path>` | Recursive decomposition into F-blocks |
| `enrich <model.yaml>` | Auto-enrich model with test contracts, patterns |
| `coverage <model.yaml>` | Check model coverage against source |
| `visualize <path>` | Generate Mermaid diagrams |

## JS/TS Scanner

For TypeScript/JavaScript projects, use the dedicated scanner:

```bash
# Via npx (recommended for JS/TS projects)
npx @arch-model/scanner-js /path/to/project

# Outputs .architecture-models/source-graph.json
# Then use: architecture-model init . (picks up source-graph.json automatically)
```

The scanner uses ts-morph for full type resolution, re-export handling, and JSDoc extraction. A Python regex fallback is available when Node.js is not installed.

## Package Structure

```
src/architecture_model/
├── cli/            — CLI commands (init, validate, docs, slice, diff, stats, etc.)
├── config/         — Configuration loading, auto-discovery, schema definition
├── core/           — Parser, validator, slicer, differ, merger, decomposer, compression
├── docs/           — Deterministic doc generators (component specs, ICD, health, drift)
├── integrations/   — LLM context formatting, pipeline bridge
├── manifest/       — Reality Manifest generator (AST scanning, grouping, TS scanner)
├── orchestration/  — Pipeline, auto-enrichment, source graph enrichment
└── spec/           — JSON Schema for model validation

packages/
└── scanner-js/     — @arch-model/scanner-js (ts-morph based TS/JS scanner)
```

## Generated Documentation

`architecture-model docs <repo>` produces:

| Document | Purpose |
|----------|---------|
| **Component Spec Sheet** | Per-component markdown (responsibilities, interfaces, dependencies) |
| **Dependency Matrix** | NxN coupling table between all components |
| **ICD** | Interface Control Document (provider→consumer contracts) |
| **Health Report** | Confidence scores, fill rates, token savings, action items |
| **Drift Report** | Changes since last extraction |
| **Index/README** | Links to all generated docs |

## Documentation

Detailed documentation is available in the `docs/` directory:

- [Specification](docs/specification.md) — Full schema specification (entity types, relationship types, validation rules, YAML format conventions)
- [LLM Protocol](docs/llm-protocol.md) — Integration protocol (6 verbs, slicing strategy, token budget management, integration patterns)

## Development

```bash
pip install -e ".[dev]"
pytest tests/ --ignore=tests/test_config_loader.py
```

## Status

| Item | Value |
|------|-------|
| Schema version | 1.4 |
| Package version | 1.0.0 |
| Python | 3.11+ |
| Test suite | 780+ tests passing |
| Entity types | 7 |
| Relationship types | 8 |
| CLI commands | 13 |
| Doc generators | 6 |
| AI tool integrations | 4 (OpenCode, Cursor, Cline, Continue) |
