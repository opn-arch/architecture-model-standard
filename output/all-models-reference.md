# Architecture Models -- Complete Reference

## Parent Model: architecture-model-standard

- **Schema Version:** 2.0
- **Validation Score:** 100/100
- **Components:** 25
- **Capabilities:** 10
- **Interfaces:** 7
- **Behaviors:** 79
- **Constraints:** 2
- **Layers:** 1
- **Actors:** 2
- **Relationships:** 237
- **Signatures:** 85
- **Constants:** 26
- **Test Contracts:** 266

### Actors

- **ACT-DEV** -- Developer: Software engineer using CLI to manage architecture models
- **ACT-LLM** -- LLM Agent: AI agent consuming architecture models via opencode-arch MCP tools

### Capabilities

| ID | Name | F-Block | Description |
|----|------|---------|-------------|
| CAP-F1 | Model Parsing & Validation | F3 | Parse YAML models and validate structural correctness (score 0-100) |
| CAP-F2 | Reality Manifest Generation | F5 | AST scanning to produce ground-truth code inventories with metrics, body hints, and test contracts |
| CAP-F3 | Model Slicing & Diffing | F3 | Subset extraction by F-block/layer, model version comparison, and enriched model composition |
| CAP-F4 | CLI Operations | F1 | Command-line interface for init, validate, slice, diff, stats, impact, manifest, coverage, enrich |
| CAP-F5 | Configuration Management | F2 | Auto-discovery config loading and project configuration schema |
| CAP-F6 | Schema Specification | F8 | JSON Schema definitions for architecture model validation |
| CAP-F7 | Model Extraction | F4 | Extract architecture model from source code |
| CAP-F8 | Domain Profiles | F7 | Cross-domain architecture modeling via domain profiles (software, controls, mechanical, electrical) |
| CAP-F9 | Shared Utilities | F9 | File discovery, exclusion patterns, and shared helper functions |
| CAP-F10 | Auto-Enrichment | F6 | Populate signatures, constants, and test_contracts from AST scanning |

### Interfaces

| ID | Name | Type | Description |
|----|------|------|-------------|
| IF-CLI | CLI Interface | InterfaceType.INTERNAL | Entry point: architecture-model {init,validate,slice,diff,stats,impact,manifest,coverage,enrich} |
| IF-PARSE-API | Parser API | InterfaceType.INTERNAL | load_model(path) -> ArchitectureModel, save_model(model, path), dump_model(model) -> str |
| IF-VALIDATE-API | Validator API | InterfaceType.INTERNAL | validate_model(model) -> ValidationResult (score, issues, is_valid) |
| IF-MANIFEST-API | Manifest API | InterfaceType.INTERNAL | generate_manifest(project_root) -> Manifest |
| IF-SLICER-API | Slicer API | InterfaceType.INTERNAL | slice_by_fblock(model, id), slice_by_layer(model, id), slice_for_artifact(model, artifact) |
| IF-PROFILE-API | Profile API | InterfaceType.INTERNAL | load_profile(name) -> DomainProfile |
| IF-ENRICH-API | Enrichment API | InterfaceType.INTERNAL | enrich_model(model, project_root) -> ArchitectureModel |

### Behaviors

- **BEH-INIT** -- Project Initialization: Scan directory structure, discover source root, auto-generate .architecture-model.yaml
- **BEH-VALIDATE** -- Model Validation: Check architectural claims against schema and structural invariants, produce score 0-100
- **BEH-MANIFEST** -- Manifest Generation: Walk source tree, parse ASTs, extract functions/classes/imports, compute metrics, discover blocks
- **BEH-ENRICH** -- Auto-Enrichment: Enrich architecture model with function signatures, constants, and test contracts from AST
- **BEH-EXTRACT** -- Model Extraction from Code: Extract architecture model entities and relationships from source code analysis
- **BEH-SLICE** -- Model Slicing: Extract sub-models by various criteria
- **BEH-DIFF** -- Model Diffing: Compare two architecture models
- **BEH-MERGE** -- Model Merging: Merge and compose architecture models
- **BEH-DECOMPOSE** -- Model Decomposition: Decompose model into subsystems
- **BEH-VALIDATE-IDS** -- ID Uniqueness Check: Check all entity IDs are unique across entity types
- **BEH-VALIDATE-REFS** -- Referential Integrity Check: Verify all relationship endpoints reference existing entities
- **BEH-VALIDATE-ORPHANS** -- Orphan Entity Detection: Find entities with no relationships
- **BEH-VALIDATE-STATUS** -- Status Consistency Check: Verify status field values are valid
- **BEH-VALIDATE-CAPS** -- Capability Realization Check: Ensure every capability is realized by at least one component
- **BEH-VALIDATE-META** -- Meta Completeness Check: Validate model meta section has required fields
- **BEH-VALIDATE-V11** -- V1.1 Semantics Check: Validate schema v1.1+ semantic rules
- **BEH-VALIDATE-REGEN** -- Regen Readiness Check: Score components for code regeneration readiness
- **BEH-VALIDATE-PROFILE** -- Domain Profile Validation: Validate domain-profile-specific rules
- **BEH-VALIDATE-IMPROVE** -- Improvement Opportunities: Detect non-critical improvements
- **BEH-PARSE-LOAD** -- Model Loading: Load YAML file, parse into ArchitectureModel dataclass
- **BEH-PARSE-SAVE** -- Model Saving: Serialize ArchitectureModel to YAML via to_dict()
- **BEH-PARSE-DUMP** -- Model Dumping: Dump model to string format for display
- **BEH-SLICE-FBLOCK** -- Slice by F-Block: Extract sub-model for a functional block by tracing relationships
- **BEH-SLICE-LAYER** -- Slice by Layer: Extract sub-model for an architectural layer
- **BEH-SLICE-STATUS** -- Slice by Status: Filter model entities by status value
- **BEH-SLICE-ARTIFACT** -- Slice by Artifact: Extract sub-model relevant to a specific artifact type
- **BEH-SLICE-COMPONENT** -- Slice by Component: Extract sub-model for a single component with dependencies
- **BEH-DIFF-ENTITIES** -- Entity Diff: Compare entities between two models, detect added/removed/modified
- **BEH-DIFF-RELS** -- Relationship Diff: Compare relationships between two models
- **BEH-MERGE-MANIFEST** -- Merge Manifest: Merge reality manifest data into architecture model
- **BEH-MERGE-ENRICH** -- Enrich from Manifest: Enrich model components with manifest-derived data
- **BEH-MERGE-COMPACT** -- Compact for Generation: Compact model for code generation context
- **BEH-MERGE-COMPOSE** -- Compose Enriched Model: Compose a fully enriched model from multiple sources
- **BEH-DECOMPOSE-IDENTIFY** -- Identify Systems: Discover functional subsystems from component graph
- **BEH-DECOMPOSE-COMPLEXITY** -- Compute Complexity: Calculate complexity metrics for subsystem partitioning
- **BEH-DECOMPOSE-PARTITION** -- Partition Subsystems: Partition components into subsystems by affinity
- **BEH-SCAN-PARSE** -- AST Parsing: Parse Python source file into AST
- **BEH-SCAN-FUNCTIONS** -- Function Extraction: Extract function definitions with signatures, decorators, docstrings
- **BEH-SCAN-CLASSES** -- Class Extraction: Extract class definitions with methods and attributes
- **BEH-SCAN-IMPORTS** -- Import Extraction: Extract import statements with aliases and relative resolution
- **BEH-SCAN-CONSTANTS** -- Constant Extraction: Extract module-level constants and assignments
- **BEH-SCAN-METRICS** -- Metrics Computation: Compute line count, status, exports for scanned file
- **BEH-MANIFEST-CONFIG** -- Config Loading: Load or discover project configuration for manifest generation
- **BEH-MANIFEST-METRICS** -- Project Metrics: Compute project-wide metrics (total lines, file counts)
- **BEH-MANIFEST-BLOCKS** -- Block Assembly: Assemble functional blocks from config with file enumeration
- **BEH-MANIFEST-SCAN** -- Block Scanning: Scan all files within each block for AST data
- **BEH-MANIFEST-IFACE** -- Interface Discovery: Discover inter-block interfaces from import analysis
- **BEH-MANIFEST-ASSEMBLE** -- Manifest Assembly: Assemble final manifest from blocks, interfaces, metrics
- **BEH-BODYHINT-CLASSIFY** -- Complexity Classification: Classify function complexity as TRIVIAL/SHORT/COMPLEX
- **BEH-BODYHINT-SUMMARIZE** -- Body Summarization: Generate body_hint text summarizing function implementation
- **BEH-TEST-DISCOVER** -- Test Method Discovery: Find test methods/functions in test files
- **BEH-TEST-ASSERTIONS** -- Assertion Pattern Matching: Extract assertion patterns from test methods (unittest + pytest)
- **BEH-IFACE-RESOLVE** -- Import Resolution: Resolve relative and absolute imports to interface edges
- **BEH-IFACE-DEDUP** -- Interface Deduplication: Deduplicate interface edges from multiple import sources
- **BEH-RECURSIVE-SCAN** -- Per-Block Deep Scan: Perform deep AST scan within a single F-block
- **BEH-RECURSIVE-DEPS** -- Cross-Block Dependencies: Compute dependency graph between F-blocks
- **BEH-ENRICH-SIGS** -- Signature Enrichment: Extract function signatures from AST and add to components
- **BEH-ENRICH-CONSTS** -- Constant Enrichment: Extract module-level constants and add to components
- **BEH-ENRICH-TESTS** -- Test Contract Enrichment: Discover test files via 7 naming conventions and extract contracts
- **BEH-ORCH-FIND-COMPS** -- Find Block Components: Find all components belonging to an F-block
- **BEH-ORCH-FIND-PARENT** -- Find Parent Component: Locate parent component for a block's component hierarchy
- **BEH-ORCH-TRACE** -- Trace Entities: Trace relationships to find connected capabilities, interfaces, behaviors, constraints
- **BEH-ORCH-COLLECT-RELS** -- Collect Relationships: Collect internal and boundary relationships for sub-model
- **BEH-ORCH-BUILD** -- Build Sub-Model: Assemble final sub-model YAML from traced entities
- **BEH-EXTRACT-CAPS** -- Extract Capabilities: Derive capabilities from source code analysis
- **BEH-EXTRACT-ACTORS** -- Extract Actors: Identify external actors from code patterns
- **BEH-EXTRACT-COMPS** -- Extract Components: Map source modules to architecture components
- **BEH-EXTRACT-IFACES** -- Extract Interfaces: Derive interfaces from import/export analysis
- **BEH-EXTRACT-RELS** -- Extract Relationships: Infer relationships between extracted entities
- **BEH-CLI-SLICE** -- CLI Slice Command: Execute model slicing from command line
- **BEH-CLI-DIFF** -- CLI Diff Command: Execute model diff from command line
- **BEH-CLI-STATS** -- CLI Stats Command: Display model statistics from command line
- **BEH-CLI-IMPACT** -- CLI Impact Command: Trace change impact from command line
- **BEH-CLI-DECOMPOSE** -- CLI Decompose Command: Generate per-F-block sub-models from command line
- **BEH-CLI-COVERAGE** -- CLI Coverage Command: Display regen coverage metrics from command line
- **BEH-PROFILE-LOAD** -- Load Profile: Resolve profile path, load YAML, parse into dataclass
- **BEH-PROFILE-APPLY** -- Apply Profile Rules: Apply domain-specific validation rules from profile
- **BEH-UTILS-DISCOVER** -- File Discovery: Discover Python source files with exclusion patterns
- **BEH-UTILS-TESTS** -- Test File Discovery: Discover test files matching source modules

### Constraints

- **CON-SCHEMA** -- Schema Compliance (ConstraintType.TECHNOLOGY): All models must conform to JSON Schema v1.5 with 7 entity types and 8 relationship types
- **CON-NO-ORPHANS** -- No Orphaned Entities (ConstraintType.TECHNOLOGY): Every entity must participate in at least one relationship

