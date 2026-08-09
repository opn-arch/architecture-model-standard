# Component: Core (COMP-1)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/architecture_model/authoring/gate.py` | — | — |
| `src/architecture_model/authoring/parser.py` | — | — |
| `src/architecture_model/cli/main.py` | — | — |
| `src/architecture_model/core/cluster.py` | — | — |
| `src/architecture_model/core/compression.py` | — | — |
| `src/architecture_model/core/confidence.py` | — | — |
| `src/architecture_model/core/corrections.py` | — | — |
| `src/architecture_model/core/coverage.py` | — | — |
| `src/architecture_model/core/decomposer.py` | — | — |
| `src/architecture_model/core/differ.py` | — | — |
| `src/architecture_model/core/merger.py` | — | — |
| `src/architecture_model/core/parser.py` | — | — |
| `src/architecture_model/core/representativeness.py` | — | — |
| `src/architecture_model/core/slicer.py` | — | — |
| `src/architecture_model/core/source_block_assign.py` | — | — |
| `src/architecture_model/core/source_block_quality.py` | — | — |
| `src/architecture_model/core/test_affinity.py` | — | — |
| `src/architecture_model/core/types.py` | — | — |
| `src/architecture_model/core/validator.py` | — | — |
| `src/architecture_model/core/visualize.py` | — | — |
| `src/architecture_model/orchestration/auto_enrich.py` | — | — |
| `src/architecture_model/orchestration/behavior_decompose.py` | — | — |
| `src/architecture_model/orchestration/behavior_flows.py` | — | — |
| `src/architecture_model/orchestration/capability_inference.py` | — | — |
| `src/architecture_model/orchestration/compaction.py` | — | — |
| `src/architecture_model/orchestration/decompose.py` | — | — |
| `src/architecture_model/orchestration/deep_decompose.py` | — | — |
| `src/architecture_model/orchestration/enrich.py` | — | — |
| `src/architecture_model/orchestration/enrichment_context.py` | — | — |
| `src/architecture_model/orchestration/full_extraction.py` | — | — |
| `src/architecture_model/orchestration/naming_context.py` | — | — |
| `src/architecture_model/orchestration/pipeline.py` | — | — |
| `src/architecture_model/orchestration/trigger_detection.py` | — | — |
| `src/architecture_model/orchestration/use_case_inference.py` | — | — |

## Responsibilities

- summary
- has changes
- added count
- removed count
- modified count
- summary
- format report
- affected artifacts
- model
- entities
- relationships
- meta
- to dict
- to dict
- parse
- parse
- parse
- parse
- parse
- parse
- parse
- parse
- parse
- parse
- parse
- all entity ids
- entity count
- relationship count
- to dict
- to yaml
- error count
- warning count
- info count
- is valid
- score
- summary

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
| `main` | `argv: list[str] | None` | `int` |  |
| `cluster_modules` | `modules: list[str], edges: list[tuple[str, str]], target_k: int, min_cluster_size: int` | `list[list[str]]` | Cluster modules into groups by import-graph affinity.

Args:
    modules: List of module file paths.
    edges: List of (source, target) import edges.
    target_k: Target number of clusters.
    min_cluster_size: Merge clusters smaller than this.

Returns:
    List of module groups (each group is a list of file paths). |
| `compute_compression_stats` | `root: Path` | `dict` | Compute compression ratio between source code and model representation. |
| `format_compression_summary` | `stats: dict` | `str` | Format stats as human-readable summary string. |
| `compute_component_confidence` | `comp: Component` | `float` | Compute confidence for a Component. Returns 0.0-1.0. |
| `compute_behavior_confidence` | `behavior: Behavior` | `float` | Compute confidence for a Behavior. Returns 0.0-1.0. |
| `compute_capability_confidence` | `capability: Capability, realized: bool` | `float` | Compute confidence for a Capability. Returns 0.0-1.0. |
| `compute_interface_confidence` | `interface: Interface` | `float` | Compute confidence for an Interface. Returns 0.0-1.0. |
| `compute_model_confidence` | `model: ArchitectureModel` | `ArchitectureModel` | Compute and set confidence on all entities in the model. |
| `aggregate_block_confidence` | `model: ArchitectureModel` | `dict[str, dict]` | Aggregate confidence scores per F-block. |
| `model_confidence_summary` | `model: ArchitectureModel` | `dict` | Generate overall confidence summary for the model. |
| `compute_function_confidence` | `func_info` | `float` | Compute confidence for a function from manifest FunctionInfo.

