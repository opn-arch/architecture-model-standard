"""Generate Mermaid diagrams from architecture models.

Produces 10 standard views:
- context: C4-style actors → interfaces → system boundary
- components: grouped by layer, realizes edges to capabilities
- behaviors: flow with triggers/contains relationships
- dependencies: inter-component dependency graph
- pipeline-flow: 10-stage pipeline with LLM refinement loop (static)
- entity-lifecycle: entity evolution across pipeline stages (static)
- data-flow: produces → transforms → subscribes-to chains
- constraint-map: constraint allocation to components
- traceability: capabilities → components → behaviors tracing
- decomposition: system → layers → components hierarchy
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


def generate_pipeline_flow_diagram() -> str:
    """Pipeline stage flow with LLM refinement loop. Static diagram."""
    stages = [
        ("S1", "Observe", "Inventory"),
        ("S2", "Infer", "Capabilities"),
        ("S3", "Allocate", "Components"),
        ("S4", "Relate", "Relationships"),
        ("S5", "Specify", "Interfaces"),
        ("S6", "Contract", "Test Contracts"),
        ("S7", "Validate", "Score"),
        ("S8", "Decompose", "Systems"),
        ("S9", "Synthesize", "Sub-models"),
        ("S10", "Emit", "Artifacts"),
    ]
    lines = ["flowchart LR"]
    class_assignments: list[str] = []

    # Stage nodes
    for sid, name, _output in stages:
        lines.append(f"    {shape('stage', sid, name)}")
        class_assignments.append(_apply_class(sid, "stage"))

    # Sequential connections with output labels
    for i in range(len(stages) - 1):
        sid_from = stages[i][0]
        sid_to = stages[i + 1][0]
        output = stages[i][2]
        lines.append(f"    {sid_from} -->|{output}| {sid_to}")

    # LLM refinement loop subgraph
    lines.append("    subgraph llm_loop[LLM Refinement Loop]")
    lines.append(f"        {shape('component', 'LLM_reinfer', 'LLM Re-inference')}")
    lines.append(f"        {shape('component', 'LLM_norm', 'Normalize')}")
    lines.append(f"        {shape('component', 'LLM_apply', 'Apply')}")
    lines.append("        LLM_reinfer --> LLM_norm --> LLM_apply")
    lines.append("    end")
    class_assignments.append(_apply_class("LLM_reinfer", "component"))
    class_assignments.append(_apply_class("LLM_norm", "component"))
    class_assignments.append(_apply_class("LLM_apply", "component"))

    # Stages S2-S5 connect to LLM loop
    for sid in ["S2", "S3", "S4", "S5"]:
        lines.append(f"    {sid} -.-> LLM_reinfer")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_entity_lifecycle_diagram() -> str:
    """How entities evolve across pipeline stages. Static illustrative diagram."""
    lines = ["flowchart LR"]
    class_assignments: list[str] = []

    # S1: Observe — modules discovered
    lines.append("    subgraph s1[Observe]")
    lines.append(f"        {shape('module', 'mod1', 'parser.py')}")
    lines.append(f"        {shape('module', 'mod2', 'validator.py')}")
    lines.append("    end")
    class_assignments.extend([_apply_class("mod1", "module"), _apply_class("mod2", "module")])

    # S2: Infer — capabilities inferred
    lines.append("    subgraph s2[Infer]")
    lines.append(f"        {shape('capability', 'cap1', 'Parsing')}")
    lines.append("    end")
    class_assignments.append(_apply_class("cap1", "capability"))

    # S3: Allocate — components formed
    lines.append("    subgraph s3[Allocate]")
    lines.append(f"        {shape('component', 'comp1', 'Parser Component')}")
    lines.append("    end")
    class_assignments.append(_apply_class("comp1", "component"))

    # S4: Relate — relationships added
    lines.append("    subgraph s4[Relate]")
    lines.append(f"        {shape('behavior', 'beh1', 'Parse Flow')}")
    lines.append("    end")
    class_assignments.append(_apply_class("beh1", "behavior"))

    # S5: Specify — interfaces exposed
    lines.append("    subgraph s5[Specify]")
    lines.append(f"        {shape('interface', 'if1', 'Parse API')}")
    lines.append("    end")
    class_assignments.append(_apply_class("if1", "interface"))

    # S6: Contract — test contracts
    lines.append("    subgraph s6[Contract]")
    lines.append(f"        {shape('constraint', 'con1', 'Test Contract')}")
    lines.append("    end")
    class_assignments.append(_apply_class("con1", "constraint"))

    # Flow between stages
    lines.append("    mod1 --> cap1 --> comp1 --> beh1 --> if1 --> con1")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_data_flow_diagram(model: "ArchitectureModel") -> str:
    """Data/event flow: produces → transforms → subscribes-to chains."""
    lines = ["flowchart LR"]
    class_assignments: list[str] = []
    data_types = {"produces", "subscribes-to", "transforms"}

    # Collect involved node IDs
    involved: set[str] = set()
    data_rels = []
    for rel in model.relationships:
        rtype = _rel_type(rel)
        if rtype in data_types:
            involved.add(rel.from_id)
            involved.add(rel.to_id)
            data_rels.append(rel)

    # Build ID→(type, name) map
    entity_map: dict[str, tuple[str, str]] = {}
    for comp in model.entities.components:
        entity_map[comp.id] = ("component", comp.name)
    for ifc in model.entities.interfaces:
        entity_map[ifc.id] = ("interface", ifc.name)
    for cap in model.entities.capabilities:
        entity_map[cap.id] = ("capability", cap.name)

    # Render nodes
    for nid in sorted(involved):
        if nid in entity_map:
            etype, ename = entity_map[nid]
            lines.append(f"    {shape(etype, nid, ename)}")
            class_assignments.append(_apply_class(nid, etype))

    # Render edges
    for rel in data_rels:
        rtype = _rel_type(rel)
        lines.append(f"    {_sid(rel.from_id)} {edge_style(rtype)} {_sid(rel.to_id)}")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_constraint_map_diagram(model: "ArchitectureModel") -> str:
    """Constraint allocation: which constraints apply to which components."""
    lines = ["flowchart LR"]
    class_assignments: list[str] = []

    constraint_rels = [r for r in model.relationships if _rel_type(r) == "constrained-by"]

    # Build maps
    con_map = {c.id: c for c in model.entities.constraints}
    comp_map = {c.id: c for c in model.entities.components}

    involved_cons: set[str] = set()
    involved_comps: set[str] = set()
    for rel in constraint_rels:
        involved_comps.add(rel.from_id)
        involved_cons.add(rel.to_id)

    # Render constraint nodes (diamond shape)
    for cid in sorted(involved_cons):
        if cid in con_map:
            lines.append(f"    {shape('constraint', cid, con_map[cid].name)}")
            class_assignments.append(_apply_class(cid, "constraint"))

    # Render component nodes
    for cid in sorted(involved_comps):
        if cid in comp_map:
            lines.append(f"    {shape('component', cid, comp_map[cid].name)}")
            class_assignments.append(_apply_class(cid, "component"))

    # Edges
    for rel in constraint_rels:
        lines.append(f"    {_sid(rel.from_id)} {edge_style('constrained-by')} {_sid(rel.to_id)}")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_traceability_diagram(model: "ArchitectureModel") -> str:
    """Requirements → capabilities → components → behaviors traceability."""
    trace_types = {"realizes", "traces-to", "satisfies", "verifies", "derives-from"}
    lines = ["flowchart TD"]
    class_assignments: list[str] = []

    trace_rels = [r for r in model.relationships if _rel_type(r) in trace_types]

    # Collect involved IDs by entity type
    cap_ids = {c.id for c in model.entities.capabilities}
    comp_ids = {c.id for c in model.entities.components}
    beh_ids = {b.id for b in model.entities.behaviors}

    involved_caps = set()
    involved_comps = set()
    involved_behs = set()
    for rel in trace_rels:
        for nid in (rel.from_id, rel.to_id):
            if nid in cap_ids:
                involved_caps.add(nid)
            elif nid in comp_ids:
                involved_comps.add(nid)
            elif nid in beh_ids:
                involved_behs.add(nid)

    cap_map = {c.id: c for c in model.entities.capabilities}
    comp_map = {c.id: c for c in model.entities.components}
    beh_map = {b.id: b for b in model.entities.behaviors}

    # Tier subgraphs
    if involved_caps:
        lines.append("    subgraph caps[Capabilities]")
        for cid in sorted(involved_caps):
            lines.append(f"        {shape('capability', cid, cap_map[cid].name)}")
            class_assignments.append(_apply_class(cid, "capability"))
        lines.append("    end")

    if involved_comps:
        lines.append("    subgraph comps[Components]")
        for cid in sorted(involved_comps):
            lines.append(f"        {shape('component', cid, comp_map[cid].name)}")
            class_assignments.append(_apply_class(cid, "component"))
        lines.append("    end")

    if involved_behs:
        lines.append("    subgraph behs[Behaviors]")
        for bid in sorted(involved_behs):
            lines.append(f"        {shape('behavior', bid, beh_map[bid].name)}")
            class_assignments.append(_apply_class(bid, "behavior"))
        lines.append("    end")

    # Edges
    for rel in trace_rels:
        rtype = _rel_type(rel)
        lines.append(f"    {_sid(rel.from_id)} {edge_style(rtype)} {_sid(rel.to_id)}")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_decomposition_diagram(model: "ArchitectureModel") -> str:
    """System → layers → components hierarchy tree."""
    lines = ["flowchart TD"]
    class_assignments: list[str] = []

    project = getattr(model.meta, "project", "System")
    root_id = "ROOT"
    lines.append(f"    {shape('stage', root_id, project)}")
    class_assignments.append(_apply_class(root_id, "stage"))

    layer_map = {l.id: l for l in model.entities.layers}
    comp_map = {c.id: c for c in model.entities.components}

    # Build contains edges
    layer_comps: dict[str, list[str]] = defaultdict(list)
    layer_ids = set(layer_map.keys())
    comp_ids = set(comp_map.keys())
    assigned_comps: set[str] = set()

    for rel in model.relationships:
        if _rel_type(rel) == "contains":
            if rel.from_id in layer_ids and rel.to_id in comp_ids:
                layer_comps[rel.from_id].append(rel.to_id)
                assigned_comps.add(rel.to_id)

    # Layers
    for lid, layer in sorted(layer_map.items()):
        lines.append(f"    {shape('layer', lid, layer.name)}")
        class_assignments.append(_apply_class(lid, "layer"))
        lines.append(f"    {_sid(root_id)} {edge_style('contains')} {_sid(lid)}")

        for cid in layer_comps.get(lid, []):
            lines.append(f"    {shape('component', cid, comp_map[cid].name)}")
            class_assignments.append(_apply_class(cid, "component"))
            lines.append(f"    {_sid(lid)} {edge_style('contains')} {_sid(cid)}")

    # Unassigned components
    for comp in model.entities.components:
        if comp.id not in assigned_comps:
            lines.append(f"    {shape('component', comp.id, comp.name)}")
            class_assignments.append(_apply_class(comp.id, "component"))
            lines.append(f"    {_sid(root_id)} {edge_style('contains')} {_sid(comp.id)}")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_component_detail_diagram(model: "ArchitectureModel", component_id: str) -> str:
    """Generate a detail diagram for a single component.

    Shows the component's capabilities, interfaces, behaviors,
    dependencies, source files, and containing layer.
    """
    # Find the component
    comp = None
    for c in model.entities.components:
        if c.id == component_id:
            comp = c
            break
    if comp is None:
        return f"flowchart TB\n    not_found[Component {_label(component_id)} not found]"

    lines = ["flowchart TB"]
    class_assignments: list[str] = []

    # Central component node
    lines.append(f"    {shape('component', comp.id, comp.name)}")
    class_assignments.append(_apply_class(comp.id, "component"))

    # Build lookup maps
    entity_map: dict[str, tuple[str, str]] = {}  # id -> (type, name)
    for c in model.entities.components:
        entity_map[c.id] = ("component", c.name)
    for c in model.entities.capabilities:
        entity_map[c.id] = ("capability", c.name)
    for i in model.entities.interfaces:
        entity_map[i.id] = ("interface", i.name)
    for b in model.entities.behaviors:
        entity_map[b.id] = ("behavior", b.name)
    for la in model.entities.layers:
        entity_map[la.id] = ("layer", la.name)

    # Containing layer
    for rel in model.relationships:
        rt = _rel_type(rel)
        if rt == "contains" and rel.to_id == component_id and rel.from_id in entity_map:
            etype, ename = entity_map[rel.from_id]
            if etype == "layer":
                lines.append(f"    {shape('layer', rel.from_id, ename)}")
                class_assignments.append(_apply_class(rel.from_id, "layer"))
                lines.append(f"    {_sid(rel.from_id)} {edge_style('contains')} {_sid(comp.id)}")

    # Realized capabilities
    caps = [(rel.to_id, entity_map[rel.to_id]) for rel in model.relationships
            if rel.from_id == component_id and _rel_type(rel) == "realizes" and rel.to_id in entity_map]
    if caps:
        lines.append(f"    subgraph caps[Capabilities]")
        for cid, (etype, ename) in caps:
            lines.append(f"        {shape('capability', cid, ename)}")
            class_assignments.append(_apply_class(cid, "capability"))
        lines.append(f"    end")
        for cid, _ in caps:
            lines.append(f"    {_sid(comp.id)} {edge_style('realizes')} {_sid(cid)}")

    # Exposed interfaces
    ifaces = [(rel.to_id, entity_map[rel.to_id]) for rel in model.relationships
              if rel.from_id == component_id and _rel_type(rel) == "exposes" and rel.to_id in entity_map]
    if ifaces:
        lines.append(f"    subgraph ifaces[Interfaces]")
        for iid, (etype, ename) in ifaces:
            lines.append(f"        {shape('interface', iid, ename)}")
            class_assignments.append(_apply_class(iid, "interface"))
        lines.append(f"    end")
        for iid, _ in ifaces:
            lines.append(f"    {_sid(comp.id)} {edge_style('exposes')} {_sid(iid)}")

    # Traced behaviors
    behs = [(rel.to_id, entity_map[rel.to_id]) for rel in model.relationships
            if rel.from_id == component_id and _rel_type(rel) == "traces-to" and rel.to_id in entity_map]
    if behs:
        lines.append(f"    subgraph behs[Behaviors]")
        for bid, (etype, ename) in behs:
            lines.append(f"        {shape('behavior', bid, ename)}")
            class_assignments.append(_apply_class(bid, "behavior"))
        lines.append(f"    end")
        for bid, _ in behs:
            lines.append(f"    {_sid(comp.id)} {edge_style('traces-to')} {_sid(bid)}")
            lines.append(f"    click {_sid(bid)} \"use-case-{bid}.mmd\"")

    # Dependencies
    deps = [(rel.to_id, entity_map[rel.to_id]) for rel in model.relationships
            if rel.from_id == component_id and _rel_type(rel) == "depends-on" and rel.to_id in entity_map]
    for did, (etype, ename) in deps:
        lines.append(f"    {shape('component', did, ename)}")
        class_assignments.append(_apply_class(did, "component"))
        lines.append(f"    {_sid(comp.id)} {edge_style('depends-on')} {_sid(did)}")
        lines.append(f"    click {_sid(did)} \"component-{did}.mmd\"")

    # Source files
    source_files = getattr(comp, "files", None) or []
    if source_files:
        lines.append(f"    subgraph files[Source Files]")
        for sf in source_files:
            fid = _sid(f"file_{sf}")
            lines.append(f"        {shape('module', fid, sf)}")
            class_assignments.append(_apply_class(fid, "module"))
        lines.append(f"    end")
        lines.append(f"    {_sid(comp.id)} -.-> files")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_use_case_diagram(model: "ArchitectureModel", behavior_id: str) -> str:
    """Generate a use-case diagram for a single behavior.

    Shows the behavior's sub-behaviors, implementing components,
    and trigger relationships.
    """
    # Find the behavior
    beh = None
    for b in model.entities.behaviors:
        if b.id == behavior_id:
            beh = b
            break
    if beh is None:
        return f"flowchart TB\n    not_found[Behavior {_label(behavior_id)} not found]"

    lines = ["flowchart TB"]
    class_assignments: list[str] = []

    # Central behavior node
    lines.append(f"    {shape('behavior', beh.id, beh.name)}")
    class_assignments.append(_apply_class(beh.id, "behavior"))

    # Build entity maps
    comp_map = {c.id: c.name for c in model.entities.components}
    beh_map = {b.id: b.name for b in model.entities.behaviors}

    # Implementing components (reverse traces-to)
    for rel in model.relationships:
        if _rel_type(rel) == "traces-to" and rel.to_id == behavior_id and rel.from_id in comp_map:
            lines.append(f"    {shape('component', rel.from_id, comp_map[rel.from_id])}")
            class_assignments.append(_apply_class(rel.from_id, "component"))
            lines.append(f"    {_sid(rel.from_id)} {edge_style('traces-to')} {_sid(beh.id)}")
            lines.append(f"    click {_sid(rel.from_id)} \"component-{rel.from_id}.mmd\"")

    # Sub-behaviors
    sub_behs = [(rel.to_id, beh_map[rel.to_id]) for rel in model.relationships
                if rel.from_id == behavior_id and _rel_type(rel) == "contains" and rel.to_id in beh_map]
    if sub_behs:
        lines.append(f"    subgraph sub[Sub-behaviors]")
        for sid, sname in sub_behs:
            lines.append(f"        {shape('behavior', sid, sname)}")
            class_assignments.append(_apply_class(sid, "behavior"))
        lines.append(f"    end")
        for sid, sname in sub_behs:
            lines.append(f"    {_sid(beh.id)} {edge_style('contains')} {_sid(sid)}")
            lines.append(f"    click {_sid(sid)} \"use-case-{sid}.mmd\"")

    # Triggered-by (other behaviors that trigger this one)
    for rel in model.relationships:
        if _rel_type(rel) == "triggers" and rel.to_id == behavior_id and rel.from_id in beh_map:
            lines.append(f"    {shape('behavior', rel.from_id, beh_map[rel.from_id])}")
            class_assignments.append(_apply_class(rel.from_id, "behavior"))
            lines.append(f"    {_sid(rel.from_id)} {edge_style('triggers')} {_sid(beh.id)}")

    # Triggers (behaviors this one triggers)
    for rel in model.relationships:
        if _rel_type(rel) == "triggers" and rel.from_id == behavior_id and rel.to_id in beh_map:
            lines.append(f"    {shape('behavior', rel.to_id, beh_map[rel.to_id])}")
            class_assignments.append(_apply_class(rel.to_id, "behavior"))
            lines.append(f"    {_sid(beh.id)} {edge_style('triggers')} {_sid(rel.to_id)}")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_all_diagrams(model: "ArchitectureModel", output_dir: Path) -> dict[str, Path]:
    """Generate all 10 standard diagrams and write to output_dir.

    Returns dict mapping diagram name to file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generators = {
        "context": generate_context_diagram,
        "components": generate_components_diagram,
        "behaviors": generate_behaviors_diagram,
        "dependencies": generate_dependencies_diagram,
        "data-flow": lambda m: generate_data_flow_diagram(m),
        "constraint-map": lambda m: generate_constraint_map_diagram(m),
        "traceability": lambda m: generate_traceability_diagram(m),
        "decomposition": lambda m: generate_decomposition_diagram(m),
    }
    # Static diagrams (no model needed)
    static_generators = {
        "pipeline-flow": generate_pipeline_flow_diagram,
        "entity-lifecycle": generate_entity_lifecycle_diagram,
    }
    paths = {}
    for name, gen_fn in generators.items():
        content = gen_fn(model)
        path = output_dir / f"{name}.mmd"
        path.write_text(content + "\n")
        paths[name] = path
    for name, gen_fn in static_generators.items():
        content = gen_fn()
        path = output_dir / f"{name}.mmd"
        path.write_text(content + "\n")
        paths[name] = path
    return paths