### Components

| ID | Name | F-Block | Sigs | Const | Contracts | Files | Regen |
|----|------|---------|:----:|:-----:|:---------:|:-----:|:-----:|
| COMP-CLI | cli | F1 | 1 | 0 | 0 | 2 | NO |
| COMP-CONFIG | config | F2 | 15 | 1 | 1 | 3 | YES |
| COMP-CORE | core | F3 | 0 | 0 | 0 | 0 | NO |
| COMP-CORE-DECOMPOSER | core.decomposer | F3 | 5 | 1 | 15 | 1 | YES |
| COMP-CORE-DIFFER | core.differ | F3 | 8 | 0 | 0 | 1 | NO |
| COMP-CORE-MERGER | core.merger | F3 | 8 | 5 | 2 | 1 | YES |
| COMP-CORE-PARSER | core.parser | F3 | 4 | 1 | 11 | 1 | YES |
| COMP-CORE-SLICER | core.slicer | F3 | 4 | 1 | 12 | 1 | YES |
| COMP-CORE-TYPES | core.types | F3 | 6 | 0 | 30 | 1 | YES |
| COMP-CORE-VALIDATOR | core.validator | F3 | 7 | 2 | 11 | 1 | YES |
| COMP-DECOMPOSE | decompose | F6 | 2 | 0 | 3 | 1 | YES |
| COMP-ENRICH | enrich | F6 | 1 | 0 | 2 | 1 | YES |
| COMP-EXTRACT | extract | F4 | 1 | 0 | 0 | 1 | NO |
| COMP-MANIFEST | manifest | F5 | 0 | 0 | 0 | 0 | NO |
| COMP-MANIFEST-BLOCKS | manifest.blocks | F5 | 1 | 1 | 21 | 1 | YES |
| COMP-MANIFEST-BODY-HINTS | manifest.body_hints | F5 | 3 | 4 | 29 | 1 | YES |
| COMP-MANIFEST-GENERATOR | manifest.generator | F5 | 4 | 1 | 21 | 3 | YES |
| COMP-MANIFEST-INTERFACES | manifest.interfaces | F5 | 1 | 1 | 20 | 1 | YES |
| COMP-MANIFEST-METRICS | manifest.metrics | F5 | 1 | 1 | 19 | 1 | YES |
| COMP-MANIFEST-SCANNER | manifest.scanner | F5 | 1 | 2 | 21 | 1 | YES |
| COMP-MANIFEST-TEST-ANALYZER | manifest.test_analyzer | F5 | 2 | 3 | 24 | 1 | YES |
| COMP-MANIFEST-TYPES | manifest.types | F5 | 3 | 1 | 17 | 1 | YES |
| COMP-PROFILES | profiles | F7 | 3 | 1 | 0 | 3 | NO |
| COMP-SPEC | spec | F8 | 0 | 0 | 0 | 1 | NO |
| COMP-UTILS | utils | F9 | 4 | 0 | 7 | 2 | YES |

### Component Details

#### COMP-CLI: cli

- **F-Block:** F1
- **Description:** CLI entry point and command dispatch (9 commands: init, validate, slice, diff, stats, impact, manifest, coverage, enrich)
- **Files:** src/architecture_model/cli/main.py, src/architecture_model/cli/__init__.py

**Signatures:**

- `main(argv: list[str] | None) --> int`

#### COMP-CONFIG: config

- **F-Block:** F2
- **Description:** Configuration loader (auto-discovery) and schema definition
- **Files:** src/architecture_model/config/loader.py, src/architecture_model/config/schema.py, src/architecture_model/config/__init__.py

**Constants:**

- `CONFIG_FILENAME` = `.architecture-model.yaml`

**Signatures:**

- `load_config(root: Path) --> ProjectConfig`
- `discover_config(root: Path) --> tuple[ProjectConfig, DiscoveryReport]`
- `get_config(root: Path) --> ProjectConfig`
- `write_config(config: ProjectConfig, root: Path | None) --> Path`
- `resolve(project_name: str, root: Path) --> 'ResolvedOutputConfig'`
- `layer_dir_map() --> dict[str, list[str]]` @property
- `fblock_dir_map() --> dict[str, str]` @property
- `fblock_dict() --> dict[str, dict[str, Any]]` @property
- `metrics_paths() --> dict[str, Path]` @property
- `resolved_output() --> ResolvedOutputConfig`
- `from_dict(data: dict[str, Any], root: Path) --> 'ProjectConfig'` @classmethod
- `to_dict() --> dict[str, Any]`
- `add_candidate(category: str, path: str, accepted: bool, reason: str) --> None`
- `claim_rate() --> float` @property
- `summary() --> str`

**Test Contracts (1):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_config_discovery_typed.py | test_discover_config_returns_report | config.name == tmp_path.name | value_equality |

#### COMP-CORE: core

- **F-Block:** F3
- **Description:** Parser, validator, slicer, differ, merger, decomposer, type system

#### COMP-CORE-DECOMPOSER: core.decomposer

- **F-Block:** F3
- **Description:** Model decomposition into subsystems
- **Files:** src/architecture_model/core/decomposer.py

**Constants:**

- `SYSTEM_THRESHOLD` = `10.0`

**Signatures:**

- `compute_complexity(comp: Component, model: ArchitectureModel) --> float`
- `identify_systems(model: ArchitectureModel, manifest: dict) --> list[SystemCandidate]`
- `auto_assign_f_blocks(model: ArchitectureModel, max_cluster_size: int) --> ArchitectureModel`
- `decompose_model(model: ArchitectureModel, manifest: dict, output_dir: str) --> DecompositionResult`
- `test_affinity_decompose(repo_path: Path) --> list[Subsystem]`

**Test Contracts (15):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_decomposer.py | test_empty_component_is_zero | compute_complexity(comp, model) == 0.0 | value_equality |
| test_decomposer.py | test_symbols_contribute | score == pytest.approx(4.9) | value_equality |
| test_decomposer.py | test_functions_contribute | score == pytest.approx(2.0) | value_equality |
| test_decomposer.py | test_deps_contribute | score == pytest.approx(3.0) | value_equality |
| test_decomposer.py | test_complex_component_above_threshold | score == pytest.approx(36.0) | value_equality |
| test_decomposer.py | test_non_depends_on_rels_ignored | score == 0.0 | value_equality |
| test_decomposer.py | test_identifies_complex_fblock_group | len(systems) == 1 | value_equality |
| test_decomposer.py | test_simple_model_no_systems | len(systems) == 0 | value_equality |
| test_decomposer.py | test_components_without_fblock_not_grouped | len(systems) == 0 | value_equality |
| test_decomposer.py | test_multiple_systems_identified | len(systems) == 2 | value_equality |
| test_decomposer.py | test_uses_fblock_id_as_name_when_not_in_manifest | len(systems) == 1 | value_equality |
| test_decomposer.py | test_decompose_creates_system | result isinstance DecompositionResult | type_check |
| test_decomposer.py | test_inter_system_rels_deduplicated | len(deps_to_simple) == 1 | value_equality |
| test_decomposer.py | test_sub_model_meta_has_system_name | sub.meta.system == 'Core Engine' | value_equality |
| test_decomposer.py | test_no_systems_returns_unchanged | len(result.top_level.entities.systems) == 0 | value_equality |

#### COMP-CORE-DIFFER: core.differ

- **F-Block:** F3
- **Description:** Model version comparison and diff generation
- **Files:** src/architecture_model/core/differ.py

**Signatures:**

- `has_changes() --> bool` @property
- `added_count() --> int` @property
- `removed_count() --> int` @property
- `modified_count() --> int` @property
- `summary() --> str`
- `format_report() --> str`
- `affected_artifacts() --> set[str]`
- `diff_models(old_model: ArchitectureModel, new_model: ArchitectureModel) --> ModelDiff`

#### COMP-CORE-MERGER: core.merger

- **F-Block:** F3
- **Description:** Model merging and composition
- **Files:** src/architecture_model/core/merger.py

**Constants:**

- `_MAX_MEMBERS_PER_SYMBOL` = `8`
- `_MAX_FUNCTIONS_PER_COMPONENT` = `12`
- `_MAX_SYMBOLS_PER_COMPONENT` = `6`
- `_YAML_CHAR_BUDGET` = `12000`
- `_EXCLUDED_FILES` = `frozenset({'setup.py', 'conftest.py'})`

**Signatures:**

- `merge_manifest(model: ArchitectureModel, manifest_path: str | Path, project_root: str | Path | None) --> ArchitectureModel`
- `model() --> ArchitectureModel` @property
- `entities()` @property
- `relationships()` @property
- `meta()` @property
- `enrich_from_manifest(model: ArchitectureModel, manifest: dict) --> EnrichmentResult`
- `compact_for_generation(model: ArchitectureModel) --> ArchitectureModel`
- `compose_enriched_model(project_root: Path) --> ArchitectureModel`

**Test Contracts (2):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_merger.py | test_manifest_hash_updated | len(model_copy.meta.manifest_hash) == 16 | value_equality |
| test_merger.py | test_missing_manifest_returns_unchanged | model_copy.meta.manifest_hash == original_hash | value_equality |

#### COMP-CORE-PARSER: core.parser

- **F-Block:** F3
- **Description:** YAML model parser (load_model, save_model, dump_model)
- **Files:** src/architecture_model/core/parser.py

**Constants:**

- `SCHEMA_PATH` = `Path(__file__).parent.parent / 'spec' / 'schema.json'`

**Signatures:**

- `load_model(path: str | Path) --> ArchitectureModel`
- `validate_model_data(data: dict[str, Any]) --> list[str]`
- `dump_model(model: ArchitectureModel) --> dict[str, Any]`
- `save_model(model: ArchitectureModel, path: str | Path) --> None`

**Test Contracts (11):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_parser.py | test_load_returns_architecture_model | model isinstance ArchitectureModel | type_check |
| test_parser.py | test_meta_has_schema_version | model.meta.schema_version == '0.1.0' | value_equality |
| test_parser.py | test_empty_file_raises | raises ValueError | raises |
| test_parser.py | test_missing_file_raises | raises FileNotFoundError | raises |
| test_parser.py | test_malformed_yaml_raises | raises Exception | raises |
| test_parser.py | test_round_trip_preserves_entity_count | reloaded.entity_count == model.entity_count | value_equality |
| test_parser.py | test_round_trip_preserves_relationship_count | reloaded.relationship_count == model.relationship_count | value_equality |
| test_parser.py | test_round_trip_preserves_meta | reloaded.meta.project == model.meta.project | value_equality |
| test_parser.py | test_round_trip_preserves_actor_ids | original_ids == reloaded_ids | value_equality |
| test_parser.py | test_real_model_passes_schema | len(real_errors) == 0 | value_equality |
| test_parser.py | test_minimal_valid_structure | real_errors isinstance list | type_check |

#### COMP-CORE-SLICER: core.slicer

- **F-Block:** F3
- **Description:** Model subsetting by F-block, layer, or artifact
- **Files:** src/architecture_model/core/slicer.py

**Constants:**

- `ACTIVE` = `ACTIVE` (Status enum member)

**Signatures:**

- `slice_by_fblock(model: ArchitectureModel, f_block: str, include_relationships: bool) --> ArchitectureModel`
- `slice_by_layer(model: ArchitectureModel, layer_id: str) --> ArchitectureModel`
- `slice_by_status(model: ArchitectureModel, status: Status) --> ArchitectureModel`
- `slice_for_artifact(model: ArchitectureModel, artifact_name: str) --> ArchitectureModel`