Factors:
- Has typed signature (params with types, return type): 30%
- Has docstring: 25%
- Has call graph (calls list): 20%
- Has raises info: 15%
- Has parameters at all: 10% |
| `load_corrections` | `repo_path: Path` | `list[dict]` | Load corrections from .architecture/corrections.yaml. Returns [] if missing. |
| `store_correction` | `repo_path: Path, correction: dict` | `dict` | Append a correction with auto-generated id, created_at, and applied=false. |
| `apply_corrections` | `model: Any, corrections: list[dict]` | `tuple[Any, list[str]]` | Apply unapplied rename and add_relationship corrections to a model. |
| `mark_applied` | `repo_path: Path, correction_ids: list[str]` | `None` | Mark specified corrections as applied=true in the YAML file. |
| `coverage_report` | `model: 'ArchitectureModel', manifest: dict, import_deps: dict[str, set[str]] | None` | `CoverageResult` | Run all coverage checks and return aggregate result. |
| `summary` | `` | `str` |  |
| `compute_complexity` | `comp: Component, model: ArchitectureModel` | `float` | Weighted complexity score for determining if a component should be in a System.

Factors:
    - Number of symbols x 2.0
    - Total members (sum of all symbol members) x 0.3
    - Number of functions x 0.5
    - Number of depends-on relationships (inbound + outbound) x 1.5 |
| `identify_systems` | `model: ArchitectureModel, manifest: dict` | `list[SystemCandidate]` | Identify F-block groups that should become Systems.

Groups components by source_block, computes aggregate complexity per group,
and returns SystemCandidates for groups exceeding SYSTEM_THRESHOLD.

For components without an source_block field, they are skipped (remain as
top-level components).

Args:
    model: The architecture model with enriched components.
    manifest: Manifest dict containing functional_blocks metadata.

Returns:
    List of SystemCandidate for groups exceeding threshold. |
| `decompose_model` | `model: ArchitectureModel, manifest: dict, output_dir: str` | `DecompositionResult` | Decompose a flat model into top-level + system sub-models.

1. Identifies system candidates via F-block complexity
2. For each system:
   - Creates System entity with sub_model_ref
   - Extracts system's components into a sub-model
   - Partitions relationships: intra-system stay in sub-model,
     inter-system get promoted to top-level (from/to rewritten to system ID)
3. Remaining components stay in top-level

Args:
    model: Flat architecture model (v1.2+ with enriched components).
    manifest: Manifest dict with functional_blocks metadata.
    output_dir: Directory name for sub-model refs (default "systems").

Returns:
    DecompositionResult with top-level model and sub-models dict. |
| `detect_systems` | `model: ArchitectureModel, manifest, target_systems: int` | `list[SystemScore]` | Multi-signal system boundary detection.

Uses import coupling, data affinity, directory cohesion, and API surface
signals to identify bounded-context boundaries.

Args:
    model: Architecture model with components having source_files.
    manifest: Manifest with modules (ModuleInfo instances).
    target_systems: Desired number of systems (0 = auto-calculate).

Returns:
    List of SystemScore representing detected system boundaries. |
| `diff_models` | `old_model: ArchitectureModel, new_model: ArchitectureModel` | `ModelDiff` | Compare two model versions and produce a structured diff.

Args:
    old_model: The previous/baseline model.
    new_model: The current/updated model.

Returns:
    ModelDiff with all detected changes. |
