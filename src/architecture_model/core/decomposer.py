"""Complexity scoring and system identification for architecture decomposition.

Provides functions to compute weighted complexity scores for components and
identify F-block groups that should be promoted to System entities.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    System,
)

# Aggregate complexity score above which an F-block group becomes a System
SYSTEM_THRESHOLD = 10.0


@dataclass
class SystemCandidate:
    """A proposed system identified from F-block complexity analysis."""
    f_block: str
    name: str
    component_ids: list[str]
    complexity_score: float


@dataclass
class Subsystem:
    """A subsystem identified from test file affinity analysis."""
    name: str                          # e.g., "ansi"
    source_files: list[Path]           # modules in this subsystem
    test_files: list[Path]             # tests that validate this subsystem
    dependencies: list[str] = field(default_factory=list)  # other subsystem names


def compute_complexity(comp: Component, model: ArchitectureModel) -> float:
    """Weighted complexity score for determining if a component should be in a System.

    Factors:
        - Number of symbols x 2.0
        - Total members (sum of all symbol members) x 0.3
        - Number of functions x 0.5
        - Number of depends-on relationships (inbound + outbound) x 1.5
    """
    symbol_weight = len(comp.symbols) * 2.0
    member_weight = sum(len(s.members) for s in comp.symbols) * 0.3
    function_weight = len(comp.functions) * 0.5

    # Count depends-on relationships involving this component
    deps = sum(
        1 for r in model.relationships
        if r.type == RelationType.DEPENDS_ON
        and (r.from_id == comp.id or r.to_id == comp.id)
    )
    dep_weight = deps * 1.5

    return symbol_weight + member_weight + function_weight + dep_weight


def identify_systems(
    model: ArchitectureModel,
    manifest: dict,
) -> list[SystemCandidate]:
    """Identify F-block groups that should become Systems.

    Groups components by f_block, computes aggregate complexity per group,
    and returns SystemCandidates for groups exceeding SYSTEM_THRESHOLD.

    For components without an f_block field, they are skipped (remain as
    top-level components).

    Args:
        model: The architecture model with enriched components.
        manifest: Manifest dict containing functional_blocks metadata.

    Returns:
        List of SystemCandidate for groups exceeding threshold.
    """
    # Group components by f_block (skip empty f_block)
    groups: dict[str, list[Component]] = defaultdict(list)
    for comp in model.entities.components:
        if comp.f_block:
            groups[comp.f_block].append(comp)

    # Get functional_blocks metadata for naming
    fblocks_meta = manifest.get("functional_blocks", {})

    candidates: list[SystemCandidate] = []
    for fblock_id, components in groups.items():
        # Sum complexity across all components in this F-block
        total_complexity = sum(
            compute_complexity(comp, model) for comp in components
        )

        if total_complexity > SYSTEM_THRESHOLD:
            # Resolve name from manifest, fall back to f_block ID
            block_info = fblocks_meta.get(fblock_id)
            name = block_info["name"] if block_info else fblock_id

            candidates.append(SystemCandidate(
                f_block=fblock_id,
                name=name,
                component_ids=[c.id for c in components],
                complexity_score=total_complexity,
            ))

    return candidates


def auto_assign_f_blocks(
    model: ArchitectureModel,
    max_cluster_size: int = 5,
) -> ArchitectureModel:
    """Assign f_block values to components via dependency-graph clustering.

    Used when the model has no f_block annotations (e.g., oracle-extracted models).
    Groups components by import/dependency density using greedy modularity:
    1. Build undirected adjacency from depends_on relationships
    2. Seed clusters from highest-degree nodes
    3. Grow each cluster by adding adjacent unassigned nodes (max size limit)
    4. Singletons keep their own f_block (decomposer threshold handles them)

    Mutates nothing — returns a new model with f_block assigned on components.
    """
    # Check if f_blocks already exist
    has_fblocks = any(c.f_block for c in model.entities.components)
    if has_fblocks:
        return model

    comps = model.entities.components
    if len(comps) <= 1:
        return model

    # Build adjacency from depends_on relationships
    adj: dict[str, set[str]] = defaultdict(set)
    comp_ids = {c.id for c in comps}
    for rel in model.relationships:
        if rel.type == RelationType.DEPENDS_ON:
            if rel.from_id in comp_ids and rel.to_id in comp_ids:
                adj[rel.from_id].add(rel.to_id)
                adj[rel.to_id].add(rel.from_id)

    # Sort components by degree (most connected first → seed clusters)
    sorted_comps = sorted(comps, key=lambda c: len(adj.get(c.id, set())), reverse=True)

    assigned: dict[str, str] = {}  # comp_id → f_block_id
    cluster_id = 0

    for comp in sorted_comps:
        if comp.id in assigned:
            continue

        # Start a new cluster from this node
        cluster_id += 1
        f_block = f"F{cluster_id}"
        cluster = [comp.id]
        assigned[comp.id] = f_block

        # Grow cluster by adding adjacent unassigned nodes
        # Prefer neighbors that share the MOST connections with the seed
        neighbors = sorted(
            [n for n in adj.get(comp.id, set()) if n not in assigned],
            key=lambda n: len(adj.get(n, set()) & adj.get(comp.id, set())),
            reverse=True,
        )
        for neighbor in neighbors:
            if neighbor in assigned:
                continue
            if len(cluster) >= max_cluster_size:
                break
            cluster.append(neighbor)
            assigned[neighbor] = f_block

    # Assign any remaining (no edges) components their own f_block
    for comp in comps:
        if comp.id not in assigned:
            cluster_id += 1
            assigned[comp.id] = f"F{cluster_id}"

    # Build new components with f_block assigned
    from copy import deepcopy
    new_comps = []
    for comp in comps:
        new_comp = deepcopy(comp)
        new_comp.f_block = assigned[comp.id]
        new_comps.append(new_comp)

    # Return new model with updated components
    new_entities = Entities(
        actors=model.entities.actors,
        capabilities=model.entities.capabilities,
        behaviors=model.entities.behaviors,
        interfaces=model.entities.interfaces,
        constraints=model.entities.constraints,
        layers=model.entities.layers,
        components=new_comps,
        systems=model.entities.systems,
    )
    return ArchitectureModel(
        meta=model.meta,
        entities=new_entities,
        relationships=model.relationships,
    )


def _slugify(name: str) -> str:
    """Lowercase and replace spaces/underscores with hyphens."""
    return name.lower().replace(" ", "-").replace("_", "-")


@dataclass
class DecompositionResult:
    """Result of model decomposition into system hierarchy."""
    top_level: ArchitectureModel
    sub_models: dict[str, ArchitectureModel]  # system_id → sub-model


def decompose_model(
    model: ArchitectureModel,
    manifest: dict,
    output_dir: str = "systems",
) -> DecompositionResult:
    """Decompose a flat model into top-level + system sub-models.

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
        DecompositionResult with top-level model and sub-models dict.
    """
    candidates = identify_systems(model, manifest)

    if not candidates:
        return DecompositionResult(top_level=model, sub_models={})

    # Build mapping: component_id → system_id for all systems
    comp_to_system: dict[str, str] = {}
    system_ids: dict[str, SystemCandidate] = {}
    for candidate in candidates:
        sys_id = f"sys-{_slugify(candidate.name)}"
        system_ids[sys_id] = candidate
        for comp_id in candidate.component_ids:
            comp_to_system[comp_id] = sys_id

    # Collect all component IDs that are promoted into systems
    promoted_comp_ids = set(comp_to_system.keys())

    # Partition components: top-level vs sub-model
    top_level_components = [
        c for c in model.entities.components if c.id not in promoted_comp_ids
    ]

    # Build sub-models and system entities
    sub_models: dict[str, ArchitectureModel] = {}
    systems: list[System] = []

    for sys_id, candidate in system_ids.items():
        slug = _slugify(candidate.name)
        sub_model_ref = f"{output_dir}/{slug}.yaml"

        # Create System entity for top-level
        sys_entity = System(
            id=sys_id,
            name=candidate.name,
            status=Status.ACTIVE,
            f_block=candidate.f_block,
            complexity_score=candidate.complexity_score,
            sub_model_ref=sub_model_ref,
            component_ids=candidate.component_ids,
        )
        systems.append(sys_entity)

        # Extract components belonging to this system
        sys_comp_ids = set(candidate.component_ids)
        sys_components = [
            c for c in model.entities.components if c.id in sys_comp_ids
        ]

        # Partition relationships for this system's sub-model (intra-system only)
        intra_rels = [
            r for r in model.relationships
            if r.from_id in sys_comp_ids and r.to_id in sys_comp_ids
        ]

        # Create sub-model with system-scoped meta
        sub_meta = ModelMeta(
            schema_version=model.meta.schema_version,
            project=model.meta.project,
            system=candidate.name,
            generated_at=model.meta.generated_at,
            source_artifacts=model.meta.source_artifacts,
            manifest_hash=model.meta.manifest_hash,
        )
        sub_model = ArchitectureModel(
            meta=sub_meta,
            entities=Entities(components=sys_components),
            relationships=intra_rels,
        )
        sub_models[sys_id] = sub_model

    # Partition relationships for top-level:
    # - Both ends outside all systems → keep as-is
    # - Inter-system (one end inside, other outside or in different system) → promote
    top_level_rels: list[Relationship] = []
    promoted_rel_keys: set[tuple[RelationType, str, str]] = set()

    for rel in model.relationships:
        from_sys = comp_to_system.get(rel.from_id)
        to_sys = comp_to_system.get(rel.to_id)

        if from_sys and to_sys and from_sys == to_sys:
            # Intra-system: already in sub-model, skip from top-level
            continue
        elif from_sys is None and to_sys is None:
            # Both ends outside all systems: keep in top-level as-is
            top_level_rels.append(rel)
        else:
            # Inter-system: rewrite the inside end to system ID
            new_from = from_sys if from_sys else rel.from_id
            new_to = to_sys if to_sys else rel.to_id

            # Deduplicate: same (type, from, to) only appears once
            key = (rel.type, new_from, new_to)
            if key not in promoted_rel_keys:
                promoted_rel_keys.add(key)
                promoted_rel = Relationship(
                    type=rel.type,
                    from_id=new_from,
                    to_id=new_to,
                )
                top_level_rels.append(promoted_rel)

    # Build top-level model
    top_level_entities = Entities(
        actors=model.entities.actors,
        capabilities=model.entities.capabilities,
        behaviors=model.entities.behaviors,
        interfaces=model.entities.interfaces,
        constraints=model.entities.constraints,
        layers=model.entities.layers,
        components=top_level_components,
        systems=systems,
    )
    top_level_model = ArchitectureModel(
        meta=model.meta,
        entities=top_level_entities,
        relationships=top_level_rels,
    )

    return DecompositionResult(top_level=top_level_model, sub_models=sub_models)


# ---------------------------------------------------------------------------
# Test-affinity decomposition strategy
# ---------------------------------------------------------------------------

# Directories to skip when scanning for source/test files
_EXCLUDED_DIRS = frozenset({
    ".venv", "venv", ".env", "env",
    "node_modules", ".git", ".hg", ".svn",
    "site-packages", "dist-packages",
    "__pycache__", ".tox", ".nox",
    "build", "dist", ".eggs", "*.egg-info",
    "output", "demos",
})


def _is_excluded(path: Path, repo_path: Path) -> bool:
    """Check if a path should be excluded from scanning."""
    parts = path.relative_to(repo_path).parts
    for part in parts:
        if part in _EXCLUDED_DIRS or part.endswith(".egg-info"):
            return True
    return False


def _discover_test_files(repo_path: Path) -> list[Path]:
    """Find all test files matching test_*.py, *_test.py, or tests_*.py patterns."""
    test_files: list[Path] = []
    for py_file in repo_path.rglob("*.py"):
        if _is_excluded(py_file, repo_path):
            continue
        name = py_file.name
        if name == "__init__.py":
            continue
        if name.startswith("test_") or name.endswith("_test.py") or name.startswith("tests_"):
            test_files.append(py_file)
    return test_files


def _discover_source_files(repo_path: Path) -> list[Path]:
    """Find all non-test Python source files."""
    source_files: list[Path] = []
    for py_file in repo_path.rglob("*.py"):
        if _is_excluded(py_file, repo_path):
            continue
        name = py_file.name
        if name.startswith("test_") or name.endswith("_test.py") or name.startswith("tests_"):
            continue
        # Skip files inside common test directories that aren't source
        # (but __init__.py inside tests/ is fine to skip)
        parts = py_file.relative_to(repo_path).parts
        if "tests" in parts and name == "__init__.py":
            continue
        source_files.append(py_file)
    return source_files


def _extract_imports(file_path: Path) -> list[str]:
    """Extract all imported module names from a Python file using AST.

    Returns a flat list of top-level module/package names imported.
    E.g., 'from colorama.ansi import Fore' -> ['colorama.ansi']
          'import os' -> ['os']
          'from .winterm import WinTerm' -> ['.winterm']
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                prefix = "." * (node.level or 0)
                imports.append(f"{prefix}{node.module}")
            elif node.level:
                # from . import something → relative import with no module
                for alias in node.names:
                    imports.append(f"{'.' * node.level}{alias.name}")
    return imports


