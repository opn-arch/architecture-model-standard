# Component: Manifest (COMP-3)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/config/loader.py` | — | — |
| `src/architecture_model/config/schema.py` | — | — |
| `src/architecture_model/utils/discovery.py` | — | — |
| `src/architecture_model/manifest/behavior.py` | — | — |
| `src/architecture_model/manifest/blocks.py` | — | — |
| `src/architecture_model/manifest/body_hints.py` | — | — |
| `src/architecture_model/manifest/call_graph.py` | — | — |
| `src/architecture_model/manifest/chains.py` | — | — |
| `src/architecture_model/manifest/display.py` | — | — |
| `src/architecture_model/manifest/generator.py` | — | — |
| `src/architecture_model/manifest/grouping.py` | — | — |
| `src/architecture_model/manifest/interfaces.py` | — | — |
| `src/architecture_model/manifest/kt_scanner.py` | — | — |
| `src/architecture_model/manifest/metrics.py` | — | — |
| `src/architecture_model/manifest/multi_scanner.py` | — | — |
| `src/architecture_model/manifest/protocol.py` | — | — |
| `src/architecture_model/manifest/recursive.py` | — | — |
| `src/architecture_model/manifest/scan_cache.py` | — | — |
| `src/architecture_model/manifest/scanner.py` | — | — |
| `src/architecture_model/manifest/slicers.py` | — | — |
| `src/architecture_model/manifest/test_analyzer.py` | — | — |
| `src/architecture_model/manifest/ts_scanner.py` | — | — |
| `src/architecture_model/manifest/types.py` | — | — |

## Responsibilities

- resolve
- layer dir map
- source block dir map
- source block dict
- metrics paths
- resolved output
- from dict
- to dict
- add candidate
- claim rate
- summary
- export names
- from json
- from manifest
- to json
- get
- put
- hits
- misses
- to dict
- to dict
- to dict
- to dict
- to dict
- success rate
- log summary
- to dict
- to dict

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
| `load_config` | `root: Path` | `ProjectConfig` | Load project configuration from .architecture-model.yaml.

Args:
    root: Project root directory containing the config file.

Returns:
    ProjectConfig loaded from file.

Raises:
    FileNotFoundError: If config file doesn't exist. |
| `discover_config` | `root: Path` | `tuple[ProjectConfig, DiscoveryReport]` | Auto-discover project configuration by scanning filesystem.

Inspects the directory structure to infer layers, functional blocks,
and metrics without requiring a config file. Produces a complete,
usable configuration including auto-generated F-blocks.

Args:
    root: Project root directory to scan.

Returns:
    Tuple of (ProjectConfig with auto-discovered values, DiscoveryReport). |
| `get_config` | `root: Path` | `ProjectConfig` | Load config from file if it exists, otherwise auto-discover.

This is the recommended entry point — it always returns a valid config.
When loading from YAML, auto-discovers sub_blocks for any block that
doesn't already define them.

Args:
    root: Project root directory.

Returns:
    ProjectConfig (from file or auto-discovered). |
| `write_config` | `config: ProjectConfig, root: Path | None` | `Path` | Write a ProjectConfig to .architecture-model.yaml.

Args:
    config: The configuration to write.
    root: Directory to write to. Defaults to config.root.

Returns:
    Path to the written config file. |
| `resolve` | `project_name: str, root: Path` | `'ResolvedOutputConfig'` | Resolve path templates with actual project name. |
| `layer_dir_map` | `` | `dict[str, list[str]]` | Map layer IDs to their directories (for merger.py). |
| `source_block_dir_map` | `` | `dict[str, str]` | Map directory/file prefixes to F-block IDs (for merger.py heuristics).

Produces entries like: {"scripts/ingestion": "F1", "app/routers": "F4"} |
| `source_block_dict` | `` | `dict[str, dict[str, Any]]` | FUNCTIONAL_BLOCKS in the legacy dict format (backward compat). |
| `metrics_paths` | `` | `dict[str, Path]` | Map metric labels to their resolved paths. |
| `resolved_output` | `` | `ResolvedOutputConfig` | Get resolved output paths using project name and root. |
| `from_dict` | `data: dict[str, Any], root: Path` | `'ProjectConfig'` | Construct from parsed YAML dictionary. |
| `to_dict` | `` | `dict[str, Any]` | Serialize to YAML-compatible dictionary. |
| `add_candidate` | `category: str, path: str, accepted: bool, reason: str` | `None` |  |
| `claim_rate` | `` | `float` |  |
| `summary` | `` | `str` |  |
| `is_excluded_dir` | `path: Path` | `bool` | Check if a directory path should be excluded from scanning. |
| `collect_py_files` | `directory: Path, recursive: bool, exclude_init: bool` | `list[Path]` | Collect Python files from a directory. |
| `discover_source_files` | `project_root: Path` | `list[Path]` | Discover all source (non-test) Python files in a project. |
| `discover_test_files` | `project_root: Path` | `list[Path]` | Discover all test Python files in a project. |
| `extract_call_order` | `func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]` | `list[str]` | Extract ordered call sequence from function body.

