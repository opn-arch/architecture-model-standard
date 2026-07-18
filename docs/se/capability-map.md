---
artifact_id: capability-map
generated_at: 2026-07-11T16:08:49.173156+00:00
generator: opencode-arch-docs
---
# Capability Map — architecture-model-standard

## Overview

This document maps the system's functional capabilities to the components that realize them, showing how architectural responsibilities are distributed across the codebase.

## Capabilities

| ID | Capability | Priority | Realized By |
|----|-----------|----------|-------------|
| CAP-F1 | Model Parsing & Validation | Medium | COMP-CORE (core) |
| CAP-F2 | Reality Manifest Generation | Medium | COMP-MANIFEST (manifest) |
| CAP-F3 | Model Slicing & Diffing | Medium | COMP-CORE (core) |
| CAP-F4 | CLI Operations | Medium | COMP-CLI (cli) |
| CAP-F5 | Configuration & Schema | Medium | COMP-CONFIG (config), COMP-SPEC (spec) |

## Capability Details

### CAP-F1: Model Parsing & Validation

- **Priority:** Medium
- **Realized by:** core
- **Exposed interfaces:** Parser API, Validator API
- **Constraints:** Schema compliance (CON-SCHEMA), No orphaned entities (CON-NO-ORPHANS)
- **Consumers:** ACT-LLM (via Parser API)

### CAP-F2: Reality Manifest Generation

- **Priority:** Medium
- **Realized by:** manifest
- **Exposed interfaces:** Manifest API
- **Dependencies:** config

### CAP-F3: Model Slicing & Diffing

- **Priority:** Medium
- **Realized by:** core
- **Exposed interfaces:** Slicer API
- **Consumers:** ACT-LLM (via Slicer API)

### CAP-F4: CLI Operations

- **Priority:** Medium
- **Realized by:** cli
- **Exposed interfaces:** CLI Interface
- **Dependencies:** core, config, manifest
- **Consumers:** ACT-DEV (via CLI Interface)

### CAP-F5: Configuration & Schema

- **Priority:** Medium
- **Realized by:** config, spec
- **Constraints:** Schema compliance (CON-SCHEMA)

## Component-to-Capability Matrix

| Component | Realizes | Exposes | Depends On |
|-----------|----------|---------|------------|
| core | CAP-F1, CAP-F3 | Parser API, Validator API, Slicer API | config, spec |
| manifest | CAP-F2 | Manifest API | config |
| cli | CAP-F4 | CLI Interface | core, config, manifest |
| config | CAP-F5 | — | — |
| spec | CAP-F5 | — | — |

## Actor Access

| Actor | Interfaces Consumed | Capabilities Reached |
|-------|-------------------|---------------------|
| ACT-DEV (Developer) | CLI Interface | CAP-F4 → CAP-F1, CAP-F2, CAP-F3 |
| ACT-LLM (LLM Agent) | Parser API, Slicer API | CAP-F1, CAP-F3 |

## Dependency Graph

```plantuml
@startuml
title Dependency Graph - architecture-model-standard

rectangle "ACT-DEV" as ACT_DEV
rectangle "ACT-LLM" as ACT_LLM
rectangle "cli" as COMP_CLI
rectangle "config" as COMP_CONFIG
rectangle "core" as COMP_CORE
rectangle "manifest" as COMP_MANIFEST
rectangle "spec" as COMP_SPEC
rectangle "CLI Interface" as IF_CLI
rectangle "Manifest API" as IF_MANIFEST_API
rectangle "Parser API" as IF_PARSE_API
rectangle "Slicer API" as IF_SLICER_API
rectangle "Validator API" as IF_VALIDATE_API

COMP_CLI ..> IF_CLI : exposes
COMP_CORE ..> IF_PARSE_API : exposes
COMP_CORE ..> IF_VALIDATE_API : exposes
COMP_CORE ..> IF_SLICER_API : exposes
COMP_MANIFEST ..> IF_MANIFEST_API : exposes
COMP_CLI --> COMP_CORE : depends-on
COMP_CLI --> COMP_CONFIG : depends-on
COMP_CLI --> COMP_MANIFEST : depends-on
COMP_CORE --> COMP_CONFIG : depends-on
COMP_CORE --> COMP_SPEC : depends-on
COMP_MANIFEST --> COMP_CONFIG : depends-on
ACT_DEV ..> IF_CLI : consumes
ACT_LLM ..> IF_PARSE_API : consumes
ACT_LLM ..> IF_SLICER_API : consumes

@enduml
```
