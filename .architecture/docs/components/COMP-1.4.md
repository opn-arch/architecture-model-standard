# Component: Model Operations (COMP-1.4)

**Status:** Status.ACTIVE
**Description:** Slice, diff, coverage, impact analysis, clustering, source block assignment

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/core/slicer.py` | — | — |
| `src/architecture_model/core/differ.py` | — | — |
| `src/architecture_model/core/coverage.py` | — | — |
| `src/architecture_model/core/cluster.py` | — | — |
| `src/architecture_model/core/source_block_assign.py` | — | — |
| `src/architecture_model/core/source_block_quality.py` | — | — |
| `src/architecture_model/core/representativeness.py` | — | — |
| `src/architecture_model/core/test_affinity.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-7 | realizes | Model Operations implements slice and query |
| CAP-8 | realizes | Model Operations implements model diff |
| CAP-13 | realizes | Coverage/representativeness detects drift |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-1 (Core) | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
