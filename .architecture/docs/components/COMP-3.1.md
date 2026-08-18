# Component: Scanners (COMP-3.1)

**Status:** Status.ACTIVE
**Description:** Language-specific source file scanners (Python, TypeScript, Kotlin)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/manifest/scanner.py` | — | — |
| `src/architecture_model/manifest/multi_scanner.py` | — | — |
| `src/architecture_model/manifest/ts_scanner.py` | — | — |
| `src/architecture_model/manifest/kt_scanner.py` | — | — |
| `src/architecture_model/manifest/body_hints.py` | — | — |
| `src/architecture_model/manifest/metrics.py` | — | — |
| `src/architecture_model/manifest/scan_cache.py` | — | — |
| `src/architecture_model/manifest/protocol.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-9 (Configuration) | depends-on | Scanners use config for exclusion patterns |
| REQ-8 | satisfies | Scanners cover all Python files |
| REQ-10 | satisfies | Multi-scanner supports Python/TS/Kotlin |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-2.2 (Observation Stages) | depends-on | Observe stage uses scanners for code facts |
| COMP-3.2 (Graph & Analysis) | depends-on | Graph analysis builds on scanner output |
| COMP-6 (Extract) | depends-on | Extract uses scanners for code analysis |
| COMP-3 (Manifest) | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

30%