def _resolve_import_to_source(
    import_name: str,
    source_files: list[Path],
    repo_path: Path,
) -> Path | None:
    """Resolve an import string to a source file path.

    Handles:
    - Direct package imports: 'colorama.ansi' → colorama/ansi.py
    - Relative imports: '.winterm' → winterm.py (in same package)
    - Simple module names: 'ansi' → ansi.py
    - Sub-module imports: 'structlog._config' → src/structlog/_config.py
    """
    # Strip leading dots for relative imports
    stripped = import_name.lstrip(".")

    # Try matching against source file module paths
    for src_file in source_files:
        rel = src_file.relative_to(repo_path)
        # Convert path to dotted module: colorama/ansi.py → colorama.ansi
        # Also handle src-layout: src/structlog/_config.py → structlog._config
        if rel.name == "__init__.py":
            module_path = ".".join(rel.parent.parts)
        else:
            module_path = ".".join(rel.with_suffix("").parts)

        # Strip 'src.' prefix for src-layout repos
        module_path_no_src = module_path
        if module_path.startswith("src."):
            module_path_no_src = module_path[4:]

        # Exact match: 'colorama.ansi' == 'colorama.ansi'
        if module_path == stripped or module_path_no_src == stripped:
            return src_file

        # Suffix match: import 'colorama.ansi' matches module 'ansi'
        # (when import is fully qualified)
        parts = stripped.split(".")
        stem = rel.stem if rel.name != "__init__.py" else rel.parent.name
        if parts[-1] == stem and len(parts) > 1:
            # Verify the package part matches
            pkg_parts = parts[:-1]
            path_parts = list(rel.parent.parts) if rel.name != "__init__.py" else list(rel.parent.parent.parts)
            # Check if package parts align (at least the last part should match)
            if pkg_parts == list(rel.parent.parts)[:len(pkg_parts)]:
                return src_file
            # Also check without 'src' prefix in path
            path_no_src = [p for p in path_parts if p != "src"]
            if pkg_parts == path_no_src[:len(pkg_parts)]:
                return src_file

        # Simple name match: 'ansi' → ansi.py
        if stripped == stem and "." not in stripped:
            return src_file

    return None


