# Component: Pipeline (COMP-2)

**Status:** Status.ACTIVE
**Description:** Modular 10-stage extraction pipeline with coordination and caching

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/pipeline/__init__.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-3 | realizes | Pipeline implements 10-stage extraction |
| COMP-2.1 (Pipeline Coordination) | contains | — |
| COMP-2.2 (Observation Stages) | contains | — |
| COMP-2.3 (Allocation & Relation Stages) | contains | — |
| COMP-2.4 (Specification & Contract Stages) | contains | — |
| COMP-2.5 (Synthesis & Emit Stages) | contains | — |
| COMP-11 (Pipeline Learning) | contains | — |
| REQ-25 | satisfies | Pipeline completes large repos without LLM |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-8 (CLI) | depends-on | CLI orchestrates pipeline runs |

## Behaviors Realized

None

## Patterns

None

## Confidence

5%
