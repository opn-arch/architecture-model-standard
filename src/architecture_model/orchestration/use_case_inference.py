"""Infer composite behaviors (use cases) from behavior trigger chains."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace as dc_replace

from architecture_model.core.types import (
    ArchitectureModel, Behavior, Entities, Relationship
)


def _find_chains(triggers: list[Relationship]) -> list[list[str]]:
    """Find linear chains in the triggers graph.
    
    A chain starts from a "head" — a behavior that is NOT a target of any trigger.
    Follows the graph forward until no more successors.
    """
    graph: dict[str, list[str]] = defaultdict(list)
    targets: set[str] = set()
    for rel in triggers:
        graph[rel.from_id].append(rel.to_id)
        targets.add(rel.to_id)
    
    heads = set(graph.keys()) - targets
    
    chains = []
    visited: set[str] = set()
    for head in sorted(heads):
        chain = []
        current = head
        while current and current not in visited:
            visited.add(current)
            chain.append(current)
            nexts = graph.get(current, [])
            current = nexts[0] if nexts else None
        if len(chain) >= 2:
            chains.append(chain)
    
    return chains


def infer_composite_behaviors(model: ArchitectureModel) -> ArchitectureModel:
    """Create composite behaviors (use cases) from trigger chains.
    
    For each chain of >=2 behaviors connected by triggers:
    1. Create a composite Behavior (UC-N) representing end-to-end use case
    2. Add contains relationships from composite to each chain member
    3. Composite inherits trigger and actor from chain head
    """
    triggers = [r for r in model.relationships if r.type == "triggers"]
    if not triggers:
        return model
    
    chains = _find_chains(triggers)
    if not chains:
        return model
    
    beh_index = {b.id: b for b in (model.entities.behaviors or [])}
    
    new_behaviors = []
    new_rels = []
    
    for i, chain in enumerate(chains, 1):
        head = beh_index.get(chain[0])
        if not head:
            continue
        
        composite = Behavior(
            id=f"UC-{i}",
            name=f"{head.name} (end-to-end)",
            status="ACTIVE",
            trigger=head.trigger,
            actor=head.actor,
            steps=[beh_index[bid].name for bid in chain if bid in beh_index],
        )
        new_behaviors.append(composite)
        
        for bid in chain:
            new_rels.append(Relationship(type="contains", from_id=composite.id, to_id=bid))
    
    all_behaviors = list(model.entities.behaviors or []) + new_behaviors
    all_rels = list(model.relationships) + new_rels
    
    new_entities = dc_replace(model.entities, behaviors=all_behaviors)
    return dc_replace(model, entities=new_entities, relationships=all_rels)