Walks body in execution order (top-to-bottom, depth-first into expressions).
For nested calls like save(transform(x)), yields innermost first (evaluation order). |
| `extract_control_flow` | `func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]` | `list[str]` | Detect structural control flow patterns in a function.

Returns deduplicated list of pattern names found. |
| `extract_guards` | `func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]` | `list[str]` | Extract precondition guards from the first 6 statements of a function body.

Guards are: assert statements, raise-if patterns, early return-if patterns. |
| `process_block` | `root: Path, block_id: str, block_def: dict, sub_block_configs: list | None` | `BlockManifest` | Process a single functional block, scanning all its files.

Returns a typed :class:`BlockManifest` with :class:`SubFunctionEntry` objects. |
| `classify_function` | `source: str, func_name: str` | `BodyComplexity` | Classify a function's body complexity.

Parses source, finds function by name, counts body statements
(excluding leading docstring). 1=TRIVIAL, 2-5=SHORT, 6+=COMPLEX. |
| `extract_body_hint` | `source: str, func_name: str, class_name: str | None` | `str` | Produce a tiered body hint for a function.

- Trivial: exact single statement text
- Short: semicolon-joined statements
- Complex: structural summary |
| `extract_file_hints` | `filepath: Path, include_private: bool` | `list[FunctionSignature]` | Scan an entire file and produce FunctionSignature objects with body hints.

Excludes private functions (starting with '_') EXCEPT '__init__'.
Includes class methods. When include_private=True, includes all functions. |
| `build_call_graph` | `manifest: Manifest` | `CallGraph` | Build a resolved call graph from manifest data. |
| `trace_flow` | `graph: CallGraph, entry: str, max_depth: int` | `FlowTrace` | BFS from entry point, following call edges. |
| `map_flow_to_components` | `flow: FlowTrace, file_to_comp: dict[str, str]` | `FlowTrace` | Populate components_crossed on a FlowTrace. |
| `build_block_chains` | `block_manifest: 'Manifest', groups: list['ModuleGroup'], block_id: str` | `list[EventChain]` | Build intra-block event chains (all within one F-block).

Traces call_order across component group boundaries within the block.
Only returns chains that span 2+ components (single-component calls
are not interesting for architecture). |
| `build_cross_block_chains` | `recursive_manifests: dict[str, 'RecursiveManifest'], block_groups: dict[str, list['ModuleGroup']]` | `list[EventChain]` | Build cross-block event chains (spanning 2+ F-blocks).

Uses block_dependencies to identify cross-boundary call paths.
A cross-block chain occurs when a function's call_order references
a function that lives in a different block. |
| `print_summary` | `manifest: dict[str, Any]` | `None` | Print a terminal summary of the manifest. |
| `generate_manifest` | `project_root: Path, config: Optional[Any]` | `Manifest` | Generate a full reality manifest via AST scan of the project.

Args:
    project_root: Absolute path to the project root directory.
    config: Optional ProjectConfig. If None, loaded from .architecture-model.yaml.

Returns:
    Typed Manifest dataclass. Call .to_dict() for JSON-compatible dict. |
| `load_or_generate_manifest` | `project_root: Path, output_dir: Path | None` | `dict[str, Any]` | Load cached manifest if fresh (< 1 hour old), otherwise regenerate.

Args:
    project_root: Path to the project root.
    output_dir: Optional output directory. If None, uses config output paths.

Returns:
    The manifest dictionary (for backward compatibility with CLI/callers). |
| `group_modules` | `modules: list[ModuleInfo], interfaces: list[InterfaceEdge], target_groups: int | None, min_group_size: int` | `list[ModuleGroup]` | Group modules into logical components using multi-signal affinity.