| `has_changes` | `` | `bool` |  |
| `added_count` | `` | `int` |  |
| `removed_count` | `` | `int` |  |
| `modified_count` | `` | `int` |  |
| `summary` | `` | `str` |  |
| `format_report` | `` | `str` | Format a human-readable diff report. |
| `affected_artifacts` | `` | `set[str]` | Determine which artifacts might be stale based on changes.

Returns set of artifact names that should be regenerated. |
| `merge_manifest` | `model: ArchitectureModel, manifest_path: str | Path, project_root: str | Path | None` | `ArchitectureModel` | Merge manifest data into the architecture model (in-place mutation).

What gets merged:
- Component file lists get enriched with manifest-discovered files.
- Layers get directory lists from manifest module scan.
- Meta gets manifest_hash updated.

What does NOT get overwritten:
- Entity names, descriptions, status markers.
- Relationships (these are architectural decisions).
- Capabilities, behaviors, constraints (model-level truth).

Args:
    model: The architecture model to enrich.
    manifest_path: Path to the reality-manifest.json file.
    project_root: Root of the consumer project (for config lookup).
                  Defaults to manifest_path's grandparent (output/{project}/manifest → root).

Returns the same model instance (mutated). |
| `enrich_from_manifest` | `model: ArchitectureModel, manifest: dict` | `EnrichmentResult` | Enrich an ArchitectureModel with ground-truth symbols and functions from an AST manifest.

Replaces component symbols/functions with manifest-derived data, enriches
relationship imports, and computes naming accuracy vs prior predictions.

Args:
    model: The architecture model to enrich (mutated in-place).
    manifest: Manifest dict as produced by the manifest generator.

Returns:
    EnrichmentResult with the enriched model and naming_accuracy score. |
| `compact_for_generation` | `model: ArchitectureModel` | `ArchitectureModel` | Compact an enriched model for LLM code generation.

Truncates symbol members and component functions when the model is too
large for a 7B model's effective context. Preserves structure (all
components, all symbol names by kind) but limits detail per entity.

The model is mutated in-place and returned.

Strategy:
- Cap symbols per component to _MAX_SYMBOLS_PER_COMPONENT (keep by importance)
- Cap members per symbol to _MAX_MEMBERS_PER_SYMBOL (keep __init__ + public)
- Cap functions per component to _MAX_FUNCTIONS_PER_COMPONENT
- Prioritize: __init__ first, then alphabetical for determinism
- Excess symbols are listed as names-only in a comment field
- For very large models (>16 components), apply stricter per-component limits |
| `compose_enriched_model` | `project_root: Path` | `ArchitectureModel` | Compose a fully-enriched ArchitectureModel from source code.

Scans all source files in the project, extracting:
- Module constants, class attributes, module assignments → Constant objects
- Function signatures with body hints → FunctionSignature objects
- Test contracts from matching test files → TestContract objects

Each source module becomes a Component in the resulting model.

Args:
    project_root: Root directory of the project to scan.

Returns:
    An ArchitectureModel with one Component per source file, enriched
    with constants, signatures, and test contracts. |
| `model` | `` | `ArchitectureModel` |  |
| `entities` | `` | `` |  |
| `relationships` | `` | `` |  |
| `meta` | `` | `` |  |
| `load_block_model` | `project_root: str | Path, block_id: str, output_dir: str` | `ArchitectureModel | None` | Load a block sub-model from the .architecture-models/ directory.
Returns None if the sub-model doesn't exist. |
| `load_model` | `path: str | Path` | `ArchitectureModel` | Load and parse an architecture model YAML file. |
| `validate_model_data` | `data: dict[str, Any]` | `list[str]` | Validate raw dict against JSON Schema. Returns list of error messages. |
| `dump_model` | `model: ArchitectureModel` | `dict[str, Any]` | Serialize ArchitectureModel back to a plain dict suitable for YAML output. |
| `save_model` | `model: ArchitectureModel, path: str | Path` | `None` | Serialize and write model to YAML file. |
| `compute_representativeness` | `model: ArchitectureModel, modules: list[ModuleInfo], interfaces: list[InterfaceEdge]` | `RepresentativenessResult` |  |
| `compute_hierarchical_representativeness` | `root_model: ArchitectureModel, sub_models: dict[str, ArchitectureModel], recursive_manifests: dict[str, 'RecursiveManifest']` | `HierarchicalRepresentativenessResult` | Verify representativeness at every level of decomposition.

