---
artifact_id: constraint-register
generated_at: 2026-07-11T16:10:42.573529+00:00
generator: opencode-arch-docs
---
# Constraint Register

## Overview

This document defines the non-functional requirements and design constraints for the architecture-model-standard project, including their allocation to specific components.

## Constraints

### CON-SCHEMA: Schema Compliance

| Field | Value |
|-------|-------|
| **ID** | CON-SCHEMA |
| **Name** | Schema Compliance |
| **Type** | Technology |
| **Metric** | — |
| **Threshold** | — |
| **Rationale** | Ensures all architectural models conform to the defined JSON/YAML schema, guaranteeing interoperability between components that produce and consume model data. |

### CON-NO-ORPHANS: No Orphaned Entities

| Field | Value |
|-------|-------|
| **ID** | CON-NO-ORPHANS |
| **Name** | No Orphaned Entities |
| **Type** | Technology |
| **Metric** | — |
| **Threshold** | — |
| **Rationale** | Ensures every entity declared in the model participates in at least one relationship, preventing dead or unreachable elements that would degrade model quality and confuse consumers. |

## Constraint Allocation

| Constraint | Constrained Components |
|------------|----------------------|
| CON-SCHEMA | COMP-CORE, COMP-SPEC |
| CON-NO-ORPHANS | COMP-CORE |

### Allocation Detail

```
CON-SCHEMA
├── COMP-CORE    (parser, validator, slicer)
└── COMP-SPEC    (JSON Schema definitions)

CON-NO-ORPHANS
└── COMP-CORE    (validator enforces orphan detection)
```

### Dependency Context

Components constrained by CON-SCHEMA form a validation chain:

- **COMP-SPEC** defines the schema artifacts that express CON-SCHEMA formally.
- **COMP-CORE** depends on COMP-SPEC and enforces CON-SCHEMA at parse and validation time.
- **COMP-CORE** also enforces CON-NO-ORPHANS during validation, checking that all entities participate in at least one relationship.

Downstream consumers (COMP-CLI, COMP-MANIFEST) are not directly constrained but inherit schema compliance through their dependency on COMP-CORE.
