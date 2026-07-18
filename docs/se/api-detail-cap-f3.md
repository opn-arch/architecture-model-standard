# API Detail — CAP-F3: Model Slicing & Diffing

## IF-SLICER-API — `architecture_model.core.slicer`

### `slice_by_fblock(model: ArchitectureModel, f_block: str, include_relationships: bool = True) -> ArchitectureModel`

Extracts all entities and relationships related to a specific functional block.

**Algorithm:**

1. Find capabilities where `capability.f_block == f_block`
2. Find behaviors tagged with this f_block
3. Find components where `component.f_block == f_block`
4. Find interfaces where f_block appears in `provider` or `consumer`
5. Find actors referenced by matched behaviors (via `behavior.actor`)
6. Collect all matched entity IDs
7. Filter relationships: include any relationship where `from_id` OR `to_id` is in the relevant set

**Returns:** A new `ArchitectureModel` containing only the F-block's entities and their relationships. Constraints and layers are excluded (they're global concerns).

**Use case:** LLM context compression — give the agent only the slice relevant to the subsystem it's working on.

---

### `slice_by_layer(model: ArchitectureModel, layer_id: str) -> ArchitectureModel`

Extracts all entities allocated to a specific architectural layer.

**Algorithm:**

1. Find layers matching `layer_id`
2. Find components where `component.layer == layer_id`
3. Filter relationships involving those component IDs

**Returns:** A new model with only the layer and its components + their relationships.

**Use case:** Working on a single tier (e.g., "data-layer") without noise from other tiers.

---

### `slice_by_status(model: ArchitectureModel, status: Status) -> ArchitectureModel`

Filters the entire model to entities with a specific status (ACTIVE, PLANNED, DEPRECATED).

**Algorithm:**

1. Filter ALL entity types (actors, capabilities, behaviors, interfaces, constraints, layers, components) by matching status
2. Collect IDs of surviving entities
3. Include only relationships where BOTH endpoints survived the filter

**Returns:** A deep-copied model with only matching-status entities.

**Use case:** "Show me only what's planned" or "show me only active architecture."

---

### `slice_for_artifact(model: ArchitectureModel, artifact_name: str) -> ArchitectureModel`

Extracts the model subset needed to regenerate a specific SE document artifact.

**Supported artifacts and what they include:**

| Artifact | Entities Included | Relationship Types |
|----------|------------------|--------------------|
| `functional-architecture` | actors, capabilities, behaviors | realizes, contains, depends_on |
| `logical-architecture` | capabilities, layers, components | allocated_to, contains, depends_on |
| `use-cases` | actors, capabilities, behaviors | realizes, depends_on |
| `icd` | capabilities, interfaces, components, layers | exposes, consumes |
| `requirements-analysis` | capabilities, behaviors, constraints | constrained_by, traces_to, realizes |
| `operations-manual` | capabilities, behaviors, interfaces, components | realizes, exposes |
| `conops` | actors, capabilities, behaviors, constraints | realizes, depends_on |
| `testing` | capabilities, behaviors, constraints, components | realizes, constrained_by |
| `deployment-guide` | capabilities, interfaces, layers, components, external actors | depends_on, exposes, consumes |
| `data-dictionary` | capabilities, interfaces, layers, data-layer components | realizes, exposes |
| `readme` | actors, capabilities, layers | realizes (COMP→CAP only) |

**Use case:** The MCP server's `architect_slice` tool uses this to give an LLM only the model context needed to regenerate a specific document.

---

## Differ — `architecture_model.core.differ`

### `diff_models(old_model: ArchitectureModel, new_model: ArchitectureModel) -> ModelDiff`

Compares two model versions and produces a structured diff. Detects additions, removals, and modifications at the entity and relationship level.

**Algorithm:**

1. For each entity type (actors, capabilities, behaviors, interfaces, constraints, layers, components):
   - Build `{id: entity}` maps for old and new
   - IDs in new but not old → ADDED
   - IDs in old but not new → REMOVED
   - IDs in both → check for field-level changes (name, status, description, f_block, layer, priority) → MODIFIED
2. For relationships:
   - Build sets of `(type, from_id, to_id)` tuples
   - Set difference → ADDED / REMOVED relationships

**Returns:** `ModelDiff` with:

| Field/Property | Type | Description |
|----------------|------|-------------|
| `entity_changes` | `list[EntityChange]` | Each with `change_type`, `entity_type`, `entity_id`, `entity_name`, `details` |
| `relationship_changes` | `list[RelationshipChange]` | Each with `change_type`, `rel_type`, `from_id`, `to_id` |
| `has_changes` | `bool` | True if any changes exist |
| `added_count` | `int` | Number of added entities |
| `removed_count` | `int` | Number of removed entities |
| `modified_count` | `int` | Number of modified entities |
| `summary()` | `str` | One-line summary: `"+3 -1 ~2 entities, 4 relationship changes"` |
| `format_report()` | `str` | Multi-line markdown report grouped by entity type |
| `affected_artifacts()` | `set[str]` | Artifact names that should be regenerated based on what changed |

