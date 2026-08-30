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


# ── Standardized Shape Syntax ──────────────────────────────────
_SHAPES: dict[str, tuple[str, str]] = {
    "component":  ("[",   "]"),
    "capability": ("(",   ")"),
    "behavior":   ("{{", "}}"),
    "interface":  ("((",  "))"),
    "module":     ("[/",  "/]"),
    "actor":      ("([",  "])"),
    "constraint": ("{",   "}"),
    "layer":      ("[(",  ")]"),
    "stage":      ("[[",  "]]"),
}

_EDGES: dict[str, str] = {
    "realizes":       "==>",
    "contains":       "-.->",
    "depends-on":     "-->",
    "uses":           "-->",
    "exposes":        "-.->",
    "consumes":       "-->",
    "traces-to":      "-.->",
    "allocated-to":   "-.->",
    "constrained-by": "-.-x",
    "triggers":       "-->",
    "produces":       "==>",
    "subscribes-to":  "-.->",
    "transforms":     "==>",
    "satisfies":      "-.->",
    "derives-from":   "-.->",
    "verifies":       "-.->",
    "supersedes":     "-.-x",
    "migrates-to":    "-.->",
    "resolves":       "-->",
    "affects":        "-.->",
}

_CSS: dict[str, str] = {
    "cls_stage":  "fill:#4A90D9,stroke:#2C5F8A,color:#fff",
    "cls_comp":   "fill:#27AE60,stroke:#1E8449,color:#fff",
    "cls_cap":    "fill:#F39C12,stroke:#D68910,color:#fff",
    "cls_beh":    "fill:#8E44AD,stroke:#6C3483,color:#fff",
    "cls_iface":  "fill:#1ABC9C,stroke:#148F77,color:#fff",
    "cls_mod":    "fill:#95A5A6,stroke:#717D7E,color:#fff",
    "cls_actor":  "fill:#E74C8B,stroke:#C2185B,color:#fff",
    "cls_con":    "fill:#E74C3C,stroke:#C0392B,color:#fff",
    "cls_layer":  "fill:#16A085,stroke:#0E6655,color:#fff",
}

_ENTITY_TO_CSS: dict[str, str] = {
    "component": "cls_comp", "capability": "cls_cap", "behavior": "cls_beh",
    "interface": "cls_iface", "module": "cls_mod", "actor": "cls_actor",
    "constraint": "cls_con", "layer": "cls_layer", "stage": "cls_stage",
}


def shape(entity_type: str, node_id: str, name: str) -> str:
    """Render a Mermaid node using the standardized shape for *entity_type*."""
    sid = _sid(node_id)
    lbl = _label(name)
    prefix, suffix = _SHAPES.get(entity_type, ("[", "]"))
    return f"{sid}{prefix}{lbl}{suffix}"


def edge_style(rel_type: str) -> str:
    """Return Mermaid edge syntax for a relationship type."""
    arrow = _EDGES.get(rel_type, "-->")
    return f"{arrow}|{rel_type}|"


def css_classes() -> list[str]:
    """Return classDef lines for all entity-type colors."""
    return [f"    classDef {name} {style}" for name, style in _CSS.items()]


def _apply_class(node_id: str, entity_type: str) -> str:
    """Return a Mermaid class assignment line."""
    cls = _ENTITY_TO_CSS.get(entity_type, "")
    return f"    class {_sid(node_id)} {cls}" if cls else ""


def generate_context_diagram(model: "ArchitectureModel") -> str:
    """C4-style context: actors interacting with system via interfaces.

    Shows: actors (person/system shapes), interfaces inside system boundary,
    consumes/exposes edges.
    """
    lines = ["flowchart TB"]
    class_assignments: list[str] = []

    # System boundary
    project = getattr(model.meta, "project", "System")
    lines.append(f"    subgraph system[{_label(project)}]")
    for ifc in model.entities.interfaces:
        lines.append(f"        {shape('interface', ifc.id, ifc.name)}")
        class_assignments.append(_apply_class(ifc.id, "interface"))
    if not model.entities.interfaces:
        lines.append(f"        sys_core[{_label(project)}]")
    lines.append("    end")

    # Actors
    for actor in model.entities.actors:
        lines.append(f"    {shape('actor', actor.id, actor.name)}")
        class_assignments.append(_apply_class(actor.id, "actor"))

    # Edges: consumes (actor->interface), exposes (component->interface)
    for rel in model.relationships:
        rtype = _rel_type(rel)
        if rtype in ("consumes", "exposes"):
            lines.append(f"    {_sid(rel.from_id)} {edge_style(rtype)} {_sid(rel.to_id)}")

    # CSS classes
    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)

    return "\n".join(lines)