Root level: checks that all blocks are represented and cross-block relationships
match real import dependencies.

Block level: standard file_coverage + relationship_accuracy + boundary_coherence
within each block's scope. |
| `to_dict` | `` | `dict` |  |
| `to_dict` | `` | `dict` |  |
| `slice_by_source_block` | `model: ArchitectureModel, source_block: str, include_relationships: bool, project_root: Union[Path, str, None]` | `ArchitectureModel` | Extract all entities and relationships related to a specific F-block.

Args:
    model: Full architecture model.
    source_block: F-block identifier (e.g., "S1", "S2").
    include_relationships: Whether to include relationships between sliced entities.

Returns:
    New ArchitectureModel containing only the F-block's entities. |
| `slice_by_layer` | `model: ArchitectureModel, layer_id: str` | `ArchitectureModel` | Extract all entities allocated to a specific layer.

Args:
    model: Full architecture model.
    layer_id: Layer identifier (e.g., "web-layer", "pipeline-layer").

Returns:
    New ArchitectureModel with layer-specific entities. |
| `slice_by_status` | `model: ArchitectureModel, status: Status` | `ArchitectureModel` | Filter model to only include entities with a specific status.

Args:
    model: Full architecture model.
    status: Status to filter by.

Returns:
    New ArchitectureModel with only matching entities. |
| `slice_for_artifact` | `model: ArchitectureModel, artifact_name: str` | `ArchitectureModel` | Extract the model subset relevant to a specific artifact's regeneration.

Artifact-specific slicing rules:
- functional-architecture: capabilities, behaviors (summary), relationships
- logical-architecture: layers, components, inter-layer relationships
- use-cases: actors, behaviors (full), capabilities (summary)
- icd: interfaces, components (providers/consumers)
- requirements-analysis: constraints, capabilities, behaviors (summary)
- readme: everything (summary level)

Args:
    model: Full architecture model.
    artifact_name: Name of the artifact to slice for.

Returns:
    Model subset appropriate for the artifact. |
| `auto_assign_source_blocks` | `model: ArchitectureModel, max_cluster_size: int` | `ArchitectureModel` | Assign source_block values to components via dependency-graph clustering.

Used when the model has no source_block annotations (e.g., oracle-extracted models).
Groups components by import/dependency density using greedy modularity:
1. Build undirected adjacency from depends_on relationships
2. Seed clusters from highest-degree nodes
3. Grow each cluster by adding adjacent unassigned nodes (max size limit)
4. Singletons keep their own source_block (decomposer threshold handles them)

Mutates nothing — returns a new model with source_block assigned on components. |
| `compute_modularity` | `model: 'ArchitectureModel'` | `float` | Compute Newman's modularity Q over depends-on edges.

Q = (1/2m) * sum_ij (A_ij - k_i*k_j / 2m) * delta(c_i, c_j)

Uses undirected interpretation of depends-on edges. |
| `compute_conductance` | `model: 'ArchitectureModel'` | `dict[str, float]` | Compute conductance per F-block.

conductance = edges_out / (edges_out + edges_in)
where edges_in = edges with both endpoints in the block,
edges_out = edges with exactly one endpoint in the block. |
| `compute_agreement_rate` | `model: 'ArchitectureModel'` | `float` | Compare existing source_block assignments with auto_assign_source_blocks output.

Returns fraction of components where assignments agree. |
| `compute_source_block_quality` | `model: 'ArchitectureModel'` | `FBlockQuality` | Compute all F-block quality metrics. |
| `compute_provenance` | `model: 'ArchitectureModel', quality: FBlockQuality` | `dict[str, FBlockProvenance]` | Compute per-component provenance and attach to component.extensions. |
| `test_affinity_decompose` | `repo_path: Path` | `list[Subsystem]` | Decompose a repository into subsystems based on test file affinity.

