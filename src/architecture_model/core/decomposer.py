"""Complexity scoring and system identification for architecture decomposition.

Bootstrap strategy for repos without existing models.
For repos WITH models, use orchestration.decompose instead.
"""

from __future__ import annotations

from collections import defaultdict
import os
from dataclasses import dataclass, field

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
    source_block: str
    name: str
    component_ids: list[str]
    complexity_score: float


@dataclass
class DecompositionResult:
    """Result of model decomposition into system hierarchy."""
    top_level: ArchitectureModel
    sub_models: dict[str, ArchitectureModel]  # system_id → sub-model


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

    Groups components by source_block, computes aggregate complexity per group,
    and returns SystemCandidates for groups exceeding SYSTEM_THRESHOLD.

    For components without an source_block field, they are skipped (remain as
    top-level components).

    Args:
        model: The architecture model with enriched components.
        manifest: Manifest dict containing functional_blocks metadata.

    Returns:
        List of SystemCandidate for groups exceeding threshold.
    """
    # Group components by source_block (skip empty source_block)
    groups: dict[str, list[Component]] = defaultdict(list)
    for comp in model.entities.components:
        if comp.source_block:
            groups[comp.source_block].append(comp)

    # Get functional_blocks metadata for naming
    source_blocks_meta = manifest.get("functional_blocks", {})

    candidates: list[SystemCandidate] = []
    for source_block_id, components in groups.items():
        # Sum complexity across all components in this F-block
        total_complexity = sum(
            compute_complexity(comp, model) for comp in components
        )

        if total_complexity > SYSTEM_THRESHOLD:
            # Resolve name from manifest, fall back to source_block ID
            block_info = source_blocks_meta.get(source_block_id)
            name = block_info["name"] if block_info else source_block_id

            candidates.append(SystemCandidate(
                source_block=source_block_id,
                name=name,
                component_ids=[c.id for c in components],
                complexity_score=total_complexity,
            ))

    return candidates


def _slugify(name: str) -> str:
    """Lowercase and replace spaces/underscores with hyphens."""
    return name.lower().replace(" ", "-").replace("_", "-")


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
            source_block=candidate.source_block,
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


@dataclass
class SystemScore:
    """Result of multi-signal system boundary detection."""
    name: str
    component_ids: list[str]
    independence: float  # 0-1
    signals: dict[str, float] = field(default_factory=dict)


def _import_to_path_candidates(imp: str) -> list[str]:
    """Convert import string to possible file path matches."""
    # e.g. "models.user" -> ["models/user.py", "models/user/__init__.py"]
    parts = imp.replace(".", "/")
    return [parts + ".py", parts + "/__init__.py"]


def _is_data_file(path: str) -> bool:
    """Check if a file is a model/data file."""
    lower = path.lower()
    return "model" in lower or "/models/" in ("/" + lower)


def _has_api_surface(path: str, functions: list[str]) -> bool:
    """Check if a file has API surface."""
    lower = path.lower()
    api_keywords = ["router", "route", "endpoint", "view", "api", "handler"]
    if any(k in lower for k in api_keywords):
        return True
    http_methods = {"get", "post", "put", "delete", "patch"}
    return bool(set(f.lower() for f in functions) & http_methods)


def _compute_pair_affinity(
    comp1_files: set[str],
    comp2_files: set[str],
    comp1_imports: set[str],
    comp2_imports: set[str],
    comp1_data_imports: set[str],
    comp2_data_imports: set[str],
    comp1_has_api: bool,
    comp2_has_api: bool,
) -> float:
    """Compute affinity between two components using 4 signals."""
    # 1. Import coupling (0.4): fraction of comp1's imports resolving to comp2's files
    import_score = 0.0
    if comp1_imports or comp2_imports:
        matches_1to2 = 0
        for imp in comp1_imports:
            candidates = _import_to_path_candidates(imp)
            if any(c in comp2_files or any(c.endswith(f) or f.endswith(c) for f in comp2_files) for c in candidates):
                matches_1to2 += 1
        matches_2to1 = 0
        for imp in comp2_imports:
            candidates = _import_to_path_candidates(imp)
            if any(c in comp1_files or any(c.endswith(f) or f.endswith(c) for f in comp1_files) for c in candidates):
                matches_2to1 += 1
        total_imports = len(comp1_imports) + len(comp2_imports)
        if total_imports > 0:
            import_score = (matches_1to2 + matches_2to1) / total_imports

    # 2. Data affinity (0.3): Jaccard similarity of data/model imports
    data_score = 0.0
    if comp1_data_imports or comp2_data_imports:
        intersection = comp1_data_imports & comp2_data_imports
        union = comp1_data_imports | comp2_data_imports
        data_score = len(intersection) / len(union) if union else 0.0

    # 3. Directory cohesion (0.2): share common directory prefix
    dir_score = 0.0
    dirs1 = set(os.path.dirname(f) for f in comp1_files if os.path.dirname(f))
    dirs2 = set(os.path.dirname(f) for f in comp2_files if os.path.dirname(f))
    if dirs1 and dirs2 and dirs1 & dirs2:
        dir_score = len(dirs1 & dirs2) / len(dirs1 | dirs2)

    # 4. API boundary penalty (0.1): if both have API, penalize merging
    api_penalty = 1.0 if (comp1_has_api and comp2_has_api) else 0.0

    affinity = (
        import_score * 0.4
        + data_score * 0.3
        + dir_score * 0.2
        + (1.0 - api_penalty) * 0.1
    )
    return affinity


def detect_systems(
    model: ArchitectureModel,
    manifest,
    target_systems: int = 0,
) -> list[SystemScore]:
    """Multi-signal system boundary detection.

    Uses import coupling, data affinity, directory cohesion, and API surface
    signals to identify bounded-context boundaries.

    Args:
        model: Architecture model with components having source_files.
        manifest: Manifest with modules (ModuleInfo instances).
        target_systems: Desired number of systems (0 = auto-calculate).

    Returns:
        List of SystemScore representing detected system boundaries.
    """
    components = model.entities.components
    if not components:
        return []

    n = len(components)
    if n == 1:
        return [SystemScore(
            name=components[0].name,
            component_ids=[components[0].id],
            independence=1.0,
            signals={"import_cohesion": 1.0, "directory_cohesion": 1.0, "external_coupling": 0.0},
        )]

    # Build file->module index
    file_to_module = {}
    for mod in manifest.modules:
        file_to_module[mod.file] = mod

    # Pre-compute per-component data
    comp_data = {}
    for comp in components:
        files = set(comp.files)
        imports = set()
        data_imports = set()
        has_api = False
        for f in comp.files:
            mod = file_to_module.get(f)
            if mod:
                imports.update(mod.imports)
                for imp in mod.imports:
                    if _is_data_file(imp.replace(".", "/")):
                        data_imports.add(imp)
                if _has_api_surface(f, [fn.name for fn in mod.functions]):
                    has_api = True
        comp_data[comp.id] = (files, imports, data_imports, has_api)

    # Compute target
    if target_systems <= 0:
        target_systems = max(2, int(n ** 0.6))
    target_systems = min(target_systems, n)

    # Agglomerative clustering
    # Start: each component is its own cluster
    clusters: list[list[str]] = [[comp.id] for comp in components]

    while len(clusters) > target_systems:
        # Find highest affinity pair
        best_affinity = -1.0
        best_i, best_j = 0, 1
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Average linkage: mean affinity between all pairs
                total = 0.0
                count = 0
                for ci in clusters[i]:
                    for cj in clusters[j]:
                        d1 = comp_data[ci]
                        d2 = comp_data[cj]
                        total += _compute_pair_affinity(
                            d1[0], d2[0], d1[1], d2[1], d1[2], d2[2], d1[3], d2[3]
                        )
                        count += 1
                avg = total / count if count else 0.0
                if avg > best_affinity:
                    best_affinity = avg
                    best_i, best_j = i, j
        # Merge
        clusters[best_i] = clusters[best_i] + clusters[best_j]
        clusters.pop(best_j)

    # Score each cluster
    comp_id_to_name = {c.id: c.name for c in components}
    all_comp_ids = set(c.id for c in components)
    results = []
    for cluster in clusters:
        cluster_set = set(cluster)
        # Internal cohesion: avg affinity within cluster
        internal = 0.0
        internal_count = 0
        for i, ci in enumerate(cluster):
            for cj in cluster[i + 1:]:
                d1 = comp_data[ci]
                d2 = comp_data[cj]
                internal += _compute_pair_affinity(
                    d1[0], d2[0], d1[1], d2[1], d1[2], d2[2], d1[3], d2[3]
                )
                internal_count += 1
        avg_internal = internal / internal_count if internal_count else 1.0

        # External coupling: avg affinity with components outside cluster
        external = 0.0
        external_count = 0
        for ci in cluster:
            for cj in all_comp_ids - cluster_set:
                d1 = comp_data[ci]
                d2 = comp_data[cj]
                external += _compute_pair_affinity(
                    d1[0], d2[0], d1[1], d2[1], d1[2], d2[2], d1[3], d2[3]
                )
                external_count += 1
        avg_external = external / external_count if external_count else 0.0

        # Directory cohesion for the cluster
        all_dirs = set()
        for ci in cluster:
            for f in comp_data[ci][0]:
                d = os.path.dirname(f)
                if d:
                    all_dirs.add(d)
        # Simple: ratio of shared top-level dirs
        dir_cohesion = 1.0 if len(cluster) == 1 else avg_internal

        # Independence = weighted(import_cohesion * 0.5, directory_cohesion * 0.3, (1 - external_coupling) * 0.2)
        independence = (
            avg_internal * 0.5
            + dir_cohesion * 0.3
            + (1.0 - avg_external) * 0.2
        )
        independence = max(0.0, min(1.0, independence))

        # Name: use first component's name or combine
        name = comp_id_to_name.get(cluster[0], "System")
        if len(cluster) > 1:
            name = "+".join(comp_id_to_name.get(c, c) for c in cluster[:2])
            if len(cluster) > 2:
                name += f"+{len(cluster) - 2}more"

        results.append(SystemScore(
            name=name,
            component_ids=cluster,
            independence=independence,
            signals={
                "import_cohesion": avg_internal,
                "directory_cohesion": dir_cohesion,
                "external_coupling": avg_external,
            },
        ))

    return results


# Re-exports for backward compatibility
from architecture_model.core.test_affinity import Subsystem, test_affinity_decompose  # noqa: E402, F401
from architecture_model.core.source_block_assign import auto_assign_source_blocks  # noqa: E402, F401