**Test Contracts (12):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_slicer.py | test_returns_only_fblock_capabilities | cap.f_block == 'F1' | value_equality |
| test_slicer.py | test_returns_only_fblock_components | comp.f_block == 'F2' | value_equality |
| test_slicer.py | test_nonexistent_fblock_returns_empty | len(sliced.entities.capabilities) == 0 | value_equality |
| test_slicer.py | test_no_relationship_mode | sliced.relationship_count == 0 | value_equality |
| test_slicer.py | test_registered_artifact_returns_subset | sliced isinstance ArchitectureModel | type_check |
| test_slicer.py | test_registered_artifact_preserves_meta | sliced.meta.project == model.meta.project | value_equality |
| test_slicer.py | test_functional_has_no_components | len(sliced.entities.components) == 0 | value_equality |
| test_slicer.py | test_unregistered_artifact_returns_full_copy | sliced.entity_count == model.entity_count | value_equality |
| test_slicer.py | test_sliced_model_no_extra_entities_leaked | len(leaked) == 0 | value_equality |
| test_slicer.py | test_active_filter | cap.status == Status.ACTIVE | value_equality |
| test_slicer.py | test_slice_by_existing_layer | sliced isinstance ArchitectureModel | type_check |
| test_slicer.py | test_slice_by_nonexistent_layer | len(sliced.entities.components) == 0 | value_equality |

#### COMP-CORE-TYPES: core.types

- **F-Block:** F3
- **Description:** Type system (ArchitectureModel, Component, Capability, FunctionSignature, TestContract, etc.)
- **Files:** src/architecture_model/core/types.py

**Signatures:**

- `parse(value: str) --> RelationType | str` @classmethod
- `all_entity_ids() --> set[str]` @property
- `entity_count() --> int` @property
- `relationship_count() --> int` @property
- `to_dict() --> dict[str, Any]`
- `to_yaml() --> str`

**Test Contracts (30):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_types.py | test_returns_dict | result isinstance dict | type_check |
| test_types.py | test_meta_fields | meta['schema_version'] == '1.0' | value_equality |
| test_types.py | test_status_is_string | actor['status'] == 'ACTIVE' | value_equality |
| test_types.py | test_actor_type_is_string | actor['type'] == 'human' | value_equality |
| test_types.py | test_interface_type_is_string | iface['type'] == 'REST' | value_equality |
| test_types.py | test_constraint_type_is_string | con['type'] == 'performance' | value_equality |
| test_types.py | test_priority_is_string | cap['priority'] == 'high' | value_equality |
| test_types.py | test_relationship_type_is_string | rel['type'] == 'realizes' | value_equality |
| test_types.py | test_strength_is_string | rel['strength'] == 'strong' | value_equality |
| test_types.py | test_from_to_values_correct | rel['from'] == 'comp-1' | value_equality |
| test_types.py | test_actor_fields | actor['id'] == 'actor-1' | value_equality |
| test_types.py | test_capability_fields | cap['f_block'] == 'FB-CodeGen' | value_equality |
| test_types.py | test_behavior_fields | beh['trigger'] == 'New project scan' | value_equality |
| test_types.py | test_interface_fields | iface['type'] == 'REST' | value_equality |
| test_types.py | test_constraint_fields | con['type'] == 'performance' | value_equality |
| test_types.py | test_layer_fields | layer['order'] == 2 | value_equality |
| test_types.py | test_component_fields | comp['layer'] == 'layer-1' | value_equality |
| test_types.py | test_returns_string | result isinstance str | type_check |
| test_types.py | test_valid_yaml | parsed isinstance dict | type_check |
| test_types.py | test_yaml_matches_to_dict | parsed == model.to_dict() | value_equality |
| test_types.py | test_round_trip_preserves_entity_ids | original.all_entity_ids == rebuilt.all_entity_ids | value_equality |
| test_types.py | test_round_trip_preserves_entity_count | original.entity_count == rebuilt.entity_count | value_equality |
| test_types.py | test_round_trip_preserves_relationship_count | original.relationship_count == rebuilt.relationship_count | value_equality |
| test_types.py | test_round_trip_preserves_meta | rebuilt.meta.schema_version == original.meta.schema_version | value_equality |
| test_types.py | test_round_trip_preserves_actor_details | new_actor.id == orig_actor.id | value_equality |
| test_types.py | test_round_trip_preserves_relationship_details | new_rel.type == orig_rel.type | value_equality |
| test_types.py | test_round_trip_preserves_behavior_details | new.trigger == orig.trigger | value_equality |
| test_types.py | test_round_trip_preserves_component_details | new.layer == orig.layer | value_equality |
| test_types.py | test_round_trip_minimal_model | rebuilt.entity_count == original.entity_count | value_equality |
| test_types.py | test_yaml_round_trip | original.all_entity_ids == rebuilt.all_entity_ids | value_equality |

#### COMP-CORE-VALIDATOR: core.validator

- **F-Block:** F3
- **Description:** Structural validation engine producing score 0-100
- **Files:** src/architecture_model/core/validator.py

**Constants:**

- `ERROR` = `ERROR` (Severity enum member)
- `INFO` = `INFO` (Severity enum member)

**Signatures:**

- `error_count() --> int` @property
- `warning_count() --> int` @property
- `info_count() --> int` @property
- `is_valid() --> bool` @property
- `score() --> int` @property
- `summary() --> str`
- `validate_model(model: ArchitectureModel, strict: bool) --> ValidationResult`

**Test Contracts (11):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_validator.py | test_perfect_model_scores_100 | result.score == 100 | value_equality |
| test_validator.py | test_score_deducts_10_per_error | result.score == 90 | value_equality |
| test_validator.py | test_score_deducts_2_per_warning | result.score == 98 | value_equality |
| test_validator.py | test_score_floors_at_zero | result.score == 0 | value_equality |
| test_validator.py | test_info_does_not_affect_score | result.score == 100 | value_equality |
| test_validator.py | test_duplicate_id_across_types_errors | dup_errors[0].severity == Severity.ERROR | value_equality |
| test_validator.py | test_unique_ids_no_duplicates | len(dup_errors) == 0 | value_equality |
| test_validator.py | test_known_external_not_dangling | len(dangling) == 0 | value_equality |
| test_validator.py | test_orphan_component_produces_info | orphans[0].severity == Severity.INFO | value_equality |
| test_validator.py | test_orphan_behavior_produces_info | orphans[0].severity == Severity.INFO | value_equality |
| test_validator.py | test_dormant_component_not_orphan | len(orphans) == 0 | value_equality |

#### COMP-DECOMPOSE: decompose

- **F-Block:** F6
- **Description:** Model decomposition into per-F-block sub-models
- **Files:** src/architecture_model/orchestration/decompose.py

**Signatures:**

- `decompose_model(project_root)`
- `write_sub_models(sub_models, output_dir)`

**Test Contracts (3):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_decompose.py | test_decompose_meta_links_to_parent | sub.meta.parent_model == '../../.architecture-model.yaml' | value_equality |
| test_decompose.py | test_write_sub_models | data['meta']['parent_model'] == '../../.architecture-mode... | value_equality |
| test_decompose.py | test_decompose_cli | ret == 0 | value_equality |

#### COMP-ENRICH: enrich

- **F-Block:** F6
- **Description:** Auto-enrichment of architecture models with AST-derived signatures, constants, and test contracts
- **Files:** src/architecture_model/orchestration/enrich.py

**Signatures:**

- `enrich_model(model: ArchitectureModel, project_root: Path) --> ArchitectureModel`

**Test Contracts (2):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_enrich.py | test_enrich_skips_planned_components | len(c.signatures) == 0 | value_equality |
| test_enrich.py | test_enrich_handles_missing_files | len(c.signatures) == 0 | value_equality |

#### COMP-EXTRACT: extract

- **F-Block:** F4
- **Description:** Extract architecture model from source code analysis
- **Files:** src/architecture_model/extract/from_code.py

**Signatures:**

- `extract_from_code(project_root: str | Path, config: ProjectConfig | None, manifest: dict | None) --> ArchitectureModel`

#### COMP-MANIFEST: manifest

- **F-Block:** F5
- **Description:** AST scanner, block discovery, metrics, interface detection, body hints, test analyzer

#### COMP-MANIFEST-BLOCKS: manifest.blocks

- **F-Block:** F5
- **Description:** Functional block discovery from source tree
- **Files:** src/architecture_model/manifest/blocks.py

**Constants:**

- `ACTIVE` = `ACTIVE` (Status/FileStatus enum member)

**Signatures:**

- `process_block(root: Path, block_id: str, block_def: dict, sub_block_configs: list | None) --> BlockManifest`

**Test Contracts (21):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_blocks_typed.py | test_process_block_returns_block_manifest | result isinstance BlockManifest | type_check |
| test_blocks_typed.py | test_process_block_backward_compat | d['sub_functions'] isinstance list | type_check |
| test_blocks_typed.py | test_deprecated_process_block_returns_dict | result isinstance dict | type_check |
| test_blocks_typed.py | test_sub_function_entry_has_signature_strings | f isinstance str | type_check |
| test_manifest_types.py | test_module_info_creation | m.file == 'src/foo.py' | value_equality |
| test_manifest_types.py | test_module_status_values | ModuleStatus.ACTIVE.value == 'active' | value_equality |
| test_manifest_types.py | test_scan_report_success_rate | r.success_rate == 0.9 | value_equality |
| test_manifest_types.py | test_scan_report_empty | r.success_rate == 1.0 | value_equality |
| test_manifest_types.py | test_interface_edge_creation | e.source == 'a/b.py' | value_equality |
| test_manifest_types.py | test_manifest_creation | m.metrics.values['total_python_files'] == 10 | value_equality |
| test_manifest_types.py | test_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_manifest_types.py | test_module_info_to_dict | d['status'] == 'active' | value_equality |
| test_manifest_types.py | test_block_manifest_to_dict | d['name'] == 'Core' | value_equality |
| test_manifest_types.py | test_sub_function_entry_to_dict | d['id'] == 'F1.1' | value_equality |
| test_manifest.py | test_each_block_has_dirs | block_def['dirs'] isinstance list | type_check |
| test_manifest.py | test_each_block_has_files | block_def['files'] isinstance list | type_check |
| test_manifest.py | test_has_metrics | generated['metrics'] isinstance dict | type_check |
| test_manifest.py | test_functional_blocks_have_sub_functions | block['sub_functions'] isinstance list | type_check |
| test_manifest.py | test_has_modules | generated['modules'] isinstance list | type_check |
| test_manifest.py | test_has_interfaces | generated['interfaces'] isinstance list | type_check |
| test_manifest.py | test_returns_non_empty_markdown | result isinstance str | type_check |

#### COMP-MANIFEST-BODY-HINTS: manifest.body_hints

- **F-Block:** F5
- **Description:** Function body hint extraction for trivial implementations
- **Files:** src/architecture_model/manifest/body_hints.py

**Constants:**

- `TRIVIAL` = `trivial` (BodyComplexity enum member)
- `SHORT` = `short` (BodyComplexity enum member)
- `COMPLEX` = `complex` (BodyComplexity enum member)
- `ACTIVE` = `ACTIVE` (Status/FileStatus enum member)

**Signatures:**

- `classify_function(source: str, func_name: str) --> BodyComplexity`
- `extract_body_hint(source: str, func_name: str, class_name: str | None) --> str`
- `extract_file_hints(filepath: Path, include_private: bool) --> list[FunctionSignature]`

