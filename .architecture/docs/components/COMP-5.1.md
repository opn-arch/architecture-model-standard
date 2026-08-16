# Component: Enrichment (COMP-5.1)

**Status:** Status.ACTIVE
**Description:** Auto-enrich models with signatures, constants, test contracts, capabilities

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/orchestration/enrich.py` | — | — |
| `src/architecture_model/orchestration/auto_enrich.py` | — | — |
| `src/architecture_model/orchestration/enrichment_context.py` | — | — |
| `src/architecture_model/orchestration/capability_inference.py` | — | — |
| `src/architecture_model/orchestration/trigger_detection.py` | — | — |
| `src/architecture_model/orchestration/use_case_inference.py` | — | — |
| `src/architecture_model/orchestration/naming_context.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-10 | realizes | Enrichment implements code intelligence |
| COMP-3 (Manifest) | depends-on | Enrichment reads manifest data |
| COMP-1.1 (Type System) | depends-on | Enrichment populates core types |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-5 (Orchestration) | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