Args:
    modules: List of modules to group.
    interfaces: Import edges between modules.
    target_groups: Desired number of groups. None = auto-calculate.
    min_group_size: Minimum modules per group (after merging).

Returns:
    List of ModuleGroup objects. |
| `create_components_from_manifest` | `manifest: Manifest, block_id: str, target_groups: int | None` | `list[Component]` | Create architecture components from a manifest using smart grouping.

Groups modules using multi-signal affinity, then creates one Component
per group with appropriate metadata.

Args:
    manifest: The manifest to create components from.
    block_id: S-block ID to assign to all components.
    target_groups: Desired number of components (None = auto).

Returns:
    List of Component objects. |
| `auto_source_blocks` | `groups: list[ModuleGroup], threshold: int` | `dict` | Generate S-block config from flat module groups.

Groups with >= threshold files become individual S-blocks.
Smaller groups are merged into a 'Shared' S-block.

Args:
    groups: Module groups from group_modules()
    threshold: Minimum files to become a standalone S-block (default: 3)

Returns:
    Dict of S-block definitions suitable for config:
    {
        "S1": {"name": "Auth", "dirs": ["src/auth"], "files": ["auth/login.py", ...]},
        "S2": {"name": "API", "dirs": ["src/api"], "files": [...]},
        "S0": {"name": "Shared", "dirs": [], "files": [...]},  # small groups merged
    } |
| `group_source_graph` | `graph: SourceGraph, target_groups: int | None, min_group_size: int` | `list[ModuleGroup]` | Group source units using multi-signal affinity (language-agnostic).

This is the SourceGraph equivalent of group_modules(). It converts
SourceUnits into lightweight ModuleInfo-compatible objects and delegates
to the existing grouping algorithm.

Args:
    graph: A SourceGraph instance (from any language scanner or JSON).
    target_groups: Desired number of groups. None = auto-calculate.
    min_group_size: Minimum modules per group (after merging).

Returns:
    List of ModuleGroup objects. |
| `derive_interfaces` | `modules: list[ModuleInfo], root: Path` | `list[InterfaceEdge]` | Derive interfaces from import analysis between scanned modules.

Uses both simple imports and imports_detailed (with relative import
resolution) to find inter-module dependencies within the project.

Args:
    modules: Typed module info objects from AST scanning.
    root: Project root path.

Returns:
    List of InterfaceEdge objects representing inter-module dependencies. |
| `scan_kotlin` | `root: Path` | `SourceGraph` | Scan Kotlin files under root, produce SourceGraph.

Extracts:
- Class/data class/object declarations (public only)
- Top-level functions (public only, skips internal/private)
- Public methods inside classes
- Import statements → dependency edges
- Package declarations → for import resolution |
| `scan_java` | `root: Path` | `SourceGraph` | Scan Java files under root, produce SourceGraph.

Extracts public classes and their public methods. |
| `compute_metrics` | `root: Path, config: Optional[Any]` | `MetricsResult` | Compute verified project metrics from filesystem.

Args:
    root: Project root directory.
    config: Optional ProjectConfig. If None, loaded from .architecture-model.yaml.

Returns:
    MetricsResult with metric values. |
| `scan_all_languages` | `root: Path` | `SourceGraph` | Scan repository for all supported languages, return merged SourceGraph.

Language detection by file extension:
- .py  → Python (via generate_manifest → SourceGraph.from_manifest)
- .kt  → Kotlin (via scan_kotlin, tree-sitter)
- .java → Java (via scan_java, tree-sitter)
- .ts/.tsx/.js/.jsx → TypeScript (via regex fallback)

Cross-language edges are NOT detected (would require API contract analysis). |
| `export_names` | `` | `list[str]` |  |
| `from_json` | `data: dict[str, Any]` | `SourceGraph` | Parse from JSON (agent or tool output).

Accepts two JSON formats:
- Canonical: {"units": [...], "edges": [...]}
- Shorthand: {"files": [...], "dependencies": [...]}

Each file/unit can have exports as strings or dicts:
- String: just the name (assumes function)
- Dict: {"name": "x", "kind": "class", "signature": "..."} |
| `from_manifest` | `manifest: 'Manifest'` | `SourceGraph` | Convert a Python Manifest to a SourceGraph.