def generate_components_diagram(model: "ArchitectureModel") -> str:
    """Components grouped by layer, with realizes edges to capabilities.

    Shows: layers as subgraphs, components inside, realizes edges to capability nodes.
    """
    lines = ["flowchart TB"]
    class_assignments: list[str] = []

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
            lines.append(f"        {shape('component', cid, comp.name)}")
            class_assignments.append(_apply_class(cid, "component"))
        lines.append("    end")

    # Unassigned components
    if unassigned:
        lines.append("    subgraph ungrouped[Components]")
        for comp in unassigned:
            lines.append(f"        {shape('component', comp.id, comp.name)}")
            class_assignments.append(_apply_class(comp.id, "component"))
        lines.append("    end")

    # Capability nodes (rounded)
    for cap in model.entities.capabilities:
        lines.append(f"    {shape('capability', cap.id, cap.name)}")
        class_assignments.append(_apply_class(cap.id, "capability"))

    # Realizes edges
    for rel in model.relationships:
        if _rel_type(rel) == "realizes":
            lines.append(f"    {_sid(rel.from_id)} {edge_style('realizes')} {_sid(rel.to_id)}")

    # CSS classes
    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)

    return "\n".join(lines)


def generate_behaviors_diagram(model: "ArchitectureModel") -> str:
    """Behavior flow: triggers/contains relationships between behaviors.

    Shows: behaviors as stadium-shaped nodes, triggers/contains edges,
    traces-to from components.
    """
    lines = ["flowchart LR"]
    class_assignments: list[str] = []

    # Behavior nodes (hexagon shape)
    beh_ids = {b.id for b in model.entities.behaviors}
    for beh in model.entities.behaviors:
        lines.append(f"    {shape('behavior', beh.id, beh.name)}")
        class_assignments.append(_apply_class(beh.id, "behavior"))

    # Edges between behaviors
    for rel in model.relationships:
        rtype = _rel_type(rel)
        if rtype == "triggers" and rel.from_id in beh_ids and rel.to_id in beh_ids:
            lines.append(f"    {_sid(rel.from_id)} {edge_style('triggers')} {_sid(rel.to_id)}")
        elif rtype == "contains" and rel.from_id in beh_ids and rel.to_id in beh_ids:
            lines.append(f"    {_sid(rel.from_id)} {edge_style('contains')} {_sid(rel.to_id)}")

    # traces-to from components to behaviors
    for rel in model.relationships:
        if _rel_type(rel) == "traces-to" and rel.to_id in beh_ids:
            comp = next((c for c in model.entities.components if c.id == rel.from_id), None)
            if comp:
                lines.append(
                    f"    {shape('component', comp.id, comp.name)} {edge_style('traces-to')} {_sid(rel.to_id)}"
                )
                class_assignments.append(_apply_class(comp.id, "component"))

    # CSS classes
    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)

    return "\n".join(lines)


def generate_dependencies_diagram(model: "ArchitectureModel") -> str:
    """Inter-component dependency graph grouped by source_block.

    Shows: components grouped by source_block in subgraphs, depends-on edges.
    """
    lines = ["flowchart LR"]
    class_assignments: list[str] = []

    # Group by source_block
    source_block_groups: dict[str, list] = defaultdict(list)
    for comp in model.entities.components:
        fb = getattr(comp, "source_block", None) or "ungrouped"
        source_block_groups[fb].append(comp)

    # Capability names for source_block labels
    source_block_names: dict[str, str] = {}
    for cap in model.entities.capabilities:
        fb = getattr(cap, "source_block", None)
        if fb:
            source_block_names[fb] = cap.name

    # Emit subgraphs
    for fb in sorted(source_block_groups):
        comps = source_block_groups[fb]
        label = source_block_names.get(fb, fb)
        lines.append(f"    subgraph {_sid(fb)}[{_label(label)}]")
        for comp in comps:
            lines.append(f"        {shape('component', comp.id, comp.name)}")
            class_assignments.append(_apply_class(comp.id, "component"))
        lines.append("    end")

    # depends-on edges
    for rel in model.relationships:
        if _rel_type(rel) == "depends-on":
            lines.append(f"    {_sid(rel.from_id)} {edge_style('depends-on')} {_sid(rel.to_id)}")

    # CSS classes
    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)

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
