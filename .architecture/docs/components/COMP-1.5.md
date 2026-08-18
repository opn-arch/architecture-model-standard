# Component: Quality Metrics (COMP-1.5)

**Status:** Status.ACTIVE
**Description:** Confidence scoring, regen readiness, corrections tracking

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/core/confidence.py` | — | — |
| `src/architecture_model/core/regen_readiness.py` | — | — |
| `src/architecture_model/core/corrections.py` | — | — |
| `src/architecture_model/core/decomposer.py` | — | — |
| `src/architecture_model/core/visualize.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-11 | realizes | Quality Metrics implements regen readiness |
| REQ-15 | satisfies | Regen readiness scoring |
| REQ-16 | satisfies | Per-component readiness with blockers |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-5.2 (Decomposition) | depends-on | Decomposition uses quality metrics |
| COMP-1 (Core) | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