**Test Contracts (29):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_body_hints.py | test_trivial_single_statement | classify_function(source, 'greet') == BodyComplexity.TRIVIAL | value_equality |
| test_body_hints.py | test_trivial_with_docstring | classify_function(source, 'greet') == BodyComplexity.TRIVIAL | value_equality |
| test_body_hints.py | test_short_two_statements | classify_function(source, 'add') == BodyComplexity.SHORT | value_equality |
| test_body_hints.py | test_short_five_statements | classify_function(source, 'process') == BodyComplexity.SHORT | value_equality |
| test_body_hints.py | test_complex_six_statements | classify_function(source, 'complex_func') == BodyComplexi... | value_equality |
| test_body_hints.py | test_complex_with_docstring_not_counted | classify_function(source, 'big_func') == BodyComplexity.C... | value_equality |
| test_body_hints.py | test_function_not_found_raises | raises ValueError | raises |
| test_body_hints.py | test_trivial_returns_exact_body | hint == 'return 42' | value_equality |
| test_body_hints.py | test_class_method_extraction | hint == 'return a + b' | value_equality |
| test_body_hints.py | test_body_hint_populated | sig.body_hint == 'return 42' | value_equality |
| test_body_hints.py | test_params_populated | sig.returns == 'float' | value_equality |
| test_body_hints.py | test_returns_populated | sig.returns == 'str' | value_equality |
| test_manifest_types.py | test_module_info_creation | m.file == 'src/foo.py' | value_equality |
| test_manifest_types.py | test_module_status_values | ModuleStatus.ACTIVE.value == 'active' | value_equality |
| test_manifest_types.py | test_scan_report_success_rate | r.success_rate == 0.9 | value_equality |
| test_manifest_types.py | test_scan_report_empty | r.success_rate == 1.0 | value_equality |
| test_manifest_types.py | test_interface_edge_creation | e.source == 'a/b.py' | value_equality |
| test_manifest_types.py | test_manifest_creation | m.metrics.values['total_python_files'] == 10 | value_equality |
| test_manifest_types.py | test_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_manifest_types.py | test_module_info_to_dict | d['status'] == 'active' | value_equality |
| test_manifest_types.py | test_block_manifest_to_dict | d['name'] == 'Core' | value_equality |
| test_manifest_types.py | test_sub_function_entry_to_dict | d['id'] == 'F1.1' | value_equality |
| test_manifest.py | test_each_block_has_dirs | block_def['dirs'] isinstance list | type_check |
| test_manifest.py | test_each_block_has_files | block_def['files'] isinstance list | type_check |
| test_manifest.py | test_has_metrics | generated['metrics'] isinstance dict | type_check |
| test_manifest.py | test_functional_blocks_have_sub_functions | block['sub_functions'] isinstance list | type_check |
| test_manifest.py | test_has_modules | generated['modules'] isinstance list | type_check |
| test_manifest.py | test_has_interfaces | generated['interfaces'] isinstance list | type_check |
| test_manifest.py | test_returns_non_empty_markdown | result isinstance str | type_check |

#### COMP-MANIFEST-GENERATOR: manifest.generator

- **F-Block:** F5
- **Description:** Top-level manifest generation orchestrator
- **Files:** src/architecture_model/manifest/generator.py, src/architecture_model/manifest/display.py, src/architecture_model/manifest/slicers.py

**Constants:**

- `ACTIVE` = `ACTIVE` (Status/FileStatus enum member)

**Signatures:**

- `generate_manifest(project_root: Path, config: Optional[Any]) --> Manifest`
- `load_or_generate_manifest(project_root: Path, output_dir: Path | None) --> dict[str, Any]`
- `print_summary(manifest: dict[str, Any]) --> None`
- `get_manifest_slice(manifest: Manifest | dict[str, Any], artifact_name: str) --> str`

**Test Contracts (21):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_generator_typed.py | test_generate_manifest_returns_manifest | result isinstance Manifest | type_check |
| test_generator_typed.py | test_generate_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_generator_typed.py | test_scan_report_tracks_counts | report.files_succeeded == report.files_attempted | value_equality |
| test_generator_typed.py | test_load_or_generate_returns_dict | result isinstance dict | type_check |
| test_manifest_types.py | test_module_info_creation | m.file == 'src/foo.py' | value_equality |
| test_manifest_types.py | test_module_status_values | ModuleStatus.ACTIVE.value == 'active' | value_equality |
| test_manifest_types.py | test_scan_report_success_rate | r.success_rate == 0.9 | value_equality |
| test_manifest_types.py | test_scan_report_empty | r.success_rate == 1.0 | value_equality |
| test_manifest_types.py | test_interface_edge_creation | e.source == 'a/b.py' | value_equality |
| test_manifest_types.py | test_manifest_creation | m.metrics.values['total_python_files'] == 10 | value_equality |
| test_manifest_types.py | test_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_manifest_types.py | test_module_info_to_dict | d['status'] == 'active' | value_equality |
| test_manifest_types.py | test_block_manifest_to_dict | d['name'] == 'Core' | value_equality |
| test_manifest_types.py | test_sub_function_entry_to_dict | d['id'] == 'F1.1' | value_equality |
| test_manifest.py | test_each_block_has_dirs | block_def['dirs'] isinstance list | type_check |
| test_manifest.py | test_each_block_has_files | block_def['files'] isinstance list | type_check |
| test_manifest.py | test_has_metrics | generated['metrics'] isinstance dict | type_check |
| test_manifest.py | test_functional_blocks_have_sub_functions | block['sub_functions'] isinstance list | type_check |
| test_manifest.py | test_has_modules | generated['modules'] isinstance list | type_check |
| test_manifest.py | test_has_interfaces | generated['interfaces'] isinstance list | type_check |
| test_manifest.py | test_returns_non_empty_markdown | result isinstance str | type_check |

#### COMP-MANIFEST-INTERFACES: manifest.interfaces

- **F-Block:** F5
- **Description:** Interface detection from public API surface
- **Files:** src/architecture_model/manifest/interfaces.py

**Constants:**

- `ACTIVE` = `ACTIVE` (Status/FileStatus enum member)

**Signatures:**

- `derive_interfaces(modules: list[ModuleInfo], root: Path) --> list[InterfaceEdge]`

**Test Contracts (20):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_interfaces_typed.py | test_derive_interfaces_returns_typed | result[0].source == 'pkg/a.py' | value_equality |
| test_interfaces_typed.py | test_derive_interfaces_no_self_reference | len(result) == 0 | value_equality |
| test_interfaces_typed.py | test_derive_interfaces_deduplicates | len(result) == 1 | value_equality |
| test_manifest_types.py | test_module_info_creation | m.file == 'src/foo.py' | value_equality |
| test_manifest_types.py | test_module_status_values | ModuleStatus.ACTIVE.value == 'active' | value_equality |
| test_manifest_types.py | test_scan_report_success_rate | r.success_rate == 0.9 | value_equality |
| test_manifest_types.py | test_scan_report_empty | r.success_rate == 1.0 | value_equality |
| test_manifest_types.py | test_interface_edge_creation | e.source == 'a/b.py' | value_equality |
| test_manifest_types.py | test_manifest_creation | m.metrics.values['total_python_files'] == 10 | value_equality |
| test_manifest_types.py | test_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_manifest_types.py | test_module_info_to_dict | d['status'] == 'active' | value_equality |
| test_manifest_types.py | test_block_manifest_to_dict | d['name'] == 'Core' | value_equality |
| test_manifest_types.py | test_sub_function_entry_to_dict | d['id'] == 'F1.1' | value_equality |
| test_manifest.py | test_each_block_has_dirs | block_def['dirs'] isinstance list | type_check |
| test_manifest.py | test_each_block_has_files | block_def['files'] isinstance list | type_check |
| test_manifest.py | test_has_metrics | generated['metrics'] isinstance dict | type_check |
| test_manifest.py | test_functional_blocks_have_sub_functions | block['sub_functions'] isinstance list | type_check |
| test_manifest.py | test_has_modules | generated['modules'] isinstance list | type_check |
| test_manifest.py | test_has_interfaces | generated['interfaces'] isinstance list | type_check |
| test_manifest.py | test_returns_non_empty_markdown | result isinstance str | type_check |

#### COMP-MANIFEST-METRICS: manifest.metrics

- **F-Block:** F5
- **Description:** Code metrics computation (LOC, complexity, etc.)
- **Files:** src/architecture_model/manifest/metrics.py

**Constants:**

- `ACTIVE` = `ACTIVE` (Status/FileStatus enum member)

**Signatures:**

- `compute_metrics(root: Path, config: Optional[Any]) --> MetricsResult`

**Test Contracts (19):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_metrics_typed.py | test_compute_metrics_returns_metrics_result | result isinstance MetricsResult | type_check |
| test_metrics_typed.py | test_compute_metrics_backward_compat | d isinstance dict | type_check |
| test_manifest_types.py | test_module_info_creation | m.file == 'src/foo.py' | value_equality |
| test_manifest_types.py | test_module_status_values | ModuleStatus.ACTIVE.value == 'active' | value_equality |
| test_manifest_types.py | test_scan_report_success_rate | r.success_rate == 0.9 | value_equality |
| test_manifest_types.py | test_scan_report_empty | r.success_rate == 1.0 | value_equality |
| test_manifest_types.py | test_interface_edge_creation | e.source == 'a/b.py' | value_equality |
| test_manifest_types.py | test_manifest_creation | m.metrics.values['total_python_files'] == 10 | value_equality |
| test_manifest_types.py | test_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_manifest_types.py | test_module_info_to_dict | d['status'] == 'active' | value_equality |
| test_manifest_types.py | test_block_manifest_to_dict | d['name'] == 'Core' | value_equality |
| test_manifest_types.py | test_sub_function_entry_to_dict | d['id'] == 'F1.1' | value_equality |
| test_manifest.py | test_each_block_has_dirs | block_def['dirs'] isinstance list | type_check |
| test_manifest.py | test_each_block_has_files | block_def['files'] isinstance list | type_check |
| test_manifest.py | test_has_metrics | generated['metrics'] isinstance dict | type_check |
| test_manifest.py | test_functional_blocks_have_sub_functions | block['sub_functions'] isinstance list | type_check |
| test_manifest.py | test_has_modules | generated['modules'] isinstance list | type_check |
| test_manifest.py | test_has_interfaces | generated['interfaces'] isinstance list | type_check |
| test_manifest.py | test_returns_non_empty_markdown | result isinstance str | type_check |

#### COMP-MANIFEST-SCANNER: manifest.scanner

- **F-Block:** F5
- **Description:** AST-based source code scanner
- **Files:** src/architecture_model/manifest/scanner.py

**Constants:**

- `ACTIVE` = `ACTIVE` (Status/FileStatus enum member)
- `MISSING` = `missing` (FileStatus enum member)

**Signatures:**

- `scan_file(root: Path, filepath: Path) --> ModuleInfo`

**Test Contracts (21):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_scanner_typed.py | test_scan_file_returns_module_info | result isinstance ModuleInfo | type_check |
| test_scanner_typed.py | test_scan_file_parse_error | result.status == ModuleStatus.MISSING | value_equality |
| test_scanner_typed.py | test_deprecated_scan_file_returns_dict | result isinstance dict | type_check |
| test_scanner_typed.py | test_deprecated_collect_py_files | len(files) == 2 | value_equality |
| test_manifest_types.py | test_module_info_creation | m.file == 'src/foo.py' | value_equality |
| test_manifest_types.py | test_module_status_values | ModuleStatus.ACTIVE.value == 'active' | value_equality |
| test_manifest_types.py | test_scan_report_success_rate | r.success_rate == 0.9 | value_equality |
| test_manifest_types.py | test_scan_report_empty | r.success_rate == 1.0 | value_equality |
| test_manifest_types.py | test_interface_edge_creation | e.source == 'a/b.py' | value_equality |
| test_manifest_types.py | test_manifest_creation | m.metrics.values['total_python_files'] == 10 | value_equality |
| test_manifest_types.py | test_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_manifest_types.py | test_module_info_to_dict | d['status'] == 'active' | value_equality |
| test_manifest_types.py | test_block_manifest_to_dict | d['name'] == 'Core' | value_equality |
| test_manifest_types.py | test_sub_function_entry_to_dict | d['id'] == 'F1.1' | value_equality |
| test_manifest.py | test_each_block_has_dirs | block_def['dirs'] isinstance list | type_check |
| test_manifest.py | test_each_block_has_files | block_def['files'] isinstance list | type_check |
| test_manifest.py | test_has_metrics | generated['metrics'] isinstance dict | type_check |
| test_manifest.py | test_functional_blocks_have_sub_functions | block['sub_functions'] isinstance list | type_check |
| test_manifest.py | test_has_modules | generated['modules'] isinstance list | type_check |
| test_manifest.py | test_has_interfaces | generated['interfaces'] isinstance list | type_check |
| test_manifest.py | test_returns_non_empty_markdown | result isinstance str | type_check |

