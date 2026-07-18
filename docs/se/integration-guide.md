---
artifact_id: integration-guide
generated_at: 2026-07-11T16:11:54.797422+00:00
generator: opencode-arch-docs
---
# Integration Guide — Architecture Model Standard

## Overview

This guide documents the available interfaces, integration patterns, and constraints for developers connecting to the Architecture Model Standard system.

## Available Interfaces

The system exposes five internal interfaces:

| Interface ID | Name | Type | Protocol | Data Format |
|-------------|------|------|----------|-------------|
| IF-CLI | CLI Interface | Internal | CLI | YAML/Text |
| IF-PARSE-API | Parser API | Internal | Python API | Python objects |
| IF-VALIDATE-API | Validator API | Internal | Python API | Python objects |
| IF-MANIFEST-API | Manifest API | Internal | Python API | Python objects |
| IF-SLICER-API | Slicer API | Internal | Python API | Python objects |

All interfaces are internal, meaning they are consumed as library imports or CLI invocations rather than network services.

## Integration Patterns

### Component Architecture

The system is composed of five active service components:

| Component | ID | Status | Role |
|-----------|----|--------|------|
| core | COMP-CORE | ACTIVE | Parsing, validation, and slicing |
| manifest | COMP-MANIFEST | ACTIVE | Reality manifest generation |
| config | COMP-CONFIG | ACTIVE | Configuration loading and discovery |
| spec | COMP-SPEC | ACTIVE | JSON Schema definitions |
| cli | COMP-CLI | ACTIVE | Command-line entry point |

### Consumer Roles

- **Developer** — Consumes the CLI Interface (IF-CLI)
- **LLM Agent** — Consumes the Parser API (IF-PARSE-API) and Slicer API (IF-SLICER-API)

### Recommended Integration by Component

#### CLI (COMP-CLI)

Use for: Human-driven workflows and shell scripting.

- Exposes: IF-CLI
- Depends on: core, config, manifest

Integrate via the `architecture-model` command-line entry point. Suitable for CI/CD pipelines and developer tooling.

#### Core (COMP-CORE)

Use for: Programmatic access to parsing, validation, and slicing.

- Exposes: IF-PARSE-API, IF-VALIDATE-API, IF-SLICER-API
- Depends on: config, spec

This is the primary integration point for LLM agents and automated systems. Import directly from the `architecture_model.core` package.

#### Manifest (COMP-MANIFEST)

Use for: Generating reality manifests from source code via AST scanning.

- Exposes: IF-MANIFEST-API
- Depends on: config

Integrate by importing `architecture_model.manifest.generator`.

#### Config (COMP-CONFIG)

Use for: Configuration loading and project auto-discovery.

- No exposed external interface
- Used internally by cli, core, and manifest

Not intended for direct external integration. Consumed transitively through other components.

#### Spec (COMP-SPEC)

Use for: JSON Schema definitions for model validation.

- No exposed external interface
- Used internally by core

Not intended for direct external integration.

### Dependency Flow

```
cli → core → config
cli → config        core → spec
cli → manifest → config
```

## Authentication & Constraints

### Security Model

All interfaces are internal (in-process). There are no network-level authentication or authorization requirements. Access control is handled at the filesystem and process level.

### Architectural Constraints

| Constraint ID | Name | Type | Description |
|--------------|------|------|-------------|
| CON-SCHEMA | Schema Compliance | Technology | All architecture models must comply with the defined YAML schema |
| CON-NO-ORPHANS | No Orphaned Entities | Technology | All entities in the model must participate in at least one relationship |

#### CON-SCHEMA: Schema Compliance

Any model submitted for validation or parsing must conform to the architecture model schema. Non-compliant models will be rejected by the validator.

#### CON-NO-ORPHANS: No Orphaned Entities

Every entity defined in a model must be connected to at least one other entity via a relationship. The validator flags orphaned entities as validation issues.

## Integration Checklist

1. Identify your consumer role (Developer or LLM Agent)
2. Select the appropriate interface based on your use case
3. Import from the corresponding component package
4. Ensure input models satisfy both schema compliance and no-orphan constraints
5. Handle validation results (score, issues, is_valid) in your integration logic
