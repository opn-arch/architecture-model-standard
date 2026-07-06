"""Complexity scoring and system identification for architecture decomposition.

Provides functions to compute weighted complexity scores for components and
identify F-block groups that should be promoted to System entities.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

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