#### COMP-MANIFEST-TEST-ANALYZER: manifest.test_analyzer

- **F-Block:** F5
- **Description:** Test contract extraction from test files
- **Files:** src/architecture_model/manifest/test_analyzer.py

**Constants:**

- `_EXCLUDED_MODULES` = `frozenset({'unittest', 'pytest', 'sys', 'os', 'io', 're', 'math', 'collections', 'itertools', 'functools', 'pathlib', 'typing', 'tempfile', 'shutil', 'json', 'copy', 'contextlib', 'textwrap', 'unittest.mock', 'mock'})`
- `_ESCAPE_CODE_RE` = `re.compile('\\\\(?:033|x1b)\\[(\\d+)m')`
- `ACTIVE` = `ACTIVE` (Status/FileStatus enum member)

**Signatures:**

- `analyze_test_file(test_file: Path) --> TestAnalysisResult`
- `extract_constants_from_contracts(contracts: list[TestContract]) --> list[Constant]`

**Test Contracts (24):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_test_analyzer.py | test_result_has_expected_fields | result isinstance TestAnalysisResult | type_check |
| test_test_analyzer.py | test_assertEqual_produces_test_contract | c isinstance TestContract | type_check |
| test_test_analyzer.py | test_test_count | result.test_count == 4 | value_equality |
| test_test_analyzer.py | test_constant_values_are_numeric_codes | black.value == '30' | value_equality |
| test_test_analyzer.py | test_extract_constants_from_contracts_standalone | len(constants) == 2 | value_equality |
| test_test_analyzer.py | test_fore_black_value | black.value == '30' | value_equality |
| test_test_analyzer.py | test_fore_reset_value | resets[0].value == '39' | value_equality |
| test_manifest_types.py | test_module_info_creation | m.file == 'src/foo.py' | value_equality |
| test_manifest_types.py | test_module_status_values | ModuleStatus.ACTIVE.value == 'active' | value_equality |
| test_manifest_types.py | test_scan_report_success_rate | r.success_rate == 0.9 | value_equality |
| test_manifest_types.py | test_scan_report_empty | r.success_rate == 1.0 | value_equality |
| test_manifest_types.py | test_interface_edge_creation | e.source == 'a/b.py' | value_equality |
| test_manifest_types.py | test_manifest_creation | m.metrics.values['total_python_files'] == 10 | value_equality |
| test_manifest_types.py | test_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_manifest_types.py | test_module_info_to_dict | d['status'] == 'active' | value_equality |
| test_manifest_types.py | test_block_manifest_to_dict | d['name'] == 'Core' | value_equality |
| test_manifest_types.py | test_sub_function_entry_to_dict | d['id'] == 'F1.1' | value_equality |
| test_manifest.py | test_each_block_has_dirs | block_def['dirs'] isinstance list | type_check |
| test_manifest.py | test_each_block_has_files | block_def['files'] isinstance list | type_check |
| test_manifest.py | test_has_metrics | generated['metrics'] isinstance dict | type_check |
| test_manifest.py | test_functional_blocks_have_sub_functions | block['sub_functions'] isinstance list | type_check |
| test_manifest.py | test_has_modules | generated['modules'] isinstance list | type_check |
| test_manifest.py | test_has_interfaces | generated['interfaces'] isinstance list | type_check |
| test_manifest.py | test_returns_non_empty_markdown | result isinstance str | type_check |

#### COMP-MANIFEST-TYPES: manifest.types

- **F-Block:** F5
- **Description:** Manifest data types (Manifest, ModuleInfo, FunctionalBlock)
- **Files:** src/architecture_model/manifest/types.py

**Constants:**

- `ACTIVE` = `ACTIVE` (Status/FileStatus enum member)

**Signatures:**

- `to_dict() --> dict[str, Any]`
- `success_rate() --> float` @property
- `log_summary() --> None`

**Test Contracts (17):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_manifest_types.py | test_module_info_creation | m.file == 'src/foo.py' | value_equality |
| test_manifest_types.py | test_module_status_values | ModuleStatus.ACTIVE.value == 'active' | value_equality |
| test_manifest_types.py | test_scan_report_success_rate | r.success_rate == 0.9 | value_equality |
| test_manifest_types.py | test_scan_report_empty | r.success_rate == 1.0 | value_equality |
| test_manifest_types.py | test_interface_edge_creation | e.source == 'a/b.py' | value_equality |
| test_manifest_types.py | test_manifest_creation | m.metrics.values['total_python_files'] == 10 | value_equality |
| test_manifest_types.py | test_manifest_to_dict_backward_compat | d['metrics'] isinstance dict | type_check |
| test_manifest_types.py | test_module_info_to_dict | d['status'] == 'active' | value_equality |
| test_manifest_types.py | test_block_manifest_to_dict | d['name'] == 'Core' | value_equality |
| test_manifest_types.py | test_sub_function_entry_to_dict | d['id'] == 'F1.1' | value_equality |
| test_manifest.py | test_each_block_has_dirs | block_def['dirs'] isinstance list | type_check |
| test_manifest.py | test_each_block_has_files | block_def['files'] isinstance list | type_check |
| test_manifest.py | test_has_metrics | generated['metrics'] isinstance dict | type_check |
| test_manifest.py | test_functional_blocks_have_sub_functions | block['sub_functions'] isinstance list | type_check |
| test_manifest.py | test_has_modules | generated['modules'] isinstance list | type_check |
| test_manifest.py | test_has_interfaces | generated['interfaces'] isinstance list | type_check |
| test_manifest.py | test_returns_non_empty_markdown | result isinstance str | type_check |

#### COMP-PROFILES: profiles

- **F-Block:** F7
- **Description:** Domain profile system (software, controls, mechanical, electrical)
- **Files:** src/architecture_model/profiles/schema.py, src/architecture_model/profiles/__init__.py, src/architecture_model/profiles/builtins/__init__.py

**Constants:**

- `PROFILES_DIR` = `Path(__file__).parent / 'builtins'`

**Signatures:**

- `from_dict(data: dict[str, Any]) --> DomainProfile` @classmethod
- `get_extended_values(enum_name: str) --> list[str]`
- `load_profile(name_or_path: str) --> DomainProfile`

#### COMP-SPEC: spec

- **F-Block:** F8
- **Description:** JSON Schema definitions for architecture model validation
- **Files:** src/architecture_model/spec/__init__.py

#### COMP-UTILS: utils

- **F-Block:** F9
- **Description:** File discovery, exclusion patterns, and shared helper functions
- **Files:** src/architecture_model/utils/discovery.py, src/architecture_model/utils/__init__.py

**Signatures:**

- `is_excluded_dir(path: Path) --> bool`
- `collect_py_files(directory: Path, recursive: bool, exclude_init: bool) --> list[Path]`
- `discover_source_files(project_root: Path) --> list[Path]`
- `discover_test_files(project_root: Path) --> list[Path]`

**Test Contracts (7):**

| Test File | Method | Assertion | Type |
|-----------|--------|-----------|------|
| test_discovery.py | test_collect_py_files_excludes_pycache | len(result) == 1 | value_equality |
| test_discovery.py | test_collect_py_files_recursive | len(result) == 2 | value_equality |
| test_discovery.py | test_collect_py_files_non_recursive | len(result) == 1 | value_equality |
| test_discovery.py | test_collect_py_files_exclude_init | len(result) == 1 | value_equality |
| test_discovery.py | test_collect_py_files_nonexistent_dir | result == [] | value_equality |
| test_discovery.py | test_discover_test_files | len(result) == 2 | value_equality |
| test_discovery.py | test_discover_test_files_by_name | len(result) == 2 | value_equality |

### Relationships

