"""Reconstruct behaviors from capabilities and component relationships.

For each capability, generates a behavior with:
- Name derived from capability name
- Intent from capability description
- Steps derived from realizing components
- trigger, actor set to reasonable defaults
"""
from architecture_model.core.types import (
    ArchitectureModel, Behavior, Relationship, RelationType, Status,
)


def reconstruct_behaviors(model: ArchitectureModel) -> tuple[list[Behavior], list[Relationship]]:
    """Generate behaviors for capabilities that lack them."""
    existing_cap_ids = set()
    for r in model.relationships:
        if r.type == RelationType.TRACES_TO:
            existing_cap_ids.add(r.to_id)

    behaviors = []
    rels = []
    cap_to_components = {}
    for r in model.relationships:
        if r.type == RelationType.REALIZES:
            cap_to_components.setdefault(r.to_id, []).append(r.from_id)

    comp_map = {c.id: c for c in model.entities.components}

    for i, cap in enumerate(model.entities.capabilities, 1):
        if cap.id in existing_cap_ids:
            continue
        comp_ids = cap_to_components.get(cap.id, [])
        comp_names = [comp_map[cid].name for cid in comp_ids if cid in comp_map]
        steps = [f"Invoke {name}" for name in comp_names] or [f"Execute {cap.name}"]

        beh = Behavior(
            id=f"BEH-R{i}",
            name=f"Perform {cap.name}",
            status=Status.ACTIVE,
            intent=cap.description or f"Behavior for {cap.name}",
            trigger=f"User or system requests {cap.name.lower()}",
            steps=steps,
        )
        behaviors.append(beh)
        rels.append(Relationship(
            type=RelationType.TRACES_TO,
            from_id=beh.id, to_id=cap.id,
            description=f"{beh.name} traces to {cap.name}",
        ))

    return behaviors, rels
