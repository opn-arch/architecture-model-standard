# Component: Validation (COMP-1.2)

**Status:** Status.ACTIVE
**Description:** Model validation — JSON schema, referential integrity, hierarchy, cycles, domain rules

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/core/validator.py` | — | — |
| `src/architecture_model/spec/__init__.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-1 | realizes | Validator implements model validation |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-2.4 (Specification & Contract Stages) | depends-on | Validate stage invokes core validator |
| COMP-1 (Core) | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
