# Component: Docs (COMP-3)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/docs/behavior_spec.py` | — | — |
| `src/architecture_model/docs/component_spec.py` | — | — |
| `src/architecture_model/docs/dependency_matrix.py` | — | — |
| `src/architecture_model/docs/diagrams.py` | — | — |
| `src/architecture_model/docs/drift.py` | — | — |
| `src/architecture_model/docs/generator.py` | — | — |
| `src/architecture_model/docs/health.py` | — | — |
| `src/architecture_model/docs/icd.py` | — | — |
| `src/architecture_model/docs/index.py` | — | — |
| `src/architecture_model/docs/integration_flows.py` | — | — |
| `src/architecture_model/docs/system_design.py` | — | — |

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
| `generate_behavior_spec` | `behavior: Behavior, flow_trace: FlowTrace, scoped_manifest: Manifest, file_to_comp: dict[str, str]` | `str` | Generate a markdown spec for a single cross-component behavior. |
| `generate_behavior_index` | `classification: BehaviorClassification, crud_summaries: dict[str, CrudSummary]` | `str` | Generate a markdown index of all behaviors. |
| `generate_component_spec` | `comp: 'Component', model: 'ArchitectureModel'` | `str` | Generate a rich markdown spec sheet for a single component. |
| `generate_dependency_matrix` | `model: 'ArchitectureModel'` | `str` | Generate an NxN dependency matrix as markdown. |
| `generate_component_diagram` | `model: 'ArchitectureModel'` | `str` | Generate a Mermaid graph TD showing components and their relationships. |
| `generate_use_case_diagram` | `model: 'ArchitectureModel'` | `str` | Generate Mermaid sequence diagrams for use-case behaviors. |
| `generate_system_boundary_diagram` | `model: 'ArchitectureModel'` | `str` | Generate a Mermaid graph TD with subgraph per system. |
| `generate_all_diagrams` | `model: 'ArchitectureModel', output_dir: Path` | `list[Path]` | Generate all diagrams, write to output_dir, return list of paths. |
| `generate_drift_report` | `old_model: 'ArchitectureModel', new_model: 'ArchitectureModel'` | `str` | Generate change report comparing two model versions. |
| `generate_docs` | `model: 'ArchitectureModel', output_dir: Path | str, manifest: dict | None, previous_model: 'ArchitectureModel | None'` | `dict[str, list[Path]]` | Generate architecture documentation.

Returns dict of category -> list of generated file paths. |
| `generate_health_report` | `model: 'ArchitectureModel', manifest: 'Manifest | None', root: 'Path | None'` | `str` | Generate architecture health metrics. |
| `generate_icd` | `model: 'ArchitectureModel'` | `str` | Generate ICD documenting inter-component interfaces. |
| `generate_index` | `model: 'ArchitectureModel', doc_paths: dict[str, list[Path]]` | `str` | Generate README.md index linking to all docs. |
| `generate_integration_flows` | `model: 'ArchitectureModel'` | `str` | Generate integration flow documentation for cross-component relationships. |
| `generate_system_design` | `model: 'ArchitectureModel', manifest` | `str` | Generate a system design document from an architecture model. |

## Interface Dependencies

- **requires** `uses_Core` → COMP-1 (Core) [Status, RelationType, ActorType, InterfaceType, ConstraintType, Priority, Strength, ComponentKind, BehaviorPattern, SymbolKind]
- **requires** `uses_Manifest` → COMP-2 (Manifest) [build_call_graph, trace_flow, map_flow_to_components, CallGraph, FlowTrace]
- **provides** `exposes_to_Core` → COMP-1 (Core) [generate_docs]

## Patterns

None

## Confidence

75%