| Type | From | To |
|------|------|-----|
| contains | L-APP | COMP-CORE |
| contains | L-APP | COMP-MANIFEST |
| contains | L-APP | COMP-CLI |
| contains | L-APP | COMP-CONFIG |
| contains | L-APP | COMP-SPEC |
| contains | L-APP | COMP-EXTRACT |
| contains | L-APP | COMP-PROFILES |
| contains | L-APP | COMP-UTILS |
| contains | L-APP | COMP-ENRICH |
| contains | COMP-CORE | COMP-CORE-PARSER |
| contains | COMP-CORE | COMP-CORE-VALIDATOR |
| contains | COMP-CORE | COMP-CORE-SLICER |
| contains | COMP-CORE | COMP-CORE-DIFFER |
| contains | COMP-CORE | COMP-CORE-MERGER |
| contains | COMP-CORE | COMP-CORE-DECOMPOSER |
| contains | COMP-CORE | COMP-CORE-TYPES |
| contains | COMP-MANIFEST | COMP-MANIFEST-SCANNER |
| contains | COMP-MANIFEST | COMP-MANIFEST-BLOCKS |
| contains | COMP-MANIFEST | COMP-MANIFEST-METRICS |
| contains | COMP-MANIFEST | COMP-MANIFEST-INTERFACES |
| contains | COMP-MANIFEST | COMP-MANIFEST-BODY-HINTS |
| contains | COMP-MANIFEST | COMP-MANIFEST-TEST-ANALYZER |
| contains | COMP-MANIFEST | COMP-MANIFEST-GENERATOR |
| contains | COMP-MANIFEST | COMP-MANIFEST-TYPES |
| realizes | COMP-CORE | CAP-F1 |
| realizes | COMP-CORE | CAP-F3 |
| realizes | COMP-MANIFEST | CAP-F2 |
| realizes | COMP-CLI | CAP-F4 |
| realizes | COMP-CONFIG | CAP-F5 |
| realizes | COMP-SPEC | CAP-F6 |
| realizes | COMP-EXTRACT | CAP-F7 |
| realizes | COMP-PROFILES | CAP-F8 |
| realizes | COMP-UTILS | CAP-F9 |
| realizes | COMP-ENRICH | CAP-F10 |
| exposes | COMP-CLI | IF-CLI |
| exposes | COMP-CORE-PARSER | IF-PARSE-API |
| exposes | COMP-CORE-VALIDATOR | IF-VALIDATE-API |
| exposes | COMP-CORE-SLICER | IF-SLICER-API |
| exposes | COMP-MANIFEST-GENERATOR | IF-MANIFEST-API |
| exposes | COMP-PROFILES | IF-PROFILE-API |
| exposes | COMP-ENRICH | IF-ENRICH-API |
| constrained-by | COMP-CORE | CON-SCHEMA |
| constrained-by | COMP-SPEC | CON-SCHEMA |
| constrained-by | COMP-CORE | CON-NO-ORPHANS |
| depends-on | COMP-CLI | COMP-CORE |
| depends-on | COMP-CLI | COMP-CONFIG |
| depends-on | COMP-CLI | COMP-MANIFEST |
| depends-on | COMP-CLI | COMP-ENRICH |
| depends-on | COMP-CORE | COMP-CONFIG |
| depends-on | COMP-CORE | COMP-SPEC |
| depends-on | COMP-CORE | COMP-PROFILES |
| depends-on | COMP-MANIFEST | COMP-CONFIG |
| depends-on | COMP-MANIFEST | COMP-UTILS |
| depends-on | COMP-EXTRACT | COMP-CORE |
| depends-on | COMP-ENRICH | COMP-CORE |
| depends-on | COMP-ENRICH | COMP-MANIFEST |
| depends-on | COMP-CORE-PARSER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-VALIDATOR | COMP-CORE-TYPES |
| depends-on | COMP-CORE-VALIDATOR | COMP-PROFILES |
| depends-on | COMP-CORE-SLICER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-DIFFER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-MERGER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-MERGER | COMP-UTILS |
| depends-on | COMP-CORE-DECOMPOSER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-DECOMPOSER | COMP-UTILS |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-SCANNER |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-BLOCKS |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-METRICS |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-INTERFACES |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-BLOCKS | COMP-MANIFEST-SCANNER |
| depends-on | COMP-MANIFEST-BLOCKS | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-BLOCKS | COMP-UTILS |
| depends-on | COMP-MANIFEST-SCANNER | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-METRICS | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-INTERFACES | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-BODY-HINTS | COMP-CORE-TYPES |
| depends-on | COMP-MANIFEST-TEST-ANALYZER | COMP-CORE-TYPES |
| traces-to | COMP-CLI | BEH-INIT |
| traces-to | COMP-CLI | BEH-VALIDATE |
| traces-to | COMP-CLI | BEH-MANIFEST |
| traces-to | COMP-CLI | BEH-ENRICH |
| traces-to | COMP-CORE-PARSER | BEH-VALIDATE |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST |
| traces-to | COMP-ENRICH | BEH-ENRICH |
| traces-to | COMP-EXTRACT | BEH-EXTRACT |
| consumes | ACT-DEV | IF-CLI |
| consumes | ACT-LLM | IF-PARSE-API |
| consumes | ACT-LLM | IF-SLICER-API |
| consumes | ACT-LLM | IF-MANIFEST-API |
| depends-on | COMP-DECOMPOSE | COMP-CORE |
| depends-on | COMP-DECOMPOSE | COMP-CONFIG |
| traces-to | COMP-CLI | BEH-SLICE |
| traces-to | COMP-CLI | BEH-DIFF |
| traces-to | COMP-CORE-MERGER | BEH-MERGE |
| traces-to | COMP-CLI | BEH-DECOMPOSE |
| contains | BEH-VALIDATE | BEH-VALIDATE-IDS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-IDS |
| contains | BEH-VALIDATE | BEH-VALIDATE-REFS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-REFS |
| contains | BEH-VALIDATE | BEH-VALIDATE-ORPHANS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-ORPHANS |
| contains | BEH-VALIDATE | BEH-VALIDATE-STATUS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-STATUS |
| contains | BEH-VALIDATE | BEH-VALIDATE-CAPS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-CAPS |
| contains | BEH-VALIDATE | BEH-VALIDATE-META |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-META |
| contains | BEH-VALIDATE | BEH-VALIDATE-V11 |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-V11 |
| contains | BEH-VALIDATE | BEH-VALIDATE-REGEN |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-REGEN |
| contains | BEH-VALIDATE | BEH-VALIDATE-PROFILE |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-PROFILE |
| contains | BEH-VALIDATE | BEH-VALIDATE-IMPROVE |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-IMPROVE |
| contains | BEH-VALIDATE | BEH-PARSE-LOAD |
| traces-to | COMP-CORE-PARSER | BEH-PARSE-LOAD |
| contains | BEH-VALIDATE | BEH-PARSE-SAVE |
| traces-to | COMP-CORE-PARSER | BEH-PARSE-SAVE |
| contains | BEH-VALIDATE | BEH-PARSE-DUMP |
| traces-to | COMP-CORE-PARSER | BEH-PARSE-DUMP |
| contains | BEH-SLICE | BEH-SLICE-FBLOCK |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-FBLOCK |
| contains | BEH-SLICE | BEH-SLICE-LAYER |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-LAYER |
| contains | BEH-SLICE | BEH-SLICE-STATUS |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-STATUS |
| contains | BEH-SLICE | BEH-SLICE-ARTIFACT |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-ARTIFACT |
| contains | BEH-SLICE | BEH-SLICE-COMPONENT |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-COMPONENT |
| contains | BEH-DIFF | BEH-DIFF-ENTITIES |
| traces-to | COMP-CORE-DIFFER | BEH-DIFF-ENTITIES |
| contains | BEH-DIFF | BEH-DIFF-RELS |
| traces-to | COMP-CORE-DIFFER | BEH-DIFF-RELS |
| contains | BEH-MERGE | BEH-MERGE-MANIFEST |
| traces-to | COMP-CORE-MERGER | BEH-MERGE-MANIFEST |
| contains | BEH-MERGE | BEH-MERGE-ENRICH |
| traces-to | COMP-CORE-MERGER | BEH-MERGE-ENRICH |
| contains | BEH-MERGE | BEH-MERGE-COMPACT |
| traces-to | COMP-CORE-MERGER | BEH-MERGE-COMPACT |
| contains | BEH-MERGE | BEH-MERGE-COMPOSE |
| traces-to | COMP-CORE-MERGER | BEH-MERGE-COMPOSE |
| contains | BEH-DECOMPOSE | BEH-DECOMPOSE-IDENTIFY |
| traces-to | COMP-CORE-DECOMPOSER | BEH-DECOMPOSE-IDENTIFY |
| contains | BEH-DECOMPOSE | BEH-DECOMPOSE-COMPLEXITY |
| traces-to | COMP-CORE-DECOMPOSER | BEH-DECOMPOSE-COMPLEXITY |
| contains | BEH-DECOMPOSE | BEH-DECOMPOSE-PARTITION |
| traces-to | COMP-CORE-DECOMPOSER | BEH-DECOMPOSE-PARTITION |
| contains | BEH-MANIFEST | BEH-SCAN-PARSE |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-PARSE |
| contains | BEH-MANIFEST | BEH-SCAN-FUNCTIONS |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-FUNCTIONS |
| contains | BEH-MANIFEST | BEH-SCAN-CLASSES |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-CLASSES |
| contains | BEH-MANIFEST | BEH-SCAN-IMPORTS |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-IMPORTS |
| contains | BEH-MANIFEST | BEH-SCAN-CONSTANTS |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-CONSTANTS |
| contains | BEH-MANIFEST | BEH-SCAN-METRICS |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-METRICS |
| contains | BEH-MANIFEST | BEH-MANIFEST-CONFIG |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-CONFIG |
| contains | BEH-MANIFEST | BEH-MANIFEST-METRICS |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-METRICS |
| contains | BEH-MANIFEST | BEH-MANIFEST-BLOCKS |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-BLOCKS |
| contains | BEH-MANIFEST | BEH-MANIFEST-SCAN |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-SCAN |
| contains | BEH-MANIFEST | BEH-MANIFEST-IFACE |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-IFACE |
| contains | BEH-MANIFEST | BEH-MANIFEST-ASSEMBLE |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-ASSEMBLE |
| contains | BEH-MANIFEST | BEH-BODYHINT-CLASSIFY |
| traces-to | COMP-MANIFEST-BODY-HINTS | BEH-BODYHINT-CLASSIFY |
| contains | BEH-MANIFEST | BEH-BODYHINT-SUMMARIZE |
| traces-to | COMP-MANIFEST-BODY-HINTS | BEH-BODYHINT-SUMMARIZE |
| contains | BEH-MANIFEST | BEH-TEST-DISCOVER |
| traces-to | COMP-MANIFEST-TEST-ANALYZER | BEH-TEST-DISCOVER |
| contains | BEH-MANIFEST | BEH-TEST-ASSERTIONS |
| traces-to | COMP-MANIFEST-TEST-ANALYZER | BEH-TEST-ASSERTIONS |
| contains | BEH-MANIFEST | BEH-IFACE-RESOLVE |
| traces-to | COMP-MANIFEST-INTERFACES | BEH-IFACE-RESOLVE |
| contains | BEH-MANIFEST | BEH-IFACE-DEDUP |
| traces-to | COMP-MANIFEST-INTERFACES | BEH-IFACE-DEDUP |
| contains | BEH-MANIFEST | BEH-RECURSIVE-SCAN |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-RECURSIVE-SCAN |
| contains | BEH-MANIFEST | BEH-RECURSIVE-DEPS |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-RECURSIVE-DEPS |
| contains | BEH-ENRICH | BEH-ENRICH-SIGS |
| traces-to | COMP-ENRICH | BEH-ENRICH-SIGS |
| contains | BEH-ENRICH | BEH-ENRICH-CONSTS |
| traces-to | COMP-ENRICH | BEH-ENRICH-CONSTS |
| contains | BEH-ENRICH | BEH-ENRICH-TESTS |
| traces-to | COMP-ENRICH | BEH-ENRICH-TESTS |
| contains | BEH-DECOMPOSE | BEH-ORCH-FIND-COMPS |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-FIND-COMPS |
| contains | BEH-DECOMPOSE | BEH-ORCH-FIND-PARENT |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-FIND-PARENT |
| contains | BEH-DECOMPOSE | BEH-ORCH-TRACE |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-TRACE |
| contains | BEH-DECOMPOSE | BEH-ORCH-COLLECT-RELS |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-COLLECT-RELS |
| contains | BEH-DECOMPOSE | BEH-ORCH-BUILD |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-BUILD |
| contains | BEH-EXTRACT | BEH-EXTRACT-CAPS |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-CAPS |
| contains | BEH-EXTRACT | BEH-EXTRACT-ACTORS |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-ACTORS |
| contains | BEH-EXTRACT | BEH-EXTRACT-COMPS |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-COMPS |
| contains | BEH-EXTRACT | BEH-EXTRACT-IFACES |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-IFACES |
| contains | BEH-EXTRACT | BEH-EXTRACT-RELS |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-RELS |
| contains | BEH-INIT | BEH-CLI-SLICE |
| traces-to | COMP-CLI | BEH-CLI-SLICE |
| contains | BEH-INIT | BEH-CLI-DIFF |
| traces-to | COMP-CLI | BEH-CLI-DIFF |
| contains | BEH-INIT | BEH-CLI-STATS |
| traces-to | COMP-CLI | BEH-CLI-STATS |
| contains | BEH-INIT | BEH-CLI-IMPACT |
| traces-to | COMP-CLI | BEH-CLI-IMPACT |
| contains | BEH-INIT | BEH-CLI-DECOMPOSE |
| traces-to | COMP-CLI | BEH-CLI-DECOMPOSE |
| contains | BEH-INIT | BEH-CLI-COVERAGE |
| traces-to | COMP-CLI | BEH-CLI-COVERAGE |
| contains | BEH-VALIDATE | BEH-PROFILE-LOAD |
| traces-to | COMP-PROFILES | BEH-PROFILE-LOAD |
| contains | BEH-VALIDATE | BEH-PROFILE-APPLY |
| traces-to | COMP-PROFILES | BEH-PROFILE-APPLY |
| contains | BEH-MANIFEST | BEH-UTILS-DISCOVER |
| traces-to | COMP-UTILS | BEH-UTILS-DISCOVER |
| contains | BEH-MANIFEST | BEH-UTILS-TESTS |
| traces-to | COMP-UTILS | BEH-UTILS-TESTS |

\newpage

## Sub-Model F1: Cli

- **Validation Score:** 90/100
- **Refines:** COMP-CLI
- **Components:** 1
- **Capabilities:** 1
- **Interfaces:** 1
- **Behaviors:** 13
- **Constraints:** 0
- **Relationships:** 25

**Capabilities:**

- CAP-F4: CLI Operations (F-Block F1)

**Interfaces:**

- IF-CLI: CLI Interface

**Behaviors:**

- BEH-INIT: Project Initialization
- BEH-VALIDATE: Model Validation
- BEH-MANIFEST: Manifest Generation
- BEH-ENRICH: Auto-Enrichment
- BEH-SLICE: Model Slicing
- BEH-DIFF: Model Diffing
- BEH-DECOMPOSE: Model Decomposition
- BEH-CLI-SLICE: CLI Slice Command
- BEH-CLI-DIFF: CLI Diff Command
- BEH-CLI-STATS: CLI Stats Command
- BEH-CLI-IMPACT: CLI Impact Command
- BEH-CLI-DECOMPOSE: CLI Decompose Command
- BEH-CLI-COVERAGE: CLI Coverage Command

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-CLI | cli | 1 | 0 | 0 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| realizes | COMP-CLI | CAP-F4 |
| exposes | COMP-CLI | IF-CLI |
| depends-on | COMP-CLI | COMP-CORE |
| depends-on | COMP-CLI | COMP-CONFIG |
| depends-on | COMP-CLI | COMP-MANIFEST |
| depends-on | COMP-CLI | COMP-ENRICH |
| traces-to | COMP-CLI | BEH-INIT |
| traces-to | COMP-CLI | BEH-VALIDATE |
| traces-to | COMP-CLI | BEH-MANIFEST |
| traces-to | COMP-CLI | BEH-ENRICH |
| traces-to | COMP-CLI | BEH-SLICE |
| traces-to | COMP-CLI | BEH-DIFF |
| traces-to | COMP-CLI | BEH-DECOMPOSE |
| contains | BEH-INIT | BEH-CLI-SLICE |
| traces-to | COMP-CLI | BEH-CLI-SLICE |
| contains | BEH-INIT | BEH-CLI-DIFF |
| traces-to | COMP-CLI | BEH-CLI-DIFF |
| contains | BEH-INIT | BEH-CLI-STATS |
| traces-to | COMP-CLI | BEH-CLI-STATS |
| contains | BEH-INIT | BEH-CLI-IMPACT |
| traces-to | COMP-CLI | BEH-CLI-IMPACT |
| contains | BEH-INIT | BEH-CLI-DECOMPOSE |
| traces-to | COMP-CLI | BEH-CLI-DECOMPOSE |
| contains | BEH-INIT | BEH-CLI-COVERAGE |
| traces-to | COMP-CLI | BEH-CLI-COVERAGE |