Algorithm:
1. Discover all test files (*_test.py, test_*.py)
2. Discover all source files (non-test .py files)
3. For each test file, AST-parse its imports to identify which source modules it tests
4. Group source modules by their primary test file (each source → exactly one subsystem)
5. Determine dependencies between subsystems via import analysis
6. Return subsystems sorted topologically (leaves first)

Source modules with no test → assigned to 'root' subsystem |
| `parse` | `value: str` | `RelationType | str` | Parse a relation type, accepting unknown values as plain strings. |
| `parse` | `value: str` | `ActorType | str` | Parse an actor type, accepting unknown values as plain strings. |
| `parse` | `value: str` | `InterfaceType | str` | Parse an interface type, accepting unknown values as plain strings. |
| `parse` | `value: str` | `ConstraintType | str` | Parse a constraint type, accepting unknown values as plain strings. |
| `parse` | `value: str` | `ComponentKind | str` | Parse a component kind, accepting unknown values as plain strings. |
| `parse` | `value: str` | `BehaviorPattern | str` | Parse a behavior pattern, accepting unknown values as plain strings. |
| `parse` | `value: str` | `EventKind | str` |  |
| `parse` | `value: str` | `ResourceKind | str` |  |
| `parse` | `value: str` | `EnvironmentKind | str` |  |
| `parse` | `value: str` | `DecisionStatus | str` |  |
| `parse` | `value: str` | `LifecyclePhase | str` |  |
| `all_entity_ids` | `` | `set[str]` | Return set of all entity IDs across all types. |
| `entity_count` | `` | `int` |  |
| `relationship_count` | `` | `int` |  |
| `to_dict` | `` | `dict[str, Any]` | Serialize the model to a plain dict suitable for YAML output.

Produces output compatible with _parse_raw() for round-trip fidelity.
Enum values are serialized as their string values. Empty optional fields
are omitted for cleanliness. |
| `to_yaml` | `` | `str` | Serialize the model to a YAML string. |
| `validate_model` | `model: ArchitectureModel, strict: bool` | `ValidationResult` | Run all validation checks on the architecture model.

Args:
    model: The model to validate.
    strict: If True, promote warnings to errors.

Returns:
    ValidationResult with all issues found. |
| `error_count` | `` | `int` |  |
| `warning_count` | `` | `int` |  |
| `info_count` | `` | `int` |  |
| `is_valid` | `` | `bool` | Model is valid if there are no errors (warnings are acceptable). |
| `score` | `` | `int` | Score 0-100. Deduct 10 per error, 2 per warning. |
| `summary` | `` | `str` |  |
| `generate_context_diagram` | `model: 'ArchitectureModel'` | `str` | C4-style context: actors interacting with system via interfaces.

Shows: actors (person/system shapes), interfaces inside system boundary,
consumes/exposes edges. |
| `generate_components_diagram` | `model: 'ArchitectureModel'` | `str` | Components grouped by layer, with realizes edges to capabilities.

Shows: layers as subgraphs, components inside, realizes edges to capability nodes. |
| `generate_behaviors_diagram` | `model: 'ArchitectureModel'` | `str` | Behavior flow: triggers/contains relationships between behaviors.

Shows: behaviors as stadium-shaped nodes, triggers/contains edges,
traces-to from components. |
| `generate_dependencies_diagram` | `model: 'ArchitectureModel'` | `str` | Inter-component dependency graph grouped by source_block.

Shows: components grouped by source_block in subgraphs, depends-on edges. |
| `generate_all_diagrams` | `model: 'ArchitectureModel', output_dir: Path` | `dict[str, Path]` | Generate all 4 standard diagrams and write to output_dir.

Returns dict mapping diagram name to file path. |
| `enrich_from_manifest` | `model: Any, manifest: Manifest` | `None` | Enrich model components in-place from manifest data.

Populates signatures, symbols, constants, contract, pattern, and
responsibilities for each component by matching files to manifest modules. |
| `enrich_behaviors_from_manifest` | `model: Any, manifest: Manifest` | `None` | Enrich model behaviors in-place from manifest data.

