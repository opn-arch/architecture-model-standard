"""Generate Mermaid diagrams from architecture models.

Produces 4 standard views:
- context: C4-style actors → interfaces → system boundary
- components: grouped by layer, realizes edges to capabilities
- behaviors: flow with triggers/contains relationships
- dependencies: inter-component dependency graph
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ArchitectureModel


def _sid(node_id: str) -> str:
    """Sanitize ID for Mermaid (replace hyphens/dots with underscores)."""
    return node_id.replace("-", "_").replace(".", "_")


def _label(name: str) -> str:
    """Escape label for Mermaid (quote if contains special chars)."""
    # Replace characters that break Mermaid syntax
    name = name.replace('"', "'").replace("[", "(").replace("]", ")")
    # If label contains parens, arrows, or braces, wrap in quotes
    if any(c in name for c in "(){}->|"):
        return f'"{name}"'
    return name


def _rel_type(rel) -> str:
    """Get relationship type as string."""
    return getattr(rel.type, "value", rel.type)


def generate_context_diagram(model: "ArchitectureModel") -> str:
    """C4-style context: actors interacting with system via interfaces.

    Shows: actors (person/system shapes), interfaces inside system boundary,
    consumes/exposes edges.
    """
    lines = ["flowchart TB"]

    # System boundary
    project = getattr(model.meta, "project", "System")
    lines.append(f"    subgraph system[{_label(project)}]")
    for ifc in model.entities.interfaces:
        lines.append(f"        {_sid(ifc.id)}{{{{{_label(ifc.name)}}}}}")
    if not model.entities.interfaces:
        lines.append(f"        sys_core[{_label(project)}]")
    lines.append("    end")

    # Actors
    for actor in model.entities.actors:
        aid = _sid(actor.id)
        atype = getattr(actor.type, "value", actor.type) if actor.type else "system"
        if atype in ("person", "human"):
            lines.append(f"    {aid}[/{_label(actor.name)}\\]")
        else:
            lines.append(f"    {aid}[{_label(actor.name)}]")

    # Edges: consumes (actor->interface), exposes (component->interface)
    for rel in model.relationships:
        rtype = _rel_type(rel)
        if rtype == "consumes":
            lines.append(f"    {_sid(rel.from_id)} -->|consumes| {_sid(rel.to_id)}")
        elif rtype == "exposes":
            lines.append(f"    {_sid(rel.from_id)} -.->|exposes| {_sid(rel.to_id)}")

    return "\n".join(lines)


def generate_components_diagram(model: "ArchitectureModel") -> str:
    """Components grouped by layer, with realizes edges to capabilities.

    Shows: layers as subgraphs, components inside, realizes edges to capability nodes.
    """
    lines = ["flowchart TB"]

    # Build layer membership from contains relationships
    layer_ids = {l.id for l in model.entities.layers}
    comp_ids = {c.id for c in model.entities.components}
    layer_members: dict[str, list[str]] = defaultdict(list)

    for rel in model.relationships:
        if _rel_type(rel) == "contains" and rel.from_id in layer_ids and rel.to_id in comp_ids:
            layer_members[rel.from_id].append(rel.to_id)

    assigned = {cid for members in layer_members.values() for cid in members}
    unassigned = [c for c in model.entities.components if c.id not in assigned]

    # Emit layers as subgraphs
    layer_map = {l.id: l for l in model.entities.layers}
    for lid in sorted(layer_members):
        layer = layer_map[lid]
        lines.append(f"    subgraph {_sid(lid)}[{_label(layer.name)}]")
        for cid in layer_members[lid]:
            comp = next(c for c in model.entities.components if c.id == cid)
            lines.append(f"        {_sid(cid)}[{_label(comp.name)}]")
        lines.append("    end")

    # Unassigned components
    if unassigned:
        lines.append("    subgraph ungrouped[Components]")
        for comp in unassigned:
            lines.append(f"        {_sid(comp.id)}[{_label(comp.name)}]")
        lines.append("    end")

    # Capability nodes (rounded)
    for cap in model.entities.capabilities:
        lines.append(f"    {_sid(cap.id)}({_label(cap.name)})")

    # Realizes edges
    for rel in model.relationships:
        if _rel_type(rel) == "realizes":
            lines.append(f"    {_sid(rel.from_id)} ==>|realizes| {_sid(rel.to_id)}")

    return "\n".join(lines)


def generate_behaviors_diagram(model: "ArchitectureModel") -> str:
    """Behavior flow: triggers/contains relationships between behaviors.

    Shows: behaviors as stadium-shaped nodes, triggers/contains edges,
    traces-to from components.
    """
    lines = ["flowchart LR"]

    # Behavior nodes (stadium shape)
    beh_ids = {b.id for b in model.entities.behaviors}
    for beh in model.entities.behaviors:
        lines.append(f"    {_sid(beh.id)}([{_label(beh.name)}])")

    # Edges between behaviors
    for rel in model.relationships:
        rtype = _rel_type(rel)
        if rtype == "triggers" and rel.from_id in beh_ids and rel.to_id in beh_ids:
            lines.append(f"    {_sid(rel.from_id)} -->|triggers| {_sid(rel.to_id)}")
        elif rtype == "contains" and rel.from_id in beh_ids and rel.to_id in beh_ids:
            lines.append(f"    {_sid(rel.from_id)} -.->|contains| {_sid(rel.to_id)}")

    # traces-to from components to behaviors
    for rel in model.relationships:
        if _rel_type(rel) == "traces-to" and rel.to_id in beh_ids:
            comp = next((c for c in model.entities.components if c.id == rel.from_id), None)
            if comp:
                lines.append(
                    f"    {_sid(comp.id)}[{_label(comp.name)}] -.->|traces-to| {_sid(rel.to_id)}"
                )

    return "\n".join(lines)


def generate_dependencies_diagram(model: "ArchitectureModel") -> str:
    """Inter-component dependency graph grouped by f_block.

    Shows: components grouped by f_block in subgraphs, depends-on edges.
    """
    lines = ["flowchart LR"]

    # Group by f_block
    fblock_groups: dict[str, list] = defaultdict(list)
    for comp in model.entities.components:
        fb = getattr(comp, "f_block", None) or "ungrouped"
        fblock_groups[fb].append(comp)

    # Capability names for f_block labels
    fblock_names: dict[str, str] = {}
    for cap in model.entities.capabilities:
        fb = getattr(cap, "f_block", None)
        if fb:
            fblock_names[fb] = cap.name

    # Emit subgraphs
    for fb in sorted(fblock_groups):
        comps = fblock_groups[fb]
        label = fblock_names.get(fb, fb)
        lines.append(f"    subgraph {_sid(fb)}[{_label(label)}]")
        for comp in comps:
            lines.append(f"        {_sid(comp.id)}[{_label(comp.name)}]")
        lines.append("    end")

    # depends-on edges
    for rel in model.relationships:
        if _rel_type(rel) == "depends-on":
            lines.append(f"    {_sid(rel.from_id)} -->|depends-on| {_sid(rel.to_id)}")

    return "\n".join(lines)


def generate_all_diagrams(model: "ArchitectureModel", output_dir: Path) -> dict[str, Path]:
    """Generate all 4 standard diagrams and write to output_dir.

    Returns dict mapping diagram name to file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generators = {
        "context": generate_context_diagram,
        "components": generate_components_diagram,
        "behaviors": generate_behaviors_diagram,
        "dependencies": generate_dependencies_diagram,
    }
    paths = {}
    for name, gen_fn in generators.items():
        content = gen_fn(model)
        path = output_dir / f"{name}.mmd"
        path.write_text(content + "\n")
        paths[name] = path
    return paths
