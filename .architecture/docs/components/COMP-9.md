# Component: Configuration (COMP-9)

**Status:** Status.ACTIVE
**Description:** Configuration loading, domain profiles, schema definitions

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/config/__init__.py` | — | — |
| `src/architecture_model/config/loader.py` | — | — |
| `src/architecture_model/config/schema.py` | — | — |
| `src/architecture_model/profiles/__init__.py` | — | — |
| `src/architecture_model/profiles/builtins/__init__.py` | — | — |
| `src/architecture_model/profiles/schema.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-3.1 (Scanners) | depends-on | Scanners use config for exclusion patterns |
| COMP-6 (Extract) | depends-on | Extract uses config for settings |
| COMP-11 (Pipeline Learning) | depends-on | Learning store uses config for paths |
| COMP-12 (Utilities) | depends-on | Utilities use config |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