\newpage

## Sub-Model F2: Config

- **Validation Score:** 90/100
- **Refines:** COMP-CONFIG
- **Components:** 1
- **Capabilities:** 1
- **Interfaces:** 0
- **Behaviors:** 0
- **Constraints:** 0
- **Relationships:** 5

**Capabilities:**

- CAP-F5: Configuration Management (F-Block F2)

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-CONFIG | config | 15 | 1 | 1 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| realizes | COMP-CONFIG | CAP-F5 |
| depends-on | COMP-CLI | COMP-CONFIG |
| depends-on | COMP-CORE | COMP-CONFIG |
| depends-on | COMP-MANIFEST | COMP-CONFIG |
| depends-on | COMP-DECOMPOSE | COMP-CONFIG |

\newpage

## Sub-Model F3: Core

- **Validation Score:** 74/100
- **Refines:** COMP-CORE
- **Components:** 8
- **Capabilities:** 2
- **Interfaces:** 3
- **Behaviors:** 29
- **Constraints:** 2
- **Relationships:** 79

**Capabilities:**

- CAP-F1: Model Parsing & Validation (F-Block F3)
- CAP-F3: Model Slicing & Diffing (F-Block F3)

**Interfaces:**

- IF-PARSE-API: Parser API
- IF-VALIDATE-API: Validator API
- IF-SLICER-API: Slicer API

**Behaviors:**

- BEH-VALIDATE: Model Validation
- BEH-MERGE: Model Merging
- BEH-VALIDATE-IDS: ID Uniqueness Check
- BEH-VALIDATE-REFS: Referential Integrity Check
- BEH-VALIDATE-ORPHANS: Orphan Entity Detection
- BEH-VALIDATE-STATUS: Status Consistency Check
- BEH-VALIDATE-CAPS: Capability Realization Check
- BEH-VALIDATE-META: Meta Completeness Check
- BEH-VALIDATE-V11: V1.1 Semantics Check
- BEH-VALIDATE-REGEN: Regen Readiness Check
- BEH-VALIDATE-PROFILE: Domain Profile Validation
- BEH-VALIDATE-IMPROVE: Improvement Opportunities
- BEH-PARSE-LOAD: Model Loading
- BEH-PARSE-SAVE: Model Saving
- BEH-PARSE-DUMP: Model Dumping
- BEH-SLICE-FBLOCK: Slice by F-Block
- BEH-SLICE-LAYER: Slice by Layer
- BEH-SLICE-STATUS: Slice by Status
- BEH-SLICE-ARTIFACT: Slice by Artifact
- BEH-SLICE-COMPONENT: Slice by Component
- BEH-DIFF-ENTITIES: Entity Diff
- BEH-DIFF-RELS: Relationship Diff
- BEH-MERGE-MANIFEST: Merge Manifest
- BEH-MERGE-ENRICH: Enrich from Manifest
- BEH-MERGE-COMPACT: Compact for Generation
- BEH-MERGE-COMPOSE: Compose Enriched Model
- BEH-DECOMPOSE-IDENTIFY: Identify Systems
- BEH-DECOMPOSE-COMPLEXITY: Compute Complexity
- BEH-DECOMPOSE-PARTITION: Partition Subsystems

**Constraints:**

- CON-SCHEMA: Schema Compliance
- CON-NO-ORPHANS: No Orphaned Entities

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-CORE | core | 0 | 0 | 0 |
| COMP-CORE-PARSER | core.parser | 4 | 1 | 11 |
| COMP-CORE-VALIDATOR | core.validator | 7 | 2 | 11 |
| COMP-CORE-SLICER | core.slicer | 4 | 1 | 12 |
| COMP-CORE-DIFFER | core.differ | 8 | 0 | 0 |
| COMP-CORE-MERGER | core.merger | 8 | 5 | 2 |
| COMP-CORE-DECOMPOSER | core.decomposer | 5 | 1 | 15 |
| COMP-CORE-TYPES | core.types | 6 | 0 | 30 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| contains | COMP-CORE | COMP-CORE-PARSER |
| contains | COMP-CORE | COMP-CORE-VALIDATOR |
| contains | COMP-CORE | COMP-CORE-SLICER |
| contains | COMP-CORE | COMP-CORE-DIFFER |
| contains | COMP-CORE | COMP-CORE-MERGER |
| contains | COMP-CORE | COMP-CORE-DECOMPOSER |
| contains | COMP-CORE | COMP-CORE-TYPES |
| realizes | COMP-CORE | CAP-F1 |
| realizes | COMP-CORE | CAP-F3 |
| exposes | COMP-CORE-PARSER | IF-PARSE-API |
| exposes | COMP-CORE-VALIDATOR | IF-VALIDATE-API |
| exposes | COMP-CORE-SLICER | IF-SLICER-API |
| constrained-by | COMP-CORE | CON-SCHEMA |
| constrained-by | COMP-CORE | CON-NO-ORPHANS |
| depends-on | COMP-CLI | COMP-CORE |
| depends-on | COMP-CORE | COMP-CONFIG |
| depends-on | COMP-CORE | COMP-SPEC |
| depends-on | COMP-CORE | COMP-PROFILES |
| depends-on | COMP-EXTRACT | COMP-CORE |
| depends-on | COMP-ENRICH | COMP-CORE |
| depends-on | COMP-CORE-PARSER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-VALIDATOR | COMP-CORE-TYPES |
| depends-on | COMP-CORE-VALIDATOR | COMP-PROFILES |
| depends-on | COMP-CORE-SLICER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-DIFFER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-MERGER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-MERGER | COMP-UTILS |
| depends-on | COMP-CORE-DECOMPOSER | COMP-CORE-TYPES |
| depends-on | COMP-CORE-DECOMPOSER | COMP-UTILS |
| depends-on | COMP-MANIFEST-BODY-HINTS | COMP-CORE-TYPES |
| depends-on | COMP-MANIFEST-TEST-ANALYZER | COMP-CORE-TYPES |
| traces-to | COMP-CORE-PARSER | BEH-VALIDATE |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE |
| depends-on | COMP-DECOMPOSE | COMP-CORE |
| traces-to | COMP-CORE-MERGER | BEH-MERGE |
| contains | BEH-VALIDATE | BEH-VALIDATE-IDS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-IDS |
| contains | BEH-VALIDATE | BEH-VALIDATE-REFS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-REFS |
| contains | BEH-VALIDATE | BEH-VALIDATE-ORPHANS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-ORPHANS |
| contains | BEH-VALIDATE | BEH-VALIDATE-STATUS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-STATUS |
| contains | BEH-VALIDATE | BEH-VALIDATE-CAPS |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-CAPS |
| contains | BEH-VALIDATE | BEH-VALIDATE-META |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-META |
| contains | BEH-VALIDATE | BEH-VALIDATE-V11 |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-V11 |
| contains | BEH-VALIDATE | BEH-VALIDATE-REGEN |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-REGEN |
| contains | BEH-VALIDATE | BEH-VALIDATE-PROFILE |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-PROFILE |
| contains | BEH-VALIDATE | BEH-VALIDATE-IMPROVE |
| traces-to | COMP-CORE-VALIDATOR | BEH-VALIDATE-IMPROVE |
| contains | BEH-VALIDATE | BEH-PARSE-LOAD |
| traces-to | COMP-CORE-PARSER | BEH-PARSE-LOAD |
| contains | BEH-VALIDATE | BEH-PARSE-SAVE |
| traces-to | COMP-CORE-PARSER | BEH-PARSE-SAVE |
| contains | BEH-VALIDATE | BEH-PARSE-DUMP |
| traces-to | COMP-CORE-PARSER | BEH-PARSE-DUMP |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-FBLOCK |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-LAYER |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-STATUS |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-ARTIFACT |
| traces-to | COMP-CORE-SLICER | BEH-SLICE-COMPONENT |
| traces-to | COMP-CORE-DIFFER | BEH-DIFF-ENTITIES |
| traces-to | COMP-CORE-DIFFER | BEH-DIFF-RELS |
| contains | BEH-MERGE | BEH-MERGE-MANIFEST |
| traces-to | COMP-CORE-MERGER | BEH-MERGE-MANIFEST |
| contains | BEH-MERGE | BEH-MERGE-ENRICH |
| traces-to | COMP-CORE-MERGER | BEH-MERGE-ENRICH |
| contains | BEH-MERGE | BEH-MERGE-COMPACT |
| traces-to | COMP-CORE-MERGER | BEH-MERGE-COMPACT |
| contains | BEH-MERGE | BEH-MERGE-COMPOSE |
| traces-to | COMP-CORE-MERGER | BEH-MERGE-COMPOSE |
| traces-to | COMP-CORE-DECOMPOSER | BEH-DECOMPOSE-IDENTIFY |
| traces-to | COMP-CORE-DECOMPOSER | BEH-DECOMPOSE-COMPLEXITY |
| traces-to | COMP-CORE-DECOMPOSER | BEH-DECOMPOSE-PARTITION |

\newpage

## Sub-Model F4: Extract

- **Validation Score:** 96/100
- **Refines:** COMP-EXTRACT
- **Components:** 1
- **Capabilities:** 1
- **Interfaces:** 0
- **Behaviors:** 6
- **Constraints:** 0
- **Relationships:** 13

**Capabilities:**

- CAP-F7: Model Extraction (F-Block F4)

**Behaviors:**

- BEH-EXTRACT: Model Extraction from Code
- BEH-EXTRACT-CAPS: Extract Capabilities
- BEH-EXTRACT-ACTORS: Extract Actors
- BEH-EXTRACT-COMPS: Extract Components
- BEH-EXTRACT-IFACES: Extract Interfaces
- BEH-EXTRACT-RELS: Extract Relationships

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-EXTRACT | extract | 1 | 0 | 0 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| realizes | COMP-EXTRACT | CAP-F7 |
| depends-on | COMP-EXTRACT | COMP-CORE |
| traces-to | COMP-EXTRACT | BEH-EXTRACT |
| contains | BEH-EXTRACT | BEH-EXTRACT-CAPS |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-CAPS |
| contains | BEH-EXTRACT | BEH-EXTRACT-ACTORS |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-ACTORS |
| contains | BEH-EXTRACT | BEH-EXTRACT-COMPS |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-COMPS |
| contains | BEH-EXTRACT | BEH-EXTRACT-IFACES |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-IFACES |
| contains | BEH-EXTRACT | BEH-EXTRACT-RELS |
| traces-to | COMP-EXTRACT | BEH-EXTRACT-RELS |

\newpage

## Sub-Model F5: Manifest

- **Validation Score:** 84/100
- **Refines:** COMP-MANIFEST
- **Components:** 9
- **Capabilities:** 1
- **Interfaces:** 1
- **Behaviors:** 21
- **Constraints:** 0
- **Relationships:** 68

**Capabilities:**

- CAP-F2: Reality Manifest Generation (F-Block F5)

**Interfaces:**

- IF-MANIFEST-API: Manifest API

