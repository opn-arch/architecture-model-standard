# Component: Core Doc Generators (COMP-4.1)

**Status:** Status.ACTIVE
**Description:** Component spec, ICD, dependency matrix, health report, drift, diagrams

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/docs/generator.py` | — | — |
| `src/architecture_model/docs/component_spec.py` | — | — |
| `src/architecture_model/docs/icd.py` | — | — |
| `src/architecture_model/docs/dependency_matrix.py` | — | — |
| `src/architecture_model/docs/health.py` | — | — |
| `src/architecture_model/docs/drift.py` | — | — |
| `src/architecture_model/docs/diagrams.py` | — | — |
| `src/architecture_model/docs/index.py` | — | — |
| `src/architecture_model/docs/behavior_spec.py` | — | — |
| `src/architecture_model/docs/integration_flows.py` | — | — |
| `src/architecture_model/docs/system_design.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-1.1 (Type System) | depends-on | Doc generators read model types |
| REQ-11 | satisfies | Template-based generators run in <1s |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-4.2 (SE Document Suite) | depends-on | SE docs build on core doc generators |
| COMP-4 (Documentation) | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
