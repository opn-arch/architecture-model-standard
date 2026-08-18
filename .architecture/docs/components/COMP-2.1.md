# Component: Pipeline Coordination (COMP-2.1)

**Status:** Status.ACTIVE
**Description:** Stage orchestration, context management, caching, reporting

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/pipeline/coordinator.py` | — | — |
| `src/architecture_model/pipeline/protocol.py` | — | — |
| `src/architecture_model/pipeline/cache.py` | — | — |
| `src/architecture_model/pipeline/context_gen.py` | — | — |
| `src/architecture_model/pipeline/report.py` | — | — |
| `src/architecture_model/pipeline/artifacts.py` | — | — |
| `src/architecture_model/pipeline/corrections.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-1.1 (Type System) | depends-on | Pipeline coordination uses core types |
| REQ-6 | satisfies | Pipeline coordinator runs deterministically |
| REQ-7 | satisfies | Stage caching enables independent runs |
| REQ-23 | satisfies | Coordinator catches stage failures gracefully |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-2 (Pipeline) | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