Populates trigger, steps, and postconditions for each behavior by matching
source_file to manifest modules and using the behavior name as entry point. |
| `enrich_with_block_context` | `model: Any, recursive_manifests: dict` | `None` | Second-pass enrichment using block-level context.

Uses recursive manifests to:
1. Classify patterns at block level (more indicators available)
2. Propagate block pattern to unclassified components
3. Infer contracts from block name when module docstring is absent |
| `manifest_to_source_graph` | `manifest: Any, model: Any` | `'SourceGraph'` | Convert a Manifest's import data into a SourceGraph for interface extraction.

Resolves module-name imports (e.g. 'src.b.core') to file paths by matching
against manifest modules, then creates DependencyEdge objects. |
| `extract_component_interfaces` | `model: Any, graph: 'SourceGraph'` | `int` | Extract interface contracts between components from cross-boundary edges.

For each dependency edge that crosses a component boundary:
- The source component gets a 'requires' interface
- The target component gets a 'provides' interface

Args:
    model: ArchitectureModel with entities.components
    graph: SourceGraph with edges (dependency info)

Returns:
    Number of interfaces added. |
| `enrich_from_source_graph` | `model: Any, graph: 'SourceGraph'` | `None` | Enrich model components from SourceGraph export data (language-agnostic).

Populates signatures, symbols, contracts, patterns, and responsibilities
from ExportedSymbol data. Enables non-Python repos to reach higher confidence. |
| `create_behaviors_from_manifest` | `model: Any, manifest: Manifest` | `tuple[list[Behavior], list[Relationship]]` | Auto-create granular behaviors from manifest, one per significant function.

Scans all modules in the manifest, creates a Behavior for each function
in router and service modules. Links behaviors to components via relationships.

Args:
    model: ArchitectureModel with entities.components populated.
    manifest: Manifest with modules and interfaces.

Returns:
    Tuple of (behaviors created, relationships linking components to behaviors). |
| `decompose_behavior` | `behavior: Behavior, model: ArchitectureModel, manifest` | `Behavior` | Promote behavior's raw steps to structured Steps.

For each raw step (a function/method name):
1. Find which component contains a function with that name
2. Use the function name as the action (titlecase, underscores to spaces)
3. Set component_ref to the owning component's ID

If manifest is provided, also look up function signatures for richer descriptions.

Returns a NEW Behavior with structured_steps populated. |
| `decompose_all_behaviors` | `model: ArchitectureModel, manifest` | `ArchitectureModel` | Decompose all behaviors in a model. |
| `classify_behaviors` | `behaviors: list[Behavior], relationships: list[Relationship], call_graph: CallGraph, file_to_comp: dict[str, str]` | `BehaviorClassification` | Classify behaviors into cross-component, single-component CRUD, and trivial. |
| `summarize_crud_group` | `component_id: str, behaviors: list[Behavior]` | `CrudSummary` | Summarize a group of CRUD behaviors for one component. |
| `build_behavior_manifest` | `behavior: Behavior, flow_trace: FlowTrace, manifest: Manifest` | `Manifest` | Build a scoped manifest containing only modules touched by the flow. |
| `build_behavior_sub_model` | `behavior: Behavior, flow_trace: FlowTrace, model: ArchitectureModel, file_to_comp: dict[str, str]` | `ArchitectureModel` | Build a sub-model for a specific behavior flow. |
| `build_file_to_comp` | `model: ArchitectureModel, manifest: Manifest` | `dict[str, str]` | Build file->component mapping from model + manifest. |
| `infer_capabilities` | `model: ArchitectureModel` | `ArchitectureModel` | Infer capabilities from behaviors, add to model with realizes relationships.

