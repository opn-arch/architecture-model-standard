"""PlantUML diagram generation from architecture model data.

Generates deterministic PlantUML syntax strings from model entities and
relationships. These can be embedded in documentation or rendered by any
PlantUML-compatible tool.
"""

from __future__ import annotations

from architecture_model.core.types import (
    ArchitectureModel,
    ActorType,
    Behavior,
    RelationType,
)


def _sanitize_id(id_str: str) -> str:
    """Sanitize an entity ID for use as a PlantUML identifier.

    Replace hyphens, dots, and spaces with underscores.
    """
    return id_str.replace("-", "_").replace(".", "_").replace(" ", "_")


def generate_component_diagram(model: ArchitectureModel) -> str:
    """Generate a C4-style component diagram showing system structure.

    Groups components by layer, renders actors, and shows
    depends-on/exposes/consumes relationships.
    """
    lines: list[str] = []
    lines.append("@startuml")
    lines.append("!include <C4/C4_Component>")
    lines.append("")
    lines.append(f"title Component Diagram - {model.meta.project}")
    lines.append("")

    # Actors
    for actor in model.entities.actors:
        aid = _sanitize_id(actor.id)
        if actor.type == ActorType.HUMAN:
            lines.append(f'Person({aid}, "{actor.name}")')
        else:
            lines.append(f'System_Ext({aid}, "{actor.name}")')

    if model.entities.actors:
        lines.append("")

    # Group components by layer
    layer_ids = {layer.id for layer in model.entities.layers}
    layer_map: dict[str, list] = {layer.id: [] for layer in model.entities.layers}
    unlayered: list = []

    for comp in model.entities.components:
        if comp.layer and comp.layer in layer_ids:
            layer_map[comp.layer].append(comp)
        else:
            unlayered.append(comp)

    # Render layer boundaries with their components
    for layer in model.entities.layers:
        comps = layer_map.get(layer.id, [])
        if not comps:
            continue
        lid = _sanitize_id(layer.id)
        lines.append(f'Container_Boundary({lid}, "{layer.name}") {{')
        for comp in comps:
            cid = _sanitize_id(comp.id)
            tech = f', "{comp.technology}"' if comp.technology else ', ""'
            lines.append(f'    Component({cid}, "{comp.name}"{tech}, "{comp.kind.value}")')
        lines.append("}")
        lines.append("")

    # Components without layers
    for comp in unlayered:
        cid = _sanitize_id(comp.id)
        tech = f', "{comp.technology}"' if comp.technology else ', ""'
        lines.append(f'Component({cid}, "{comp.name}"{tech}, "{comp.kind.value}")')

    if unlayered:
        lines.append("")

    # Relationships (only depends-on, exposes, consumes)
    allowed_types = {RelationType.DEPENDS_ON, RelationType.EXPOSES, RelationType.CONSUMES}
    rels_rendered = False
    for rel in model.relationships:
        if rel.type in allowed_types:
            fid = _sanitize_id(rel.from_id)
            tid = _sanitize_id(rel.to_id)
            lines.append(f'Rel({fid}, {tid}, "{rel.type.value}")')
            rels_rendered = True

    if rels_rendered:
        lines.append("")

    lines.append("@enduml")
    return "\n".join(lines)


def generate_dependency_diagram(model: ArchitectureModel) -> str:
    """Generate a dependency graph showing component relationships.

    Simpler than C4 — plain PlantUML with rectangles and arrows.
    Only includes entities that participate in at least one relationship.
    """
    lines: list[str] = []
    lines.append("@startuml")
    lines.append(f"title Dependency Graph - {model.meta.project}")
    lines.append("")

    # Filter to relevant relationship types
    allowed_types = {RelationType.DEPENDS_ON, RelationType.EXPOSES, RelationType.CONSUMES}
    relevant_rels = [r for r in model.relationships if r.type in allowed_types]

    # Collect IDs that participate in relationships
    connected_ids: set[str] = set()
    for rel in relevant_rels:
        connected_ids.add(rel.from_id)
        connected_ids.add(rel.to_id)

    if not connected_ids:
        lines.append("@enduml")
        return "\n".join(lines)

    # Build name lookup from all entity types
    name_lookup: dict[str, str] = {}
    for comp in model.entities.components:
        name_lookup[comp.id] = comp.name
    for iface in model.entities.interfaces:
        name_lookup[iface.id] = iface.name

    # Render rectangles for connected entities
    for entity_id in sorted(connected_ids):
        sid = _sanitize_id(entity_id)
        name = name_lookup.get(entity_id, entity_id)
        lines.append(f'rectangle "{name}" as {sid}')

    lines.append("")

    # Render arrows
    for rel in relevant_rels:
        fid = _sanitize_id(rel.from_id)
        tid = _sanitize_id(rel.to_id)
        if rel.type == RelationType.DEPENDS_ON:
            lines.append(f"{fid} --> {tid} : depends-on")
        elif rel.type == RelationType.EXPOSES:
            lines.append(f"{fid} ..> {tid} : exposes")
        elif rel.type == RelationType.CONSUMES:
            lines.append(f"{fid} ..> {tid} : consumes")

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def generate_sequence_diagram(behavior: Behavior, model: ArchitectureModel) -> str:
    """Generate a sequence diagram from a behavior's steps.

    Returns empty string if behavior has no steps.
    """
    if not behavior.steps:
        return ""

    lines: list[str] = []
    lines.append("@startuml")
    lines.append(f"title {behavior.name}")
    lines.append("")

    # Resolve actor if present
    actor_name: str | None = None
    actor_alias: str | None = None
    if behavior.actor:
        # Look up actor entity by ID
        for act in model.entities.actors:
            if act.id == behavior.actor:
                actor_name = act.name
                actor_alias = _sanitize_id(act.id)
                break
        if not actor_name:
            # Use raw actor ID as fallback
            actor_name = behavior.actor
            actor_alias = _sanitize_id(behavior.actor)

        lines.append(f'actor "{actor_name}" as {actor_alias}')

    # Add System participant for generic step mapping
    lines.append(f'participant "System" as System')
    lines.append("")

    # Render steps as messages
    source = actor_alias if actor_alias else "System"
    for i, step in enumerate(behavior.steps):
        if i == 0 and actor_alias:
            lines.append(f"{source} -> System : {step}")
        else:
            lines.append(f"System -> System : {step}")

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def generate_all_diagrams(model: ArchitectureModel) -> dict[str, str]:
    """Generate all applicable diagrams for the model.

    Returns dict mapping diagram name to PlantUML string.
    Only includes diagrams where there's enough data.
    """
    result: dict[str, str] = {}

    # Component diagram: requires at least 2 components
    if len(model.entities.components) >= 2:
        result["component-diagram"] = generate_component_diagram(model)

    # Dependency graph: requires at least 1 relevant relationship
    allowed_types = {RelationType.DEPENDS_ON, RelationType.EXPOSES, RelationType.CONSUMES}
    has_dep_rels = any(r.type in allowed_types for r in model.relationships)
    if has_dep_rels:
        result["dependency-graph"] = generate_dependency_diagram(model)

    # Sequence diagrams: one per behavior with steps
    for behavior in model.entities.behaviors:
        if behavior.steps:
            diagram = generate_sequence_diagram(behavior, model)
            if diagram:
                result[f"sequence-{behavior.id}"] = diagram

    return result
