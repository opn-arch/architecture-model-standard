# System Design: architecture-model-standard

## Architecture Overview

—
Schema version: 2.0

## Component Inventory

| ID | Name | Status | Files | Behaviors |
|----|------|--------|-------|-----------|
| COMP-CORE | Core | Status.ACTIVE | 9 | 3 |
| COMP-MANIFEST | Manifest | Status.ACTIVE | 11 | 1 |
| COMP-CONFIG | Config | Status.ACTIVE | 2 | 1 |
| COMP-CLI | CLI | Status.ACTIVE | 2 | 1 |
| COMP-ORCHESTRATION | Orchestration | Status.ACTIVE | 2 | 1 |
| COMP-EXTRACT | Extract | Status.ACTIVE | 1 | 1 |
| COMP-UTILS | Utils | Status.ACTIVE | 1 | 1 |
| COMP-PROFILES | Profiles | Status.ACTIVE | 1 | 1 |
| COMP-SPEC | Spec | Status.ACTIVE | 0 | 1 |

## Layer Structure

- **Library** (LAYER-LIB)
- **Orchestration** (LAYER-ORCH)
- **User Interface** (LAYER-UI)

## Key Behaviors

- **CRUD: 6 CRUD endpoints (1 CLI, 4 CLI:, 1 MCP)** (BEH-CRUD-_unknown)

## Relationship Summary

| Type | Count |
|------|-------|
| allocated-to | 9 |
| constrained-by | 2 |
| consumes | 7 |
| depends-on | 19 |
| exposes | 13 |
| realizes | 11 |
| traces-to | 9 |

## Architecture Diagram

```mermaid
graph TD
  COMP-CLI[CLI] --> COMP-CORE[Core]
  COMP-CLI[CLI] --> COMP-CONFIG[Config]
  COMP-CLI[CLI] --> COMP-MANIFEST[Manifest]
  COMP-CLI[CLI] --> COMP-ORCHESTRATION[Orchestration]
  COMP-ORCHESTRATION[Orchestration] --> COMP-CORE[Core]
  COMP-ORCHESTRATION[Orchestration] --> COMP-MANIFEST[Manifest]
  COMP-ORCHESTRATION[Orchestration] --> COMP-CONFIG[Config]
  COMP-EXTRACT[Extract] --> COMP-CORE[Core]
  COMP-EXTRACT[Extract] --> COMP-CONFIG[Config]
  COMP-EXTRACT[Extract] --> COMP-MANIFEST[Manifest]
  COMP-CORE[Core] --> COMP-UTILS[Utils]
  COMP-MANIFEST[Manifest] --> COMP-UTILS[Utils]
  COMP-CONFIG[Config] --> COMP-UTILS[Utils]
  COMP-CORE[Core] --> COMP-PROFILES[Profiles]
  COMP-CORE[Core] --> COMP-SPEC[Spec]
  COMP-CORE[Core] --> COMP-CONFIG[Config]
  COMP-CORE[Core] --> COMP-MANIFEST[Manifest]
  COMP-MANIFEST[Manifest] --> COMP-CONFIG[Config]
  COMP-MANIFEST[Manifest] --> COMP-CORE[Core]
```
