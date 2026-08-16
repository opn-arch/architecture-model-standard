# Component: Synthesis & Emit Stages (COMP-2.5)

**Status:** Status.ACTIVE
**Description:** decompose + synthesize + emit: break down, merge, output final model

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/pipeline/decompose.py` | — | — |
| `src/architecture_model/pipeline/decompose_types.py` | — | — |
| `src/architecture_model/pipeline/synthesize.py` | — | — |
| `src/architecture_model/pipeline/synthesize_types.py` | — | — |
| `src/architecture_model/pipeline/emit.py` | — | — |
| `src/architecture_model/pipeline/emit_types.py` | — | — |
| `src/architecture_model/pipeline/regen_score.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-1.3 (Parser & Persistence) | depends-on | Emit stage uses parser for YAML output |

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
