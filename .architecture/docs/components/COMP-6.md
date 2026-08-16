# Component: Extract (COMP-6)

**Status:** Status.ACTIVE
**Description:** Code-to-model extraction — route detection, constraint detection, artifact parsing

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/extract/from_code.py` | — | — |
| `src/architecture_model/extract/from_artifacts.py` | — | — |
| `src/architecture_model/extract/route_detector.py` | — | — |
| `src/architecture_model/extract/constraint_detector.py` | — | — |
| `src/architecture_model/extract/table_parser.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-2 | realizes | Extract implements code-to-model extraction |
| COMP-3.1 (Scanners) | depends-on | Extract uses scanners for code analysis |
| COMP-9 (Configuration) | depends-on | Extract uses config for settings |

### Dependents (incoming)

None

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
