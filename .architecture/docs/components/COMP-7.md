# Component: Authoring (COMP-7)

**Status:** Status.ACTIVE
**Description:** Forward-author models from requirements, check development gates

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/authoring/__init__.py` | — | — |
| `src/architecture_model/authoring/parser.py` | — | — |
| `src/architecture_model/authoring/gate.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-6 | realizes | Authoring implements requirements-to-model |
| CAP-12 | realizes | Authoring gate check |
| COMP-1.1 (Type System) | depends-on | Authoring produces core model types |
| COMP-3 (Manifest) | depends-on | Gate check reads manifest |
| REQ-14 | satisfies | Authoring parser handles markdown requirements |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-8 (CLI) | depends-on | CLI triggers authoring commands |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
