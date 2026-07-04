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

## Role in the Knowledge OS

The Knowledge OS is a multi-modal knowledge architecture combining:
- Structured data (PostgreSQL + pgvector)
- Code intelligence (AST analysis, import graphs, domain tagging)
- LLM synthesis (architecture generation, artifact production)
- MBSE artifacts (27 system engineering documents generated per project)

This package is the **architectural layer** — it sits between raw code analysis and artifact generation:

```
Code → [AST Scan] → Reality Manifest → [Architecture Model] → LLM Context → Artifact Generation
```

When the pipeline's `synthesize` stage produces architecture JSON via LLM, this package:
1. Validates the output against the schema (7 entity types, 8 relationship types)
2. Writes/refines `.architecture-model.yaml` (the project descriptor)
3. Provides structured context slices to downstream artifact generators via `enrich_manifest_slice()`

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
├── cli/          — CLI commands (init, extract, validate, slice, diff, query, context, stats, impact)
├── config/       — Configuration loading, auto-discovery, schema definition
├── core/         — Parser, validator, slicer, differ, type system
├── extract/      — Extract model from generated Tier 1 artifacts
├── integrations/ — LLM context formatting, pipeline bridge
├── manifest/     — Reality Manifest generator (AST scanning, metrics, blocks, interfaces)
└── spec/         — JSON Schema for model validation
```

## Status

- Schema version: 1.0
- Package version: 0.1.0
- Test suite: 34 unit tests (standalone), 140 total with integration fixtures
- Validation score: 100/100, 0 orphaned entities
- CLI entry point: `architecture-model`
- Install: `pip install -e .` (editable) or `pip install architecture-model-standard`
