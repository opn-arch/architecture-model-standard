# Component: Manifest (COMP-3)

**Status:** Status.ACTIVE
**Description:** Source code scanning — AST analysis, import resolution, grouping

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/manifest/__init__.py` | — | — |
| `src/architecture_model/manifest/types.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-4 | realizes | Manifest implements reality manifest generation |
| COMP-3.1 (Scanners) | contains | — |
| COMP-3.2 (Graph & Analysis) | contains | — |
| COMP-3.3 (Grouping & Generation) | contains | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-5.1 (Enrichment) | depends-on | Enrichment reads manifest data |
| COMP-7 (Authoring) | depends-on | Gate check reads manifest |
| COMP-8 (CLI) | depends-on | CLI triggers manifest generation |

## Behaviors Realized

None

## Patterns

None

## Confidence

5%
