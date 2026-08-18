# Component: Export (COMP-10)

**Status:** Status.ACTIVE
**Description:** Flat-file export for AI consumption, reference doc generation

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/export/__init__.py` | — | — |
| `src/architecture_model/export/flatfiles.py` | — | — |
| `src/architecture_model/export/reference.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-15 | realizes | Export produces flat files for AI |
| COMP-1.3 (Parser & Persistence) | depends-on | Export serializes model data |
| REQ-29 | satisfies | Export includes all artifact types |
| REQ-30 | satisfies | Export is self-contained for AI |

### Dependents (incoming)

None

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
