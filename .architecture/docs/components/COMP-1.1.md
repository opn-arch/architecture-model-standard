# Component: Type System (COMP-1.1)

**Status:** Status.ACTIVE
**Description:** All dataclasses, enums, and type definitions for the architecture model

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/core/types.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-2.1 (Pipeline Coordination) | depends-on | Pipeline coordination uses core types |
| COMP-2.3 (Allocation & Relation Stages) | depends-on | Allocation uses core types and model structure |
| COMP-4.1 (Core Doc Generators) | depends-on | Doc generators read model types |
| COMP-5.1 (Enrichment) | depends-on | Enrichment populates core types |
| COMP-7 (Authoring) | depends-on | Authoring produces core model types |
| COMP-1 (Core) | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