def _subsystem_name_from_test(test_file: Path) -> str:
    """Derive subsystem name from test file name.

    test_alpha.py → 'alpha'
    ansi_test.py → 'ansi'
    tests_alpha.py → 'alpha'
    """
    name = test_file.stem
    if name.startswith("test_"):
        return name[5:]  # strip 'test_'
    elif name.startswith("tests_"):
        return name[6:]  # strip 'tests_'
    elif name.endswith("_test"):
        return name[:-5]  # strip '_test'
    return name


def test_affinity_decompose(repo_path: Path) -> list[Subsystem]:
    """Decompose a repository into subsystems based on test file affinity.

    Algorithm:
    1. Discover all test files (*_test.py, test_*.py)
    2. Discover all source files (non-test .py files)
    3. For each test file, AST-parse its imports to identify which source modules it tests
    4. Group source modules by their primary test file (each source → exactly one subsystem)
    5. Determine dependencies between subsystems via import analysis
    6. Return subsystems sorted topologically (leaves first)

    Source modules with no test → assigned to 'root' subsystem
    """
    test_files = _discover_test_files(repo_path)
    source_files = _discover_source_files(repo_path)

    if not source_files:
        return []

    # Step 3: For each test file, find which source files it imports
    # Build: test_name → set of source files it imports
    test_to_sources: dict[str, set[Path]] = {}
    test_name_to_file: dict[str, Path] = {}

    for test_file in test_files:
        sub_name = _subsystem_name_from_test(test_file)
        imports = _extract_imports(test_file)

        matched_sources: set[Path] = set()
        for imp in imports:
            src = _resolve_import_to_source(imp, source_files, repo_path)
            if src is not None:
                matched_sources.add(src)

        if matched_sources:
            if sub_name not in test_to_sources:
                test_to_sources[sub_name] = set()
                test_name_to_file[sub_name] = test_file
            test_to_sources[sub_name].update(matched_sources)
            # If multiple test files map to same subsystem name, keep track
            # (unusual but handle gracefully)

    # Step 4: Primary assignment — each source file belongs to exactly one subsystem
    # Priority: assign to the subsystem whose name best matches the source file stem
    # Then: assign to the test that imports it exclusively
    # Finally: if claimed by multiple, prefer the name-matched test

    # Build: source → list of subsystems that claim it
    source_claimants: dict[Path, list[str]] = defaultdict(list)
    for sub_name, sources in test_to_sources.items():
        for src in sources:
            source_claimants[src].append(sub_name)

    # Assign each source to exactly one subsystem
    source_assignment: dict[Path, str] = {}
    for src_file, claimants in source_claimants.items():
        if len(claimants) == 1:
            source_assignment[src_file] = claimants[0]
        else:
            # Multiple tests import this source — pick the best match by name
            stem = src_file.stem
            best_match = None
            for c in claimants:
                if c == stem:
                    best_match = c
                    break
            if best_match is None:
                # No exact name match — assign to first alphabetically for determinism
                best_match = sorted(claimants)[0]
            source_assignment[src_file] = best_match

    # Step: Build subsystem_sources and assign unclaimed to 'root'
    subsystem_sources: dict[str, set[Path]] = defaultdict(set)
    subsystem_tests: dict[str, set[Path]] = defaultdict(set)

    for src_file, sub_name in source_assignment.items():
        subsystem_sources[sub_name].add(src_file)

    # Record test files for each subsystem
    for sub_name, test_file in test_name_to_file.items():
        if sub_name in subsystem_sources:
            subsystem_tests[sub_name].add(test_file)

    # Also collect ALL test files for a subsystem (handle multiple test files
    # mapping to same name, e.g., via directory structures)
    for test_file in test_files:
        sub_name = _subsystem_name_from_test(test_file)
        if sub_name in subsystem_sources:
            subsystem_tests[sub_name].add(test_file)

    # Assign unclaimed source files to 'root'
    for src_file in source_files:
        if src_file not in source_assignment:
            subsystem_sources["root"].add(src_file)

    # Ensure 'root' exists even if empty
    if "root" not in subsystem_sources:
        subsystem_sources["root"] = set()

    # Build source→subsystem mapping for dependency detection
    source_to_subsystem: dict[Path, str] = {}
    for sub_name, sources in subsystem_sources.items():
        for src in sources:
            source_to_subsystem[src] = sub_name

    # Step 5: Determine dependencies between subsystems
    subsystem_deps: dict[str, set[str]] = defaultdict(set)
    for sub_name, sources in subsystem_sources.items():
        for src_file in sources:
            imports = _extract_imports(src_file)
            for imp in imports:
                target = _resolve_import_to_source(imp, source_files, repo_path)
                if target is not None:
                    target_sub = source_to_subsystem.get(target)
                    if target_sub and target_sub != sub_name:
                        subsystem_deps[sub_name].add(target_sub)

    # Step 6: Topological sort (leaves first = Kahn's algorithm)
    all_names = set(subsystem_sources.keys())
    # Remove empty root if it has no files
    if not subsystem_sources.get("root"):
        all_names.discard("root")

    # Topological sort: A depends on B means B comes before A
    # in_degree[A] = number of subsystems A depends on (that exist in graph)
    in_degree: dict[str, int] = {}
    for name in all_names:
        deps_in_graph = subsystem_deps.get(name, set()) & all_names
        in_degree[name] = len(deps_in_graph)

    # Kahn's algorithm
    queue = sorted([n for n in all_names if in_degree[n] == 0])
    sorted_names: list[str] = []
    while queue:
        node = queue.pop(0)
        sorted_names.append(node)
        # Find nodes that depend on this node and reduce their in-degree
        for sub_name in all_names:
            if node in (subsystem_deps.get(sub_name, set()) & all_names):
                in_degree[sub_name] -= 1
                if in_degree[sub_name] == 0:
                    queue.append(sub_name)
        queue.sort()  # deterministic ordering

    # Any remaining (cycles) — append in alphabetical order
    remaining = sorted(all_names - set(sorted_names))
    sorted_names.extend(remaining)

    # Build result
    result: list[Subsystem] = []
    for sub_name in sorted_names:
        sources = sorted(subsystem_sources.get(sub_name, set()))
        tests = sorted(subsystem_tests.get(sub_name, set()))
        deps = sorted(subsystem_deps.get(sub_name, set()) & all_names)
        result.append(Subsystem(
            name=sub_name,
            source_files=sources,
            test_files=tests,
            dependencies=deps,
        ))

    return result