**Behaviors:**

- BEH-MANIFEST: Manifest Generation
- BEH-SCAN-PARSE: AST Parsing
- BEH-SCAN-FUNCTIONS: Function Extraction
- BEH-SCAN-CLASSES: Class Extraction
- BEH-SCAN-IMPORTS: Import Extraction
- BEH-SCAN-CONSTANTS: Constant Extraction
- BEH-SCAN-METRICS: Metrics Computation
- BEH-MANIFEST-CONFIG: Config Loading
- BEH-MANIFEST-METRICS: Project Metrics
- BEH-MANIFEST-BLOCKS: Block Assembly
- BEH-MANIFEST-SCAN: Block Scanning
- BEH-MANIFEST-IFACE: Interface Discovery
- BEH-MANIFEST-ASSEMBLE: Manifest Assembly
- BEH-BODYHINT-CLASSIFY: Complexity Classification
- BEH-BODYHINT-SUMMARIZE: Body Summarization
- BEH-TEST-DISCOVER: Test Method Discovery
- BEH-TEST-ASSERTIONS: Assertion Pattern Matching
- BEH-IFACE-RESOLVE: Import Resolution
- BEH-IFACE-DEDUP: Interface Deduplication
- BEH-RECURSIVE-SCAN: Per-Block Deep Scan
- BEH-RECURSIVE-DEPS: Cross-Block Dependencies

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-MANIFEST | manifest | 0 | 0 | 0 |
| COMP-MANIFEST-SCANNER | manifest.scanner | 1 | 2 | 21 |
| COMP-MANIFEST-BLOCKS | manifest.blocks | 1 | 1 | 21 |
| COMP-MANIFEST-METRICS | manifest.metrics | 1 | 1 | 19 |
| COMP-MANIFEST-INTERFACES | manifest.interfaces | 1 | 1 | 20 |
| COMP-MANIFEST-BODY-HINTS | manifest.body_hints | 3 | 4 | 29 |
| COMP-MANIFEST-TEST-ANALYZER | manifest.test_analyzer | 2 | 3 | 24 |
| COMP-MANIFEST-GENERATOR | manifest.generator | 4 | 1 | 21 |
| COMP-MANIFEST-TYPES | manifest.types | 3 | 1 | 17 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| contains | COMP-MANIFEST | COMP-MANIFEST-SCANNER |
| contains | COMP-MANIFEST | COMP-MANIFEST-BLOCKS |
| contains | COMP-MANIFEST | COMP-MANIFEST-METRICS |
| contains | COMP-MANIFEST | COMP-MANIFEST-INTERFACES |
| contains | COMP-MANIFEST | COMP-MANIFEST-BODY-HINTS |
| contains | COMP-MANIFEST | COMP-MANIFEST-TEST-ANALYZER |
| contains | COMP-MANIFEST | COMP-MANIFEST-GENERATOR |
| contains | COMP-MANIFEST | COMP-MANIFEST-TYPES |
| realizes | COMP-MANIFEST | CAP-F2 |
| exposes | COMP-MANIFEST-GENERATOR | IF-MANIFEST-API |
| depends-on | COMP-CLI | COMP-MANIFEST |
| depends-on | COMP-MANIFEST | COMP-CONFIG |
| depends-on | COMP-MANIFEST | COMP-UTILS |
| depends-on | COMP-ENRICH | COMP-MANIFEST |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-SCANNER |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-BLOCKS |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-METRICS |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-INTERFACES |
| depends-on | COMP-MANIFEST-GENERATOR | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-BLOCKS | COMP-MANIFEST-SCANNER |
| depends-on | COMP-MANIFEST-BLOCKS | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-BLOCKS | COMP-UTILS |
| depends-on | COMP-MANIFEST-SCANNER | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-METRICS | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-INTERFACES | COMP-MANIFEST-TYPES |
| depends-on | COMP-MANIFEST-BODY-HINTS | COMP-CORE-TYPES |
| depends-on | COMP-MANIFEST-TEST-ANALYZER | COMP-CORE-TYPES |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST |
| contains | BEH-MANIFEST | BEH-SCAN-PARSE |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-PARSE |
| contains | BEH-MANIFEST | BEH-SCAN-FUNCTIONS |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-FUNCTIONS |
| contains | BEH-MANIFEST | BEH-SCAN-CLASSES |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-CLASSES |
| contains | BEH-MANIFEST | BEH-SCAN-IMPORTS |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-IMPORTS |
| contains | BEH-MANIFEST | BEH-SCAN-CONSTANTS |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-CONSTANTS |
| contains | BEH-MANIFEST | BEH-SCAN-METRICS |
| traces-to | COMP-MANIFEST-SCANNER | BEH-SCAN-METRICS |
| contains | BEH-MANIFEST | BEH-MANIFEST-CONFIG |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-CONFIG |
| contains | BEH-MANIFEST | BEH-MANIFEST-METRICS |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-METRICS |
| contains | BEH-MANIFEST | BEH-MANIFEST-BLOCKS |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-BLOCKS |
| contains | BEH-MANIFEST | BEH-MANIFEST-SCAN |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-SCAN |
| contains | BEH-MANIFEST | BEH-MANIFEST-IFACE |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-IFACE |
| contains | BEH-MANIFEST | BEH-MANIFEST-ASSEMBLE |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-MANIFEST-ASSEMBLE |
| contains | BEH-MANIFEST | BEH-BODYHINT-CLASSIFY |
| traces-to | COMP-MANIFEST-BODY-HINTS | BEH-BODYHINT-CLASSIFY |
| contains | BEH-MANIFEST | BEH-BODYHINT-SUMMARIZE |
| traces-to | COMP-MANIFEST-BODY-HINTS | BEH-BODYHINT-SUMMARIZE |
| contains | BEH-MANIFEST | BEH-TEST-DISCOVER |
| traces-to | COMP-MANIFEST-TEST-ANALYZER | BEH-TEST-DISCOVER |
| contains | BEH-MANIFEST | BEH-TEST-ASSERTIONS |
| traces-to | COMP-MANIFEST-TEST-ANALYZER | BEH-TEST-ASSERTIONS |
| contains | BEH-MANIFEST | BEH-IFACE-RESOLVE |
| traces-to | COMP-MANIFEST-INTERFACES | BEH-IFACE-RESOLVE |
| contains | BEH-MANIFEST | BEH-IFACE-DEDUP |
| traces-to | COMP-MANIFEST-INTERFACES | BEH-IFACE-DEDUP |
| contains | BEH-MANIFEST | BEH-RECURSIVE-SCAN |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-RECURSIVE-SCAN |
| contains | BEH-MANIFEST | BEH-RECURSIVE-DEPS |
| traces-to | COMP-MANIFEST-GENERATOR | BEH-RECURSIVE-DEPS |

\newpage

## Sub-Model F6: Orchestration

- **Validation Score:** 88/100
- **Components:** 2
- **Capabilities:** 1
- **Interfaces:** 1
- **Behaviors:** 9
- **Constraints:** 0
- **Relationships:** 19

**Capabilities:**

- CAP-F10: Auto-Enrichment (F-Block F6)

**Interfaces:**

- IF-ENRICH-API: Enrichment API

**Behaviors:**

- BEH-ENRICH: Auto-Enrichment
- BEH-ENRICH-SIGS: Signature Enrichment
- BEH-ENRICH-CONSTS: Constant Enrichment
- BEH-ENRICH-TESTS: Test Contract Enrichment
- BEH-ORCH-FIND-COMPS: Find Block Components
- BEH-ORCH-FIND-PARENT: Find Parent Component
- BEH-ORCH-TRACE: Trace Entities
- BEH-ORCH-COLLECT-RELS: Collect Relationships
- BEH-ORCH-BUILD: Build Sub-Model

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-ENRICH | enrich | 1 | 0 | 2 |
| COMP-DECOMPOSE | decompose | 2 | 0 | 3 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| realizes | COMP-ENRICH | CAP-F10 |
| exposes | COMP-ENRICH | IF-ENRICH-API |
| depends-on | COMP-CLI | COMP-ENRICH |
| depends-on | COMP-ENRICH | COMP-CORE |
| depends-on | COMP-ENRICH | COMP-MANIFEST |
| traces-to | COMP-ENRICH | BEH-ENRICH |
| depends-on | COMP-DECOMPOSE | COMP-CORE |
| depends-on | COMP-DECOMPOSE | COMP-CONFIG |
| contains | BEH-ENRICH | BEH-ENRICH-SIGS |
| traces-to | COMP-ENRICH | BEH-ENRICH-SIGS |
| contains | BEH-ENRICH | BEH-ENRICH-CONSTS |
| traces-to | COMP-ENRICH | BEH-ENRICH-CONSTS |
| contains | BEH-ENRICH | BEH-ENRICH-TESTS |
| traces-to | COMP-ENRICH | BEH-ENRICH-TESTS |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-FIND-COMPS |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-FIND-PARENT |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-TRACE |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-COLLECT-RELS |
| traces-to | COMP-DECOMPOSE | BEH-ORCH-BUILD |

\newpage

## Sub-Model F7: Profiles

- **Validation Score:** 94/100
- **Refines:** COMP-PROFILES
- **Components:** 1
- **Capabilities:** 1
- **Interfaces:** 1
- **Behaviors:** 2
- **Constraints:** 0
- **Relationships:** 6

**Capabilities:**

- CAP-F8: Domain Profiles (F-Block F7)

**Interfaces:**

- IF-PROFILE-API: Profile API

**Behaviors:**

- BEH-PROFILE-LOAD: Load Profile
- BEH-PROFILE-APPLY: Apply Profile Rules

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-PROFILES | profiles | 3 | 1 | 0 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| realizes | COMP-PROFILES | CAP-F8 |
| exposes | COMP-PROFILES | IF-PROFILE-API |
| depends-on | COMP-CORE | COMP-PROFILES |
| depends-on | COMP-CORE-VALIDATOR | COMP-PROFILES |
| traces-to | COMP-PROFILES | BEH-PROFILE-LOAD |
| traces-to | COMP-PROFILES | BEH-PROFILE-APPLY |

\newpage

## Sub-Model F8: Spec

- **Validation Score:** 96/100
- **Refines:** COMP-SPEC
- **Components:** 1
- **Capabilities:** 1
- **Interfaces:** 0
- **Behaviors:** 0
- **Constraints:** 1
- **Relationships:** 3

**Capabilities:**

- CAP-F6: Schema Specification (F-Block F8)

**Constraints:**

- CON-SCHEMA: Schema Compliance

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-SPEC | spec | 0 | 0 | 0 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| realizes | COMP-SPEC | CAP-F6 |
| constrained-by | COMP-SPEC | CON-SCHEMA |
| depends-on | COMP-CORE | COMP-SPEC |

\newpage

## Sub-Model F9: Utils

- **Validation Score:** 90/100
- **Refines:** COMP-UTILS
- **Components:** 1
- **Capabilities:** 1
- **Interfaces:** 0
- **Behaviors:** 2
- **Constraints:** 0
- **Relationships:** 7

**Capabilities:**

- CAP-F9: Shared Utilities (F-Block F9)

**Behaviors:**

- BEH-UTILS-DISCOVER: File Discovery
- BEH-UTILS-TESTS: Test File Discovery

**Components:**

| ID | Name | Sigs | Const | Contracts |
|----|------|:----:|:-----:|:---------:|
| COMP-UTILS | utils | 4 | 0 | 7 |

**Relationships:**

| Type | From | To |
|------|------|-----|
| realizes | COMP-UTILS | CAP-F9 |
| depends-on | COMP-MANIFEST | COMP-UTILS |
| depends-on | COMP-CORE-MERGER | COMP-UTILS |
| depends-on | COMP-CORE-DECOMPOSER | COMP-UTILS |
| depends-on | COMP-MANIFEST-BLOCKS | COMP-UTILS |
| traces-to | COMP-UTILS | BEH-UTILS-DISCOVER |
| traces-to | COMP-UTILS | BEH-UTILS-TESTS |

\newpage