Clustering (priority order):
1. URL prefix from trigger (/users/*, /orders/*)
2. Actor (same actor -> same capability)
3. Ungrouped -> "Internal Operations"

Preserves existing capabilities. Returns new model with additions. |
| `build_capability_hierarchy` | `model: ArchitectureModel` | `ArchitectureModel` | Add contains relationships between capabilities based on URL path depth.

If capability A's behaviors use prefix /X and capability B's behaviors
use prefix /X/Y, then A contains B. |
| `compact_for_storage` | `model: ArchitectureModel` | `tuple[ArchitectureModel, dict[str, list[Behavior]]]` | Compact a model by offloading leaf behaviors to per-component groups. |
| `decompose_model` | `project_root, model_path` | `` | Generate sub-models for each F-block by tracing parent model relationships.

For each F-block:
1. Find components by file path matching
2. Trace realizes/exposes/traces-to/constrained-by to find connected entities
3. Collect internal + boundary relationships
4. Build sub-model with parent's actual entities (not invented ones)

Args:
    project_root: Root directory with .architecture-model.yaml
    model_path: Optional path to model file (default: project_root/.architecture-model.yaml)

Returns:
    Dict mapping block_id -> ArchitectureModel (sub-model) |
| `compact_root_model` | `model, block_ids: list[str]` | `None` | Strip implementation detail from components in-place, keeping identity.

After decomposition, the root model no longer needs heavy detail on
components that have been decomposed into sub-models.  This function
zeroes out implementation-level fields while preserving identity and
architectural contract fields. |
| `write_sub_models` | `sub_models, output_dir` | `` | Write sub-models to YAML files.

Output structure:
    output_dir/<block_id>/.architecture-model.yaml |
| `deep_decompose_block` | `manifest: Manifest, block_id: str, block_name: str, max_modules: int, target_k: int, min_cluster_size: int, parent_id: str` | `DecomposeResult` | Decompose a block manifest into sub-components via import clustering.

Args:
    manifest: Block manifest with modules and their imports.
    block_id: F-block ID (e.g., "F6").
    block_name: Human name (e.g., "Integration MQTT").
    max_modules: Don't decompose if fewer modules than this.
    target_k: Target number of sub-components.
    min_cluster_size: Merge clusters smaller than this.
    parent_id: Parent component ID prefix for naming.

Returns:
    DecomposeResult with sub_components and internal_relationships.
    Empty sub_components if block is too small to decompose. |
| `iterative_decompose` | `manifest: Manifest, block_id: str, block_name: str, leaf_max_files: int, max_depth: int, target_k: int, min_cluster_size: int` | `list[DecomposeResult]` | Iteratively decompose until all clusters are <= leaf_max_files.

Returns list of DecomposeResult objects (one per decomposition round
that produced sub-components). Empty list if block is already a leaf. |
| `enrich_model` | `model: ArchitectureModel, project_root: Path` | `ArchitectureModel` | Auto-populate signatures, constants, test_contracts on components. |
| `format_enrichment_prompt` | `decompositions: list[DecomposeResult]` | `str` | Format all leaves for agent pattern/contract annotation.

Returns a prompt string containing:
1. Available patterns with indicators
2. All leaf components with their files/classes/functions
3. Instructions for annotation format |
| `full_extraction` | `repo_path: Path, target_systems: int` | `ArchitectureModel` | Run complete architecture extraction pipeline.

Pipeline steps:
1. Generate manifest (AST scan) + optionally scan non-Python languages
2. Build call graph from manifest
3. Group modules into components (uses SourceGraph path if multi-language)
4. Create initial model with components
5. Detect system boundaries (multi-signal)
6. Create behaviors from manifest (router/service functions)
7. Detect behavior triggers from call graph
8. Infer composite behaviors (use cases from trigger chains)
9. Decompose behaviors (raw steps → structured Steps)
10. Infer capabilities from behavior trigger patterns
11. Build capability hierarchy from URL nesting
12. Return enriched model

Args:
    repo_path: Path to repository root
    target_systems: Number of systems to detect (0 = auto)

Returns:
    Fully enriched ArchitectureModel |
| `full_extraction_with_docs` | `repo_path: Path, target_systems: int, output_dir: str` | `tuple[ArchitectureModel, dict]` | Full extraction + docs + compaction + hierarchical output.

Produces:
- Compact .architecture-model.yaml (use cases + summaries only)
- .architecture-models/full-model.yaml (complete reference)
- .architecture-models/docs/ (component specs, behavior specs, diagrams, etc.)
- .architecture-models/COMP-*/ (per-component sub-models with full behaviors)

Args:
    repo_path: Path to repository root
    target_systems: Number of systems to detect (0 = auto)
    output_dir: Output directory name (default: .architecture-models)

Returns:
    (compact_model, artifacts) where artifacts describes what was written. |
| `format_naming_context` | `result: DecomposeResult` | `str` | Format a DecomposeResult for the agent to assign semantic names.

Returns a compact string showing each cluster's key files, classes,
and inter-cluster dependencies. |
| `run_pipeline` | `project_root: Path, parent_model: str, model_file: str | None, output_dir: str, deep: bool, compact: bool, from_scratch: bool` | `PipelineResult` | Run the full decomposition pipeline.

1. Generate recursive manifests (per-block AST scan + dependency analysis)
2. Decompose parent model into sub-models (relationship tracing)
3. Write all artifacts to output_dir/<block_id>/

Args:
    project_root: Root directory with .architecture-model.yaml
    parent_model: Config filename with functional_blocks (default: .architecture-model.yaml)
    model_file: Model filename with entities/relationships. If None, auto-detects:
                tries parent_model first, then .architecture-model-extracted.yaml
    output_dir: Output directory name (default: .architecture-models)
    deep: Enable iterative deep decomposition of blocks
    compact: Compact root model after decomposition
    from_scratch: If True and no model exists, bootstrap one from manifest
                  using module grouping and auto-enrichment

Returns:
    PipelineResult with manifests, sub_models, and written paths. |
| `detect_behavior_triggers` | `behaviors: list[Behavior], call_graph: CallGraph, behavior_entries: dict[str, str], max_depth: int` | `list[Relationship]` | Detect triggers relationships between behaviors via call graph.

For each behavior's entry function, trace its call graph (BFS).
If the trace reaches the entry function of another behavior -> triggers edge. |
| `build_behavior_entry_map` | `behaviors: list[Behavior], call_graph: CallGraph` | `dict[str, str]` | Infer behavior entry function qnames from behavior name + source_file.

Heuristic: behavior.name (snake_cased) matches a function in behavior.source_file.
Falls back to first function in the source file with best name overlap. |
| `infer_composite_behaviors` | `model: ArchitectureModel` | `ArchitectureModel` | Create composite behaviors (use cases) from trigger chains.

For each chain of >=2 behaviors connected by triggers:
1. Create a composite Behavior (UC-N) representing end-to-end use case
2. Add contains relationships from composite to each chain member
3. Composite inherits trigger and actor from chain head |

## Interface Dependencies

- **requires** `uses_Manifest` → COMP-2 (Manifest) [ModuleStatus, FunctionInfo, ClassInfo, ImportDetail, DecoratedFunction, ModuleInfo, InterfaceEdge, SubFunctionEntry, BlockManifest, MetricsResult]
- **requires** `uses_Schema` → COMP-6 (Schema) [load_profile, EnumExtension, EntityExtension, ConditionalRule, DomainProfile]
- **provides** `exposes_to_Docs` → COMP-3 (Docs) [Status, RelationType, ActorType, InterfaceType, ConstraintType, Priority, Strength, ComponentKind, BehaviorPattern, SymbolKind]
- **provides** `exposes_to_Manifest` → COMP-2 (Manifest) [Status, RelationType, ActorType, InterfaceType, ConstraintType, Priority, Strength, ComponentKind, BehaviorPattern, SymbolKind]
- **requires** `uses_Docs` → COMP-3 (Docs) [generate_docs]
- **requires** `uses_Store` → COMP-5 (Store) [save_project, save_block, load_project, ProjectSnapshot]
- **provides** `exposes_to_Store` → COMP-5 (Store) [load_block_model, load_model, validate_model_data, dump_model, save_model]

## Patterns

- state-machine

## Confidence

100%
