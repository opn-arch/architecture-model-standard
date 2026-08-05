"""Automatic F-block assignment via dependency-graph clustering.

Bootstrap utility for models without f_block annotations.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    RelationType,
)


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
    sorted_comps = sorted(comps, key=lambda c: (-len(adj.get(c.id, set())), c.id))

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