**Staleness detection:** `affected_artifacts()` maps entity types to artifacts:
- actor/behavior changes → `use-cases`
- capability changes → `functional-architecture`, `use-cases`
- layer/component changes → `logical-architecture`
- interface changes → `icd`
- constraint changes → `requirements-analysis`
- All changes → `readme`

---

## Merger — `architecture_model.core.merger`

### `merge_manifest(model: ArchitectureModel, manifest_path: str | Path, project_root: str | Path | None = None) -> ArchitectureModel`

Merges manifest data INTO the architecture model (in-place mutation). The manifest provides code-grounded facts; the model provides architectural decisions. Merger supplements — never overwrites decisions.

**What gets merged:**
- Component `files` lists enriched with manifest-discovered paths
- Layer `directories` populated from manifest module scan
- `meta.manifest_hash` updated with content hash

**What is NOT overwritten:**
- Entity names, descriptions, status markers
- Relationships (architectural decisions)
- Capabilities, behaviors, constraints (model-level truth)

---

### `compose_enriched_model(project_root: Path) -> ArchitectureModel`

The heavy-duty enrichment pipeline. Scans ALL source files and builds a model enriched with AST-level detail sufficient for code regeneration.

**Algorithm:**

1. Discover all source files (non-test `.py` files)
2. Discover all test files (`test_*.py`, `*_test.py`)
3. Map tests to sources (by naming convention and import analysis)
4. For each source file:
   - Parse AST
   - Extract **constants** (module-level `UPPER_CASE = literal` + class attributes)
   - Extract **function signatures** with **body hints** (trivial implementations)
   - Extract **test contracts** from mapped test files (assertions about expected behavior)
5. Each source module becomes a Component with all extracted detail

**Returns:** An `ArchitectureModel` with one Component per source file, enriched with:
- `constants: list[Constant]` — name, value, context
- `signatures: list[FunctionSignature]` — name, params, returns, decorators, body_hint
- `test_contracts: list[TestContract]` — test_file, test_method, assertion, contract_type

This is the function that produces models capable of **blind code regeneration** (100% fidelity without reading source).

---

## Decomposer — `architecture_model.core.decomposer`

### `compute_complexity(comp: Component, model: ArchitectureModel) -> float`

Weighted complexity score for a single component.

**Formula:**
```
score = (symbols × 2.0) + (total_members × 0.3) + (functions × 0.5) + (dep_relationships × 1.5)
```

---

### `identify_systems(model: ArchitectureModel, manifest: dict) -> list[SystemCandidate]`

Identifies F-block groups complex enough to warrant promotion to System entities.

**Algorithm:**
1. Group components by `f_block`
2. Sum complexity scores per group
3. Groups exceeding `SYSTEM_THRESHOLD` (10.0) become SystemCandidates

**Returns:** `SystemCandidate` with `f_block`, `name`, `component_ids`, `complexity_score`.

---

### `auto_assign_f_blocks(model: ArchitectureModel, max_cluster_size: int = 5) -> ArchitectureModel`

Assigns `f_block` values to components via dependency-graph clustering. Used when the model has no f_block annotations (e.g., freshly extracted models).

**Algorithm:**
1. Build undirected adjacency from `depends_on` relationships
2. Sort components by degree (most connected first)
3. Seed clusters from highest-degree nodes
4. Grow each cluster by adding adjacent unassigned nodes (up to `max_cluster_size`)
5. Singletons get their own f_block

**Returns:** New model (no mutation) with `f_block` assigned on all components.

---

### `test_affinity_decompose(repo_path: Path) -> list[Subsystem]`

Decomposes a repository into subsystems based on test file affinity. This is the algorithm that drives the blind regeneration benchmark.

**Algorithm:**

1. Discover all test files (`*_test.py`, `test_*.py`)
2. Discover all source files (non-test `.py`)
3. For each test file, AST-parse imports to identify which source modules it tests
4. Primary assignment: each source file belongs to exactly one subsystem (preference: name match > exclusive import > first claimant)
5. Source modules with no test → assigned to `root` subsystem
6. Determine inter-subsystem dependencies via import analysis
7. Return subsystems sorted topologically (leaves first)

**Returns:** `list[Subsystem]` where each has:
- `name: str` — subsystem identifier (e.g., "ansi", "parser")
- `source_files: list[Path]` — modules in this subsystem
- `test_files: list[Path]` — tests validating this subsystem
- `dependencies: list[str]` — names of upstream subsystems

**Why topological sort matters:** During regeneration, leaf subsystems (no deps) are regenerated first. Downstream subsystems can then import them.
