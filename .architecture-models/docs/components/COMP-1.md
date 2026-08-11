# Component: Authoring (COMP-1)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/authoring/gate.py` | — | — |
| `src/architecture_model/authoring/parser.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `check_development_gate` | `model: ArchitectureModel, manifest: Manifest, phase: str | None` | `GateResult` | Check if code reality is tracking toward authored architecture intent.

Args:
    model: The architecture model to check.
    manifest: The reality manifest from code scanning.
    phase: Override lifecycle phase ("concept" or "production").
           If None, defaults to "production". |
| `parse_requirements_doc` | `text: str` | `ArchitectureModel` | Parse a markdown requirements document into an ArchitectureModel.

Supported sections: # Actors, # Capabilities, # Constraints (case-insensitive). |

## Interface Dependencies

- **requires** `uses_Core` → COMP-4 (Core) [Status, RelationType, ActorType, InterfaceType, ConstraintType, Priority, Strength, ComponentKind, BehaviorPattern, SymbolKind]
- **requires** `uses_Manifest` → COMP-3 (Manifest) [ModuleStatus, FunctionInfo, ClassInfo, ImportDetail, DecoratedFunction, ModuleInfo, InterfaceEdge, SubFunctionEntry, BlockManifest, MetricsResult]
- **provides** `exposes_to_Pipeline` → COMP-2 (Pipeline) [parse_requirements_doc]

## Patterns

None

## Confidence

82%