This is the bridge between the existing Python AST scanner
and the language-agnostic protocol. |
| `to_json` | `` | `dict[str, Any]` | Serialize to JSON for persistence or transport. |
| `generate_block_manifest` | `root: Path, block_id: str, block_def: dict[str, Any]` | `Manifest` | Generate a full Manifest scoped to a single F-block's files. |
| `generate_recursive_manifests` | `project_root: Path, parent_model: str, source_block_override: dict[str, dict] | None` | `dict[str, RecursiveManifest]` | Generate a RecursiveManifest for each F-block in the project config.

Args:
    project_root: Repository root path.
    parent_model: Config/model filename to read F-blocks from.
    source_block_override: If provided, use these F-block definitions instead of
        reading from config. Dict mapping block_id -> {name, dirs, files}. |
| `compute_block_dependencies` | `manifests: dict[str, RecursiveManifest], config` | `dict[str, list[str]]` | Compute cross-block dependency graph from import analysis.

For each block, examines all imports in its modules. If an import resolves
to a file belonging to a different block, that's a cross-block dependency.

Returns:
    Dict mapping block_id -> list of block_ids it depends on. |
| `write_recursive_manifests` | `manifests: dict[str, RecursiveManifest], output_dir: Path` | `list[Path]` | Write each RecursiveManifest to its own JSON file. |
| `get` | `filepath: Path` | `ModuleInfo | None` | Get cached scan result for a file. |
| `put` | `filepath: Path, module: ModuleInfo` | `None` | Cache a scan result. |
| `hits` | `` | `int` |  |
| `misses` | `` | `int` |  |
| `scan_file` | `root: Path, filepath: Path, cache` | `ModuleInfo` | Scan a single Python file and return typed metadata.

Args:
    root: Project root directory.
    filepath: Absolute path to the Python file.
    cache: Optional ScanCache for pipeline-scoped deduplication.

Returns:
    ModuleInfo with all extracted metadata. |
| `get_manifest_slice` | `manifest: Manifest | dict[str, Any], artifact_name: str` | `str` | Return focused markdown slice for artifact context injection.

Args:
    manifest: A typed Manifest or legacy raw dict.
    artifact_name: One of the 10 artifact names.

Returns:
    Formatted markdown string with relevant manifest data. |
| `analyze_test_file` | `test_file: Path` | `TestAnalysisResult` | Parse a test file and extract behavioral contracts.

Handles both unittest (assertEqual, assertTrue, assertRaises)
and pytest (assert ==, assert isinstance, pytest.raises) patterns. |
| `extract_constants_from_contracts` | `contracts: list[TestContract]` | `list[Constant]` | Derive constants from value_equality contracts.

e.g., assertion "Fore.BLACK == '\033[30m'" →
Constant(name="BLACK", value="30", context="attribute of Fore, produces escape code \033[30m") |
| `scan_typescript_fallback` | `root: Path` | `dict[str, Any]` | Scan a TS/JS project using regex patterns.
Returns a SourceGraph-compatible dict. |
| `to_dict` | `` | `dict[str, Any]` | Convert to legacy dict format for backward compatibility. |
| `to_dict` | `` | `dict[str, str]` |  |
| `to_dict` | `` | `dict[str, Any]` |  |
| `to_dict` | `` | `dict[str, Any]` |  |
| `to_dict` | `` | `dict[str, int]` |  |
| `success_rate` | `` | `float` |  |
| `log_summary` | `` | `None` |  |
| `to_dict` | `` | `dict[str, Any]` | Convert to legacy dict format for JSON serialization. |
| `to_dict` | `` | `dict[str, Any]` |  |

## Interface Dependencies

- **provides** `exposes_to_Authoring` → COMP-1 (Authoring) [ModuleStatus, FunctionInfo, ClassInfo, ImportDetail, DecoratedFunction, ModuleInfo, InterfaceEdge, SubFunctionEntry, BlockManifest, MetricsResult]
- **provides** `exposes_to_Pipeline` → COMP-2 (Pipeline) [load_config, discover_config, get_config, write_config]
- **provides** `exposes_to_Core` → COMP-4 (Core) [is_excluded_dir, collect_py_files, discover_source_files, discover_test_files]
- **provides** `exposes_to_Extract` → COMP-6 (Extract) [load_config, discover_config, get_config, write_config]
- **requires** `uses_Core` → COMP-4 (Core) [Status, RelationType, ActorType, InterfaceType, ConstraintType, Priority, Strength, ComponentKind, BehaviorPattern, SymbolKind]

## Patterns

- serializer

## Confidence

100%
