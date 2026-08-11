# Interface Control Document

**Project:** architecture-model-standard

**Total Interfaces:** 11

## Authoring (COMP-1)

**Contract:** Development gate: check if code reality tracks toward authored architecture intent

### → Pipeline (COMP-2)

**Symbols:** `parse_requirements_doc`

| Function | Signature | Description |
|----------|-----------|-------------|
| `parse_requirements_doc` | `(text: str) → ArchitectureModel` | Parse a markdown requirements document into an ArchitectureM |

## Manifest (COMP-3)

**Contract:** Configuration loader for the Architecture Model Standard

### → Authoring (COMP-1)

**Symbols:** `ModuleStatus`, `FunctionInfo`, `ClassInfo`, `ImportDetail`, `DecoratedFunction`, `ModuleInfo`, `InterfaceEdge`, `SubFunctionEntry`, `BlockManifest`, `MetricsResult`

### → Pipeline (COMP-2)

**Symbols:** `load_config`, `discover_config`, `get_config`, `write_config`

| Function | Signature | Description |
|----------|-----------|-------------|
| `load_config` | `(root: Path) → ProjectConfig` | Load project configuration from .architecture-model.yaml.

A |
| `discover_config` | `(root: Path) → tuple[ProjectConfig, DiscoveryReport]` | Auto-discover project configuration by scanning filesystem.
 |
| `get_config` | `(root: Path) → ProjectConfig` | Load config from file if it exists, otherwise auto-discover. |
| `write_config` | `(config: ProjectConfig, root: Path | None) → Path` | Write a ProjectConfig to .architecture-model.yaml.

Args:
   |

### → Core (COMP-4)

**Symbols:** `is_excluded_dir`, `collect_py_files`, `discover_source_files`, `discover_test_files`

| Function | Signature | Description |
|----------|-----------|-------------|
| `is_excluded_dir` | `(path: Path) → bool` | Check if a directory path should be excluded from scanning. |
| `collect_py_files` | `(directory: Path, recursive: bool, exclude_init: bool) → list[Path]` | Collect Python files from a directory. |
| `discover_source_files` | `(project_root: Path) → list[Path]` | Discover all source (non-test) Python files in a project. |
| `discover_test_files` | `(project_root: Path) → list[Path]` | Discover all test Python files in a project. |

### → Extract (COMP-6)

**Symbols:** `load_config`, `discover_config`, `get_config`, `write_config`

| Function | Signature | Description |
|----------|-----------|-------------|
| `load_config` | `(root: Path) → ProjectConfig` | Load project configuration from .architecture-model.yaml.

A |
| `discover_config` | `(root: Path) → tuple[ProjectConfig, DiscoveryReport]` | Auto-discover project configuration by scanning filesystem.
 |
| `get_config` | `(root: Path) → ProjectConfig` | Load config from file if it exists, otherwise auto-discover. |
| `write_config` | `(config: ProjectConfig, root: Path | None) → Path` | Write a ProjectConfig to .architecture-model.yaml.

Args:
   |

## Core (COMP-4)

**Contract:** Module-level import-graph clustering

### → Authoring (COMP-1)

**Symbols:** `Status`, `RelationType`, `ActorType`, `InterfaceType`, `ConstraintType`, `Priority`, `Strength`, `ComponentKind`, `BehaviorPattern`, `SymbolKind`

### → Pipeline (COMP-2)

**Symbols:** `load_block_model`, `load_model`, `validate_model_data`, `dump_model`, `save_model`

| Function | Signature | Description |
|----------|-----------|-------------|
| `load_block_model` | `(project_root: str | Path, block_id: str, output_dir: str) → ArchitectureModel | None` | Load a block sub-model from the .architecture-models/ direct |
| `load_model` | `(path: str | Path) → ArchitectureModel` | Load and parse an architecture model YAML file. |
| `validate_model_data` | `(data: dict[str, Any]) → list[str]` | Validate raw dict against JSON Schema. Returns list of error |
| `dump_model` | `(model: ArchitectureModel) → dict[str, Any]` | Serialize ArchitectureModel back to a plain dict suitable fo |
| `save_model` | `(model: ArchitectureModel, path: str | Path) → None` | Serialize and write model to YAML file. |

### → Extract (COMP-6)

**Symbols:** `Status`, `RelationType`, `ActorType`, `InterfaceType`, `ConstraintType`, `Priority`, `Strength`, `ComponentKind`, `BehaviorPattern`, `SymbolKind`

### → Manifest (COMP-3)

**Symbols:** `Status`, `RelationType`, `ActorType`, `InterfaceType`, `ConstraintType`, `Priority`, `Strength`, `ComponentKind`, `BehaviorPattern`, `SymbolKind`

## Extract (COMP-6)

**Contract:** Parse project configuration files to derive technical and organizational constraints

### → Pipeline (COMP-2)

**Symbols:** `detect_routes`, `RouteInfo`

| Function | Signature | Description |
|----------|-----------|-------------|
| `detect_routes` | `(project_root: Path, web_layer_dirs: list[str] | None) → list[RouteInfo]` | Scan Python files for route handler declarations.

Args:
    |

## Schema (COMP-7)

**Contract:** Domain profile schema and loading logic

### → Core (COMP-4)

**Symbols:** `load_profile`, `EnumExtension`, `EntityExtension`, `ConditionalRule`, `DomainProfile`

| Function | Signature | Description |
|----------|-----------|-------------|
| `load_profile` | `(name_or_path: str) → DomainProfile` |  |
