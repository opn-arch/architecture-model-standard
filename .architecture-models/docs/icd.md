# Interface Control Document

**Project:** architecture-model-standard

**Total Interfaces:** 8

## Core (COMP-1)

**Contract:** Development gate: check if code reality tracks toward authored architecture intent

### → Docs (COMP-3)

**Symbols:** `Status`, `RelationType`, `ActorType`, `InterfaceType`, `ConstraintType`, `Priority`, `Strength`, `ComponentKind`, `BehaviorPattern`, `SymbolKind`

### → Manifest (COMP-2)

**Symbols:** `Status`, `RelationType`, `ActorType`, `InterfaceType`, `ConstraintType`, `Priority`, `Strength`, `ComponentKind`, `BehaviorPattern`, `SymbolKind`

### → Store (COMP-5)

**Symbols:** `load_block_model`, `load_model`, `validate_model_data`, `dump_model`, `save_model`

| Function | Signature | Description |
|----------|-----------|-------------|
| `load_block_model` | `(project_root: str | Path, block_id: str, output_dir: str) → ArchitectureModel | None` | Load a block sub-model from the .architecture-models/ direct |
| `load_model` | `(path: str | Path) → ArchitectureModel` | Load and parse an architecture model YAML file. |
| `validate_model_data` | `(data: dict[str, Any]) → list[str]` | Validate raw dict against JSON Schema. Returns list of error |
| `dump_model` | `(model: ArchitectureModel) → dict[str, Any]` | Serialize ArchitectureModel back to a plain dict suitable fo |
| `save_model` | `(model: ArchitectureModel, path: str | Path) → None` | Serialize and write model to YAML file. |

## Manifest (COMP-2)

**Contract:** Configuration loader for the Architecture Model Standard

### → Core (COMP-1)

**Symbols:** `ModuleStatus`, `FunctionInfo`, `ClassInfo`, `ImportDetail`, `DecoratedFunction`, `ModuleInfo`, `InterfaceEdge`, `SubFunctionEntry`, `BlockManifest`, `MetricsResult`

### → Docs (COMP-3)

**Symbols:** `build_call_graph`, `trace_flow`, `map_flow_to_components`, `CallGraph`, `FlowTrace`

| Function | Signature | Description |
|----------|-----------|-------------|
| `build_call_graph` | `(manifest: Manifest) → CallGraph` | Build a resolved call graph from manifest data. |
| `trace_flow` | `(graph: CallGraph, entry: str, max_depth: int) → FlowTrace` | BFS from entry point, following call edges. |
| `map_flow_to_components` | `(flow: FlowTrace, file_to_comp: dict[str, str]) → FlowTrace` | Populate components_crossed on a FlowTrace. |

## Docs (COMP-3)

**Contract:** Behavior spec document generator — Mermaid sequence diagrams and index

### → Core (COMP-1)

**Symbols:** `generate_docs`

| Function | Signature | Description |
|----------|-----------|-------------|
| `generate_docs` | `(model: 'ArchitectureModel', output_dir: Path | str, manifest: dict | None, previous_model: 'ArchitectureModel | None') → dict[str, list[Path]]` | Generate architecture documentation.

Returns dict of catego |

## Store (COMP-5)

**Contract:** Persist architecture artifacts to

### → Core (COMP-1)

**Symbols:** `save_project`, `save_block`, `load_project`, `ProjectSnapshot`

| Function | Signature | Description |
|----------|-----------|-------------|
| `save_project` | `(root: Path, model: Any, manifest: Any, representativeness: Any | None, telemetry: dict | None) → Path` | Persist model + manifest + metrics to .architecture/ directo |
| `save_block` | `(root: Path, block_id: str, model: Any, manifest: Any, representativeness: Any | None) → Path` | Persist a hierarchical block's artifacts to .architecture/<b |
| `load_project` | `(root: Path) → ProjectSnapshot` | Load model + manifest + metrics from .architecture/ director |

## Schema (COMP-6)

**Contract:** Domain profile schema and loading logic

### → Core (COMP-1)

**Symbols:** `load_profile`, `EnumExtension`, `EntityExtension`, `ConditionalRule`, `DomainProfile`

| Function | Signature | Description |
|----------|-----------|-------------|
| `load_profile` | `(name_or_path: str) → DomainProfile` |  |
