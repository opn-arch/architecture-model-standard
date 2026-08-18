# Component: CLI (COMP-8)

**Status:** Status.ACTIVE
**Description:** Command-line interface — all user-facing commands

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/__init__.py` | — | — |
| `src/architecture_model/__main__.py` | — | — |
| `src/architecture_model/cli/__init__.py` | — | — |
| `src/architecture_model/cli/main.py` | — | — |
| `src/architecture_model/cli/visualize.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-1 (Core) | depends-on | CLI imports all core operations |
| COMP-2 (Pipeline) | depends-on | CLI orchestrates pipeline runs |
| COMP-3 (Manifest) | depends-on | CLI triggers manifest generation |
| COMP-4 (Documentation) | depends-on | CLI triggers doc generation |
| COMP-5 (Orchestration) | depends-on | CLI triggers enrichment/decomposition |
| COMP-7 (Authoring) | depends-on | CLI triggers authoring commands |
| REQ-26 | satisfies | CLI exposes all operations for MCP wrapping |

### Dependents (incoming)

None

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
