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

import re
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
            lines.append(f"        click {_sid(cid)} \"component-{cid}.mmd\" \"View component detail\"")
            class_assignments.append(_apply_class(cid, "component"))
        lines.append("    end")

    # Unassigned components
    if unassigned:
        lines.append("    subgraph ungrouped[Components]")
        for comp in unassigned:
            lines.append(f"        {shape('component', comp.id, comp.name)}")
            lines.append(f"        click {_sid(comp.id)} \"component-{comp.id}.mmd\" \"View component detail\"")
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
        lines.append(f"    click {_sid(beh.id)} \"use-case-{beh.id}.mmd\" \"View use case detail\"")
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


def generate_icd_diagram(model: "ArchitectureModel") -> str:
    """Interface Control Document: all interfaces with provider/consumer edges.

    Shows: interfaces as central nodes, provider components (exposes),
    consumer actors/components (consumes), grouped by provider component.
    """
    lines = ["flowchart LR"]
    class_assignments: list[str] = []

    comp_map = {c.id: c for c in model.entities.components}
    ifc_map = {i.id: i for i in model.entities.interfaces}
    actor_map = {a.id: a for a in model.entities.actors}
    entity_map: dict[str, tuple[str, str]] = {}
    for c in model.entities.components:
        entity_map[c.id] = ("component", c.name)
    for a in model.entities.actors:
        entity_map[a.id] = ("actor", a.name)
    for i in model.entities.interfaces:
        entity_map[i.id] = ("interface", i.name)

    # Build provider->interfaces mapping
    provider_ifaces: dict[str, list[str]] = defaultdict(list)
    for rel in model.relationships:
        if _rel_type(rel) == "exposes" and rel.to_id in ifc_map:
            provider_ifaces[rel.from_id].append(rel.to_id)

    # Group interfaces by provider into subgraphs
    rendered_ifaces: set[str] = set()
    for provider_id, iface_ids in sorted(provider_ifaces.items()):
        provider = entity_map.get(provider_id)
        if not provider:
            continue
        ptype, pname = provider
        lines.append(f'    subgraph {_sid(provider_id)}["{_label(pname)}"]')
        for iid in iface_ids:
            ifc = ifc_map.get(iid)
            if ifc:
                lines.append(f"        {shape('interface', iid, ifc.name)}")
                class_assignments.append(_apply_class(iid, "interface"))
                rendered_ifaces.add(iid)
        lines.append("    end")
        class_assignments.append(_apply_class(provider_id, "component"))

    # Orphan interfaces (no provider)
    orphans = [i for i in model.entities.interfaces if i.id not in rendered_ifaces]
    if orphans:
        lines.append('    subgraph orphan["Unassigned Interfaces"]')
        for ifc in orphans:
            lines.append(f"        {shape('interface', ifc.id, ifc.name)}")
            class_assignments.append(_apply_class(ifc.id, "interface"))
        lines.append("    end")

    # Consumer edges
    for rel in model.relationships:
        if _rel_type(rel) == "consumes" and rel.to_id in ifc_map and rel.from_id in entity_map:
            ftype, fname = entity_map[rel.from_id]
            lines.append(f"    {shape(ftype, rel.from_id, fname)}")
            class_assignments.append(_apply_class(rel.from_id, ftype))
            lines.append(f"    {_sid(rel.from_id)} {edge_style('consumes')} {_sid(rel.to_id)}")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_requirements_allocation_diagram(model: "ArchitectureModel") -> str:
    """Requirements Allocation: requirements/constraints mapped to components.

    Shows: requirements as nodes, satisfies edges to components,
    constrained-by edges from components to constraints.
    """
    lines = ["flowchart LR"]
    class_assignments: list[str] = []

    req_map = {r.id: r for r in model.entities.requirements}
    con_map = {c.id: c for c in model.entities.constraints}
    comp_map = {c.id: c for c in model.entities.components}

    # Satisfies edges (component -> requirement)
    rendered_reqs: set[str] = set()
    rendered_comps: set[str] = set()
    for rel in model.relationships:
        if _rel_type(rel) == "satisfies":
            if rel.from_id in comp_map and rel.to_id in req_map:
                if rel.to_id not in rendered_reqs:
                    req = req_map[rel.to_id]
                    lines.append(f"    {shape('constraint', rel.to_id, req.name)}")
                    class_assignments.append(_apply_class(rel.to_id, "constraint"))
                    rendered_reqs.add(rel.to_id)
                if rel.from_id not in rendered_comps:
                    comp = comp_map[rel.from_id]
                    lines.append(f"    {shape('component', rel.from_id, comp.name)}")
                    class_assignments.append(_apply_class(rel.from_id, "component"))
                    rendered_comps.add(rel.from_id)
                lines.append(f"    {_sid(rel.from_id)} {edge_style('satisfies')} {_sid(rel.to_id)}")

    # Constrained-by edges
    rendered_cons: set[str] = set()
    for rel in model.relationships:
        if _rel_type(rel) == "constrained-by":
            if rel.from_id in comp_map and rel.to_id in con_map:
                if rel.to_id not in rendered_cons:
                    con = con_map[rel.to_id]
                    lines.append(f"    {shape('constraint', rel.to_id, con.name)}")
                    class_assignments.append(_apply_class(rel.to_id, "constraint"))
                    rendered_cons.add(rel.to_id)
                if rel.from_id not in rendered_comps:
                    comp = comp_map[rel.from_id]
                    lines.append(f"    {shape('component', rel.from_id, comp.name)}")
                    class_assignments.append(_apply_class(rel.from_id, "component"))
                    rendered_comps.add(rel.from_id)
                lines.append(f"    {_sid(rel.from_id)} {edge_style('constrained-by')} {_sid(rel.to_id)}")

    # If nothing rendered, show a placeholder
    if not rendered_reqs and not rendered_cons:
        lines.append("    none[No requirements or constraints allocated]")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_system_decomposition_diagram(model: "ArchitectureModel") -> str:
    """System Decomposition (Physical Architecture): systems containing components.

    Shows: system entities as subgraphs containing their components,
    with inter-system dependency edges.
    """
    lines = ["flowchart TB"]
    class_assignments: list[str] = []

    sys_map = {s.id: s for s in model.entities.systems}
    comp_map = {c.id: c for c in model.entities.components}

    # Build system -> component membership
    sys_components: dict[str, list[str]] = defaultdict(list)
    for sys in model.entities.systems:
        # Use component_ids field if available
        for cid in getattr(sys, "component_ids", []):
            if cid in comp_map:
                sys_components[sys.id].append(cid)

    # Also check contains relationships
    for rel in model.relationships:
        if _rel_type(rel) == "contains" and rel.from_id in sys_map and rel.to_id in comp_map:
            if rel.to_id not in sys_components[rel.from_id]:
                sys_components[rel.from_id].append(rel.to_id)

    assigned_comps: set[str] = set()
    for sys_id, comp_ids in sys_components.items():
        sys = sys_map[sys_id]
        lines.append(f'    subgraph {_sid(sys_id)}["{_label(sys.name)}"]')
        for cid in comp_ids:
            comp = comp_map[cid]
            lines.append(f"        {shape('component', cid, comp.name)}")
            class_assignments.append(_apply_class(cid, "component"))
            assigned_comps.add(cid)
        lines.append("    end")

    # Unassigned components
    unassigned = [c for c in model.entities.components if c.id not in assigned_comps]
    if unassigned:
        lines.append('    subgraph unassigned["Unassigned Components"]')
        for comp in unassigned:
            lines.append(f"        {shape('component', comp.id, comp.name)}")
            class_assignments.append(_apply_class(comp.id, "component"))
        lines.append("    end")

    # Inter-component dependency edges
    comp_ids = {c.id for c in model.entities.components}
    for rel in model.relationships:
        if _rel_type(rel) == "depends-on" and rel.from_id in comp_ids and rel.to_id in comp_ids:
            lines.append(f"    {_sid(rel.from_id)} {edge_style('depends-on')} {_sid(rel.to_id)}")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_conops_diagram(model: "ArchitectureModel") -> str:
    """ConOps view: actors interacting with the system through capability groups.

    Shows external actors on the left, system boundary with L1 capability
    groups (from CAP-0 contains relationships), and actor-to-capability edges.
    """
    lines = ["graph LR"]
    class_assignments: list[str] = []

    # Build contains lookup: parent_id -> [child_id]
    contains: dict[str, list[str]] = defaultdict(list)
    for rel in model.relationships:
        if _rel_type(rel) == "contains":
            contains[rel.from_id].append(rel.to_id)

    # Build entity lookup
    cap_map = {c.id: c for c in model.entities.capabilities}

    # Actors subgraph
    if model.entities.actors:
        lines.append('    subgraph ext["External Actors"]')
        for actor in model.entities.actors:
            lines.append(f"        {shape('actor', actor.id, actor.name)}")
            class_assignments.append(_apply_class(actor.id, "actor"))
        lines.append("    end")

    # System boundary
    project = getattr(model.meta, "project", "System")
    lines.append(f'    subgraph sys["{_label(project)}"]')

    # Find L1 groups: children of CAP-0 (or whatever root capability)
    root_cap_id = "CAP-0"
    l1_group_ids = contains.get(root_cap_id, [])

    if l1_group_ids:
        for g_id in l1_group_ids:
            g_cap = cap_map.get(g_id)
            if not g_cap:
                continue
            g_label = _label(g_cap.name)
            lines.append(f'        subgraph {_sid(g_id)}["{g_label}"]')
            # Children of this group
            for child_id in contains.get(g_id, []):
                child = cap_map.get(child_id)
                if child:
                    lines.append(f"            {shape('capability', child.id, child.name)}")
                    class_assignments.append(_apply_class(child.id, "capability"))
            lines.append("        end")
    else:
        # Fallback: show all capabilities flat
        for cap in model.entities.capabilities:
            lines.append(f"        {shape('capability', cap.id, cap.name)}")
            class_assignments.append(_apply_class(cap.id, "capability"))

    lines.append("    end")

    # Actor-to-capability edges
    actor_ids = {a.id for a in model.entities.actors}
    cap_ids = {c.id for c in model.entities.capabilities}
    has_edges = False
    for rel in model.relationships:
        if rel.from_id in actor_ids and rel.to_id in cap_ids:
            lines.append(f"    {_sid(rel.from_id)} --> {_sid(rel.to_id)}")
            has_edges = True
        elif rel.to_id in actor_ids and rel.from_id in cap_ids:
            lines.append(f"    {_sid(rel.to_id)} --> {_sid(rel.from_id)}")
            has_edges = True

    # If no direct edges, connect all actors to system boundary
    if not has_edges and model.entities.actors:
        for actor in model.entities.actors:
            lines.append(f"    {_sid(actor.id)} --> sys")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_functional_architecture_diagram(model: "ArchitectureModel") -> str:
    """Functional decomposition tree showing the full capability hierarchy.

    Walks the capability hierarchy using contains relationships.
    Root (CAP-0) at top, L1 groups as subgraphs, children inside.
    """
    lines = ["graph TB"]
    class_assignments: list[str] = []

    # Build contains lookup
    contains: dict[str, list[str]] = defaultdict(list)
    for rel in model.relationships:
        if _rel_type(rel) == "contains":
            contains[rel.from_id].append(rel.to_id)

    cap_map = {c.id: c for c in model.entities.capabilities}

    # Root capability
    root_id = "CAP-0"
    root = cap_map.get(root_id)
    if root:
        lines.append(f"    {shape('capability', root.id, root.name)}")
        class_assignments.append(_apply_class(root.id, "capability"))

    # L1 groups (children of root)
    l1_ids = contains.get(root_id, [])
    for g_id in l1_ids:
        g_cap = cap_map.get(g_id)
        if not g_cap:
            continue
        lines.append(f'    subgraph {_sid(g_id)}["{_label(g_cap.name)}"]')

        # L1 capabilities (children of group)
        l1_child_ids = contains.get(g_id, [])
        for child_id in l1_child_ids:
            child = cap_map.get(child_id)
            if not child:
                continue
            lines.append(f"        {shape('capability', child.id, child.name)}")
            class_assignments.append(_apply_class(child.id, "capability"))

            # L2 sub-capabilities
            for sub_id in contains.get(child_id, []):
                sub = cap_map.get(sub_id)
                if sub:
                    lines.append(f"        {shape('capability', sub.id, sub.name)}")
                    class_assignments.append(_apply_class(sub.id, "capability"))
                    lines.append(f"        {_sid(child_id)} -.-> {_sid(sub_id)}")

        lines.append("    end")

        # Edge from root to group
        if root:
            lines.append(f"    {_sid(root_id)} -.-> {_sid(g_id)}")

        # Edges from group to its children
        for child_id in l1_child_ids:
            if cap_map.get(child_id):
                lines.append(f"    {_sid(g_id)} -.-> {_sid(child_id)}")

    # If no hierarchy found, show all caps flat
    if not l1_ids:
        for cap in model.entities.capabilities:
            if cap.id != root_id:
                lines.append(f"    {shape('capability', cap.id, cap.name)}")
                class_assignments.append(_apply_class(cap.id, "capability"))

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_logical_architecture_diagram(model: "ArchitectureModel") -> str:
    """Components grouped by layer with dependency edges.

    Groups components by their layer (via contains relationships),
    shows depends-on relationships between components.
    """
    lines = ["graph TB"]
    class_assignments: list[str] = []

    # Build layer -> components mapping from contains relationships
    layer_components: dict[str, list[str]] = defaultdict(list)
    comp_in_layer: set[str] = set()
    for rel in model.relationships:
        if _rel_type(rel) == "contains":
            # Check if from_id is a layer
            layer_ids = {la.id for la in model.entities.layers}
            if rel.from_id in layer_ids:
                layer_components[rel.from_id].append(rel.to_id)
                comp_in_layer.add(rel.to_id)

    layer_map = {la.id: la for la in model.entities.layers}
    comp_map = {c.id: c for c in model.entities.components}

    # Render layers with their components
    for layer in model.entities.layers:
        comps = layer_components.get(layer.id, [])
        lines.append(f'    subgraph {_sid(layer.id)}["{_label(layer.name)}"]')
        for comp_id in comps:
            comp = comp_map.get(comp_id)
            if comp:
                lines.append(f"        {shape('component', comp.id, comp.name)}")
                class_assignments.append(_apply_class(comp.id, "component"))
        lines.append("    end")

    # Components not in any layer
    for comp in model.entities.components:
        if comp.id not in comp_in_layer:
            lines.append(f"    {shape('component', comp.id, comp.name)}")
            class_assignments.append(_apply_class(comp.id, "component"))

    # Dependency edges
    comp_ids = {c.id for c in model.entities.components}
    for rel in model.relationships:
        if _rel_type(rel) == "depends-on" and rel.from_id in comp_ids and rel.to_id in comp_ids:
            lines.append(f"    {_sid(rel.from_id)} --> {_sid(rel.to_id)}")

    lines.extend(css_classes())
    lines.extend(a for a in class_assignments if a)
    return "\n".join(lines)


def generate_behavior_overview_diagram(model: "ArchitectureModel") -> str:
    """Top-level behaviors with trigger edges.

    Finds top-level behaviors (not contained by another behavior),
    groups by ID prefix, shows triggers relationships.
    """
    lines = ["graph LR"]
    class_assignments: list[str] = []

    # Find behaviors that are contained by another behavior
    contained_behaviors: set[str] = set()
    beh_ids = {b.id for b in model.entities.behaviors}
    for rel in model.relationships:
        if _rel_type(rel) == "contains" and rel.from_id in beh_ids and rel.to_id in beh_ids:
            contained_behaviors.add(rel.to_id)

    # Top-level behaviors
    top_behaviors = [b for b in model.entities.behaviors if b.id not in contained_behaviors]

    # Group by prefix pattern
    groups: dict[str, list] = defaultdict(list)
    for beh in top_behaviors:
        # Extract prefix: BEH-C*, BEH-P*, etc.
        m = re.match(r"(BEH-[A-Z]+)", beh.id)
        if m:
            groups[m.group(1)].append(beh)
        else:
            groups["Other"].append(beh)

    # Render groups as subgraphs
    for prefix, behs in sorted(groups.items()):
        # Derive group label
        if prefix == "BEH-C":
            label = "CLI Commands"
        elif prefix == "BEH-P":
            label = "Pipeline Stages"
        elif prefix == "BEH-O":
            label = "Operations"
        elif prefix == "BEH-V":
            label = "Validation"
        else:
            label = prefix
        lines.append(f'    subgraph {_sid(prefix)}["{label}"]')
        for beh in behs:
            lines.append(f"        {shape('behavior', beh.id, beh.name)}")
            class_assignments.append(_apply_class(beh.id, "behavior"))
        lines.append("    end")

    # Trigger edges (only between top-level)
    top_ids = {b.id for b in top_behaviors}
    for rel in model.relationships:
        if _rel_type(rel) == "triggers" and rel.from_id in top_ids and rel.to_id in top_ids:
            lines.append(f"    {_sid(rel.from_id)} --> {_sid(rel.to_id)}")

    # Also show triggers between any behaviors for completeness
    for rel in model.relationships:
        if _rel_type(rel) == "triggers" and (rel.from_id not in top_ids or rel.to_id not in top_ids):
            if rel.from_id in beh_ids and rel.to_id in beh_ids:
                lines.append(f"    {_sid(rel.from_id)} --> {_sid(rel.to_id)}")

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


def _convert_clicks_to_anchors(mermaid_content: str) -> str:
    """Replace click directives referencing .mmd files with anchor links."""
    return re.sub(
        r'click (\S+) "([^"]+)\.mmd"(?:\s+"[^"]*")?',
        r'click \1 href "#diagram-\2"',
        mermaid_content,
    )


def inject_click_handlers(mermaid_code: str, entity_ids: set[str]) -> str:
    """Inject click callbacks for every entity node in a Mermaid diagram.

    Scans the Mermaid code for sanitized node IDs that correspond to known
    entity IDs and appends `click <sid> showEntity` directives. Existing
    click directives for those nodes are removed first to avoid duplicates.

    Args:
        mermaid_code: Raw Mermaid diagram string.
        entity_ids: Set of original (unsanitized) entity IDs from the model.

    Returns:
        Mermaid code with click handlers injected before classDef lines.
    """
    # Build sid -> original_id mapping
    sid_to_id: dict[str, str] = {_sid(eid): eid for eid in entity_ids}

    # Remove existing click directives
    lines = []
    for line in mermaid_code.split("\n"):
        stripped = line.strip()
        if stripped.startswith("click "):
            continue
        lines.append(line)

    # Find all sids that appear as node definitions in the diagram
    # Mermaid node patterns: sid[, sid(, sid{, sid([, sid((, sid[[, sid[(, sid[/
    node_pattern = re.compile(r'\b(' + '|'.join(re.escape(s) for s in sid_to_id) + r')[\[\(\{\|]')

    found_sids: set[str] = set()
    for line in lines:
        for m in node_pattern.finditer(line):
            found_sids.add(m.group(1))

    # Insert click directives before classDef lines (or at end)
    click_lines = [f"    click {sid} showEntity" for sid in sorted(found_sids)]

    # Find insertion point (before first classDef or at end)
    insert_idx = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith("classDef "):
            insert_idx = i
            break

    result_lines = lines[:insert_idx] + click_lines + lines[insert_idx:]
    return "\n".join(result_lines)


def build_entity_properties(model: "ArchitectureModel") -> dict[str, dict]:
    """Build property cards for all entities in the model.

    Returns dict mapping entity_id -> {type, name, description, status, properties}
    where properties is a dict of type-specific key/value pairs for display.
    """
    props: dict[str, dict] = {}

    def _base(entity, etype: str, extra: dict | None = None) -> dict:
        d: dict = {
            "type": etype,
            "name": entity.name,
            "description": getattr(entity, "description", ""),
            "status": getattr(entity.status, "value", str(entity.status)),
            "properties": {},
        }
        if extra:
            d["properties"] = extra
        return d

    for a in model.entities.actors:
        props[a.id] = _base(a, "actor", {
            "Actor Type": getattr(a.type, "value", str(a.type)),
            "Goals": ", ".join(a.goals) if a.goals else "",
        })

    for c in model.entities.capabilities:
        props[c.id] = _base(c, "capability", {
            "Priority": getattr(c.priority, "value", str(c.priority)),
            "Source Block": c.source_block or "",
        })

    for b in model.entities.behaviors:
        extra: dict[str, str] = {}
        if hasattr(b, "trigger") and b.trigger:
            extra["Trigger"] = b.trigger
        if hasattr(b, "preconditions") and b.preconditions:
            extra["Preconditions"] = ", ".join(b.preconditions)
        props[b.id] = _base(b, "behavior", extra)

    for i in model.entities.interfaces:
        props[i.id] = _base(i, "interface", {
            "Type": getattr(i.type, "value", str(i.type)) if hasattr(i, "type") else "",
            "Protocol": getattr(i, "protocol", "") or "",
        })

    for c in model.entities.constraints:
        props[c.id] = _base(c, "constraint", {
            "Rationale": getattr(c, "rationale", "") or "",
        })

    for la in model.entities.layers:
        props[la.id] = _base(la, "layer")

    for c in model.entities.components:
        extra_c: dict[str, str] = {}
        if hasattr(c, "layer") and c.layer:
            extra_c["Layer"] = c.layer
        files = getattr(c, "files", []) or []
        if files:
            extra_c["Files"] = str(len(files))
        props[c.id] = _base(c, "component", extra_c)

    for s in model.entities.systems:
        extra_s: dict[str, str] = {}
        if s.component_ids:
            extra_s["Components"] = str(len(s.component_ids))
        if s.sub_model_ref:
            extra_s["Sub-model"] = s.sub_model_ref
        props[s.id] = _base(s, "system", extra_s)

    for r in model.entities.requirements:
        props[r.id] = _base(r, "requirement", {
            "Priority": r.priority or "",
            "Source": r.source_doc or "",
            "Rationale": r.rationale or "",
        })

    return props


def generate_html_viewer(
    model: "ArchitectureModel",
    output_path: Path,
    title: str = "Architecture Viewer",
) -> Path:
    """Generate a self-contained HTML viewer with 7 SE model views and universal click navigation.

    Features:
    - 7 SE views: ConOps, Functional Architecture, Logical Architecture,
      Behavior Model, ICD, Requirements Allocation, System Decomposition
    - Every entity node is clickable in every diagram
    - Clicking navigates to entity detail page (property card + faceted diagrams)
    - History stack with breadcrumb trail and back button
    - Dark theme, mobile-responsive with hamburger menu

    Returns the path to the generated HTML file.
    """
    import json as _json

    output_path = Path(output_path)

    # Collect all entity IDs for click injection
    all_ids = model.all_entity_ids

    # ── 1. Generate 7 SE overview diagrams (with click injection) ─
    se_views: dict[str, dict[str, str]] = {
        "conops": {"label": "ConOps", "subtitle": "Concept of Operations",
                   "mermaid": inject_click_handlers(generate_conops_diagram(model), all_ids)},
        "functional": {"label": "Functional Architecture", "subtitle": "Functional Analysis (SA-4.2)",
                       "mermaid": inject_click_handlers(generate_functional_architecture_diagram(model), all_ids)},
        "logical": {"label": "Logical Architecture", "subtitle": "Logical Decomposition (SA-4.3)",
                    "mermaid": inject_click_handlers(generate_logical_architecture_diagram(model), all_ids)},
        "behavior": {"label": "Behavior Model", "subtitle": "Use Case Analysis",
                     "mermaid": inject_click_handlers(generate_behavior_overview_diagram(model), all_ids)},
        "icd": {"label": "ICD", "subtitle": "Interface Control Document",
                "mermaid": inject_click_handlers(generate_icd_diagram(model), all_ids)},
        "requirements": {"label": "Requirements", "subtitle": "Requirements Analysis (SA-4.1)",
                         "mermaid": inject_click_handlers(generate_requirements_allocation_diagram(model), all_ids)},
        "systems": {"label": "System Decomposition", "subtitle": "Physical Architecture",
                    "mermaid": inject_click_handlers(generate_system_decomposition_diagram(model), all_ids)},
    }

    # ── 2. Entity categories for sidebar ──────────────────────────
    entity_categories: list[tuple[str, str, list]] = [
        ("systems", "Systems", list(model.entities.systems)),
        ("layers", "Layers", list(model.entities.layers)),
        ("components", "Components", list(model.entities.components)),
        ("capabilities", "Capabilities", list(model.entities.capabilities)),
        ("behaviors", "Behaviors", list(model.entities.behaviors)),
        ("interfaces", "Interfaces", list(model.entities.interfaces)),
        ("actors", "Actors", list(model.entities.actors)),
        ("requirements", "Requirements", list(model.entities.requirements)),
        ("constraints", "Constraints", list(model.entities.constraints)),
    ]

    _plural_to_singular = {
        "layers": "layer", "components": "component", "capabilities": "capability",
        "behaviors": "behavior", "interfaces": "interface", "actors": "actor",
        "systems": "system", "requirements": "requirement", "constraints": "constraint",
    }

    # ── 3. Explorer facets (with click injection) ─────────────────
    explorer_data: dict[str, dict[str, str]] = {}
    for etype, _label_text, entities in entity_categories:
        singular = _plural_to_singular.get(etype, etype.rstrip("s"))
        for ent in entities:
            facets = generate_entity_explorer(model, singular, ent.id)
            if facets:
                # Inject click handlers into each facet diagram
                explorer_data[ent.id] = {
                    k: inject_click_handlers(v, all_ids) for k, v in facets.items()
                }

    # ── 4. Property cards ─────────────────────────────────────────
    entity_props = build_entity_properties(model)

    # ── 5. JSON data blob ─────────────────────────────────────────
    diagram_data = {
        "se_views": {k: {"label": v["label"], "subtitle": v["subtitle"], "mermaid": v["mermaid"]}
                     for k, v in se_views.items()},
        "entities": explorer_data,
        "properties": entity_props,
    }
    data_json = _json.dumps(diagram_data, ensure_ascii=False)

    # ── 6. Sidebar HTML ──────────────────────────────────────────
    se_nav = "\n".join(
        f'            <a href="#" data-view="{k}" class="nav-link se-link">{v["label"]}</a>'
        for k, v in se_views.items()
    )

    entity_nav_parts = []
    for etype, elabel, entities in entity_categories:
        if not entities:
            continue
        items = "\n".join(
            f'                <a href="#" onclick="showEntity(\'{e.id}\');return false;" '
            f'class="nav-link entity-link">{e.id}: {e.name}</a>'
            for e in entities
        )
        entity_nav_parts.append(
            f'        <details class="entity-cat">\n'
            f'            <summary>{elabel} ({len(entities)})</summary>\n'
            f'{items}\n'
            f'        </details>'
        )
    entity_nav = "\n".join(entity_nav_parts)

    # ── 7. Assemble HTML ─────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; }}

        /* Hamburger */
        .hamburger {{ display: none; position: fixed; top: 10px; left: 10px; z-index: 1001;
                      background: #16213e; border: 1px solid #0f3460; padding: 8px 12px;
                      color: #e0e0e0; border-radius: 4px; cursor: pointer; font-size: 20px; }}
        @media (max-width: 768px) {{ .hamburger {{ display: block; }} }}

        /* Sidebar */
        .sidebar {{ position: fixed; top: 0; left: 0; width: 280px; height: 100vh;
                    background: #16213e; overflow-y: auto; padding: 16px; z-index: 1000;
                    border-right: 1px solid #0f3460; transition: transform 0.3s ease; }}
        @media (max-width: 768px) {{
            .sidebar {{ transform: translateX(-100%); }}
            .sidebar.open {{ transform: translateX(0); }}
        }}
        .sidebar h2 {{ color: #e94560; margin-bottom: 16px; font-size: 15px; }}
        .sidebar .nav-section {{ color: #a0a0c0; font-size: 11px; text-transform: uppercase;
                                 letter-spacing: 1px; margin: 14px 0 6px; }}
        .sidebar .nav-link {{ display: block; padding: 4px 0 4px 12px; color: #7ec8e3;
                              text-decoration: none; font-size: 12px; cursor: pointer; }}
        .sidebar .nav-link:hover, .sidebar .nav-link.active {{ color: #e94560; }}
        .sidebar details {{ margin-bottom: 2px; }}
        .sidebar summary {{ cursor: pointer; padding: 5px 0; color: #a0a0c0; font-size: 13px;
                            list-style: none; }}
        .sidebar summary::before {{ content: "\\25b6  "; font-size: 10px; }}
        .sidebar details[open] > summary::before {{ content: "\\25bc  "; }}
        .sidebar .entity-link {{ padding-left: 20px; font-size: 11px; white-space: nowrap;
                                 overflow: hidden; text-overflow: ellipsis; }}
        .sidebar .divider {{ border-top: 1px solid #0f3460; margin: 10px 0; }}

        /* Content */
        .content {{ margin-left: 280px; padding: 20px; min-height: 100vh; }}
        @media (max-width: 768px) {{ .content {{ margin-left: 0; padding: 12px; padding-top: 50px; }} }}

        /* Breadcrumbs */
        .breadcrumbs {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
                        margin-bottom: 12px; font-size: 12px; }}
        .breadcrumbs a {{ color: #7ec8e3; text-decoration: none; cursor: pointer; }}
        .breadcrumbs a:hover {{ color: #e94560; }}
        .breadcrumbs .sep {{ color: #555; }}
        .breadcrumbs .current {{ color: #e0e0e0; }}
        .back-btn {{ background: #0f3460; color: #7ec8e3; border: 1px solid #1a5276;
                     padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;
                     margin-right: 8px; }}
        .back-btn:hover {{ background: #1a5276; color: #e94560; }}

        /* Headers */
        .content-header {{ color: #e94560; font-size: 18px; margin-bottom: 4px; }}
        .content-subtitle {{ color: #a0a0c0; font-size: 13px; margin-bottom: 16px; font-style: italic; }}

        /* Property card */
        .prop-card {{ background: #16213e; border: 1px solid #0f3460; border-radius: 6px;
                      padding: 14px; margin-bottom: 16px; display: grid;
                      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px; }}
        .prop-item {{ font-size: 12px; }}
        .prop-label {{ color: #a0a0c0; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .prop-value {{ color: #e0e0e0; margin-top: 2px; }}
        .prop-desc {{ grid-column: 1 / -1; }}
        .prop-desc .prop-value {{ font-size: 13px; line-height: 1.5; color: #c0c0d0; }}

        /* Diagram */
        .diagram-box {{ background: #0a0a1a; padding: 16px; border-radius: 6px;
                        border: 1px solid #0f3460; margin-bottom: 16px; overflow-x: auto; }}
        .accordion {{ border-bottom: 1px solid #0f3460; }}
        .accordion-header {{ padding: 10px 0; cursor: pointer; color: #7ec8e3; font-size: 14px;
                             user-select: none; }}
        .accordion-header:hover {{ color: #e94560; }}
        .accordion-header::before {{ content: "\\25b6  "; font-size: 10px; }}
        .accordion-header.open::before {{ content: "\\25bc  "; }}
        .accordion-body {{ max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }}
        .accordion-body.open {{ max-height: 4000px; }}
        .welcome {{ color: #a0a0c0; font-size: 14px; margin-top: 40px; text-align: center; }}

        /* Entity type badges */
        .type-badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px;
                       font-size: 10px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }}
        .type-badge.actor {{ background: #E74C8B; color: #fff; }}
        .type-badge.capability {{ background: #F39C12; color: #fff; }}
        .type-badge.component {{ background: #27AE60; color: #fff; }}
        .type-badge.behavior {{ background: #8E44AD; color: #fff; }}
        .type-badge.interface {{ background: #1ABC9C; color: #fff; }}
        .type-badge.layer {{ background: #16A085; color: #fff; }}
        .type-badge.constraint {{ background: #E74C3C; color: #fff; }}
        .type-badge.system {{ background: #4A90D9; color: #fff; }}
        .type-badge.requirement {{ background: #E74C3C; color: #fff; }}
    </style>
</head>
<body>
    <button class="hamburger" onclick="document.querySelector('.sidebar').classList.toggle('open')">&#9776;</button>

    <nav class="sidebar">
        <h2>{title}</h2>
        <div class="nav-section">SE Model Views</div>
{se_nav}
        <div class="divider"></div>
        <div class="nav-section">Entities</div>
{entity_nav}
    </nav>

    <main class="content" id="content">
        <p class="welcome">Select a view or entity from the sidebar.</p>
    </main>

    <script>
        var D = {data_json};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: false, theme: 'dark', securityLevel: 'loose',
                             flowchart: {{ htmlLabels: true, curve: 'basis' }} }});

        var renderCounter = 0;
        var navHistory = [];  // Stack of {{type, id, label}}
        var content = document.getElementById('content');

        /* ── Mermaid rendering ────────────────────────────────── */
        async function renderMermaid(container, code) {{
            try {{
                var id = 'mmd_' + (++renderCounter);
                var {{ svg }} = await mermaid.render(id, code);
                container.innerHTML = svg;
            }} catch(e) {{
                container.innerHTML = '<pre style="color:#e94560">' + e.message + '</pre>';
            }}
        }}

        /* ── Mobile nav ───────────────────────────────────────── */
        function closeMobileNav() {{
            if (window.innerWidth <= 768)
                document.querySelector('.sidebar').classList.remove('open');
        }}

        /* ── Breadcrumbs ──────────────────────────────────────── */
        function renderBreadcrumbs(currentLabel) {{
            var html = '';
            if (navHistory.length > 0) {{
                html += '<button class="back-btn" onclick="goBack()">&#8592; Back</button>';
            }}
            for (var i = 0; i < navHistory.length; i++) {{
                var h = navHistory[i];
                if (h.type === 'view') {{
                    html += '<a onclick="goToHistory(' + i + ');return false;">' + h.label + '</a>';
                }} else {{
                    html += '<a onclick="goToHistory(' + i + ');return false;">' + h.label + '</a>';
                }}
                html += '<span class="sep">&#9656;</span>';
            }}
            html += '<span class="current">' + currentLabel + '</span>';
            return '<div class="breadcrumbs">' + html + '</div>';
        }}

        function goBack() {{
            if (navHistory.length === 0) return;
            var prev = navHistory.pop();
            if (prev.type === 'view') showView(prev.id, false);
            else showEntity(prev.id, false);
        }}

        function goToHistory(idx) {{
            var target = navHistory[idx];
            navHistory = navHistory.slice(0, idx);
            if (target.type === 'view') showView(target.id, false);
            else showEntity(target.id, false);
        }}

        /* ── Property card HTML ───────────────────────────────── */
        function propCardHtml(eid) {{
            var p = D.properties[eid];
            if (!p) return '';
            var html = '<div class="prop-card">';
            html += '<div class="prop-item"><div class="prop-label">ID</div><div class="prop-value">' + eid + '</div></div>';
            html += '<div class="prop-item"><div class="prop-label">Type</div><div class="prop-value"><span class="type-badge ' + p.type + '">' + p.type + '</span></div></div>';
            html += '<div class="prop-item"><div class="prop-label">Status</div><div class="prop-value">' + (p.status || 'N/A') + '</div></div>';
            if (p.properties) {{
                for (var k in p.properties) {{
                    if (p.properties[k]) {{
                        html += '<div class="prop-item"><div class="prop-label">' + k + '</div><div class="prop-value">' + p.properties[k] + '</div></div>';
                    }}
                }}
            }}
            if (p.description) {{
                html += '<div class="prop-item prop-desc"><div class="prop-label">Description</div><div class="prop-value">' + p.description + '</div></div>';
            }}
            html += '</div>';
            return html;
        }}

        /* ── Show SE view ─────────────────────────────────────── */
        function showView(key, pushHistory) {{
            var v = D.se_views[key];
            if (!v) return;
            if (pushHistory !== false) {{
                // Push current state if exists
                var cur = content.dataset.currentType;
                var curId = content.dataset.currentId;
                var curLabel = content.dataset.currentLabel;
                if (cur) navHistory.push({{type: cur, id: curId, label: curLabel}});
            }}
            content.dataset.currentType = 'view';
            content.dataset.currentId = key;
            content.dataset.currentLabel = v.label;

            var html = renderBreadcrumbs(v.label);
            html += '<h2 class="content-header">' + v.label + '</h2>';
            html += '<div class="content-subtitle">' + v.subtitle + '</div>';
            html += '<div class="diagram-box" id="dia-main"></div>';
            content.innerHTML = html;
            renderMermaid(document.getElementById('dia-main'), v.mermaid);
            closeMobileNav();
        }}

        /* ── Show Entity detail ───────────────────────────────── */
        window.showEntity = function(eid, pushHistory) {{
            if (pushHistory !== false) {{
                var cur = content.dataset.currentType;
                var curId = content.dataset.currentId;
                var curLabel = content.dataset.currentLabel;
                if (cur) navHistory.push({{type: cur, id: curId, label: curLabel}});
            }}

            var p = D.properties[eid] || {{}};
            var label = (p.name ? eid + ': ' + p.name : eid);
            content.dataset.currentType = 'entity';
            content.dataset.currentId = eid;
            content.dataset.currentLabel = label;

            var html = renderBreadcrumbs(label);
            html += '<h2 class="content-header">' + label + '</h2>';
            html += propCardHtml(eid);

            var facets = D.entities[eid];
            if (facets && Object.keys(facets).length > 0) {{
                var i = 0;
                for (var facetName in facets) {{
                    var cid = 'f_' + eid.replace(/[^a-zA-Z0-9]/g,'_') + '_' + i;
                    html += '<div class="accordion">'
                        + '<div class="accordion-header" data-target="' + cid
                        + '" data-code="' + btoa(unescape(encodeURIComponent(facets[facetName])))
                        + '">' + facetName + '</div>'
                        + '<div class="accordion-body" id="' + cid + '">'
                        + '<div class="diagram-box" id="' + cid + '_dia"></div>'
                        + '</div></div>';
                    i++;
                }}
            }} else {{
                html += '<p style="color:#a0a0c0;margin-top:12px">No relationship diagrams for this entity.</p>';
            }}
            content.innerHTML = html;

            // Wire accordion
            content.querySelectorAll('.accordion-header').forEach(function(hdr) {{
                hdr.addEventListener('click', function() {{
                    var body = document.getElementById(this.dataset.target);
                    var isOpen = body.classList.contains('open');
                    body.classList.toggle('open');
                    this.classList.toggle('open');
                    if (!isOpen && !body.dataset.rendered) {{
                        body.dataset.rendered = '1';
                        var code = decodeURIComponent(escape(atob(this.dataset.code)));
                        renderMermaid(document.getElementById(this.dataset.target + '_dia'), code);
                    }}
                }});
            }});
            closeMobileNav();
        }};

        /* ── Wire sidebar SE view links ───────────────────────── */
        document.querySelectorAll('[data-view]').forEach(function(a) {{
            a.addEventListener('click', function(ev) {{
                ev.preventDefault();
                navHistory = [];
                content.dataset.currentType = '';
                content.dataset.currentId = '';
                content.dataset.currentLabel = '';
                showView(this.dataset.view, false);
            }});
        }});
    </script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


def generate_entity_explorer(
    model: "ArchitectureModel",
    entity_type: str,
    entity_id: str,
) -> dict[str, str]:
    """Generate faceted diagrams for an entity.

    Returns dict mapping facet name to Mermaid diagram content.
    Empty dict if entity not found.
    """
    # Build entity lookup maps
    entity_map: dict[str, tuple[str, str]] = {}
    for c in model.entities.components:
        entity_map[c.id] = ("component", c.name)
    for c in model.entities.capabilities:
        entity_map[c.id] = ("capability", c.name)
    for b in model.entities.behaviors:
        entity_map[b.id] = ("behavior", b.name)
    for i in model.entities.interfaces:
        entity_map[i.id] = ("interface", i.name)
    for la in model.entities.layers:
        entity_map[la.id] = ("layer", la.name)
    for a in model.entities.actors:
        entity_map[a.id] = ("actor", a.name)

    if entity_id not in entity_map:
        return {}

    etype, ename = entity_map[entity_id]
    if etype != entity_type:
        return {}

    def _facet_diagram(center_type: str, center_id: str, center_name: str,
                       related: list[tuple[str, str, str, str]]) -> str:
        """Build a small graph LR diagram.

        related: list of (related_id, related_type, related_name, rel_label)
        where rel_label is like 'realizes' and edge goes center->related.
        """
        lines = ["graph LR"]
        lines.append(f"  {shape(center_type, center_id, center_name)}")
        seen = set()
        for rid, rtype, rname, rel_label in related:
            if rid not in seen:
                lines.append(f"  {shape(rtype, rid, rname)}")
                seen.add(rid)
            lines.append(f"  {_sid(center_id)} {edge_style(rel_label)} {_sid(rid)}")
        return "\n".join(lines)

    def _facet_diagram_reverse(center_type: str, center_id: str, center_name: str,
                               related: list[tuple[str, str, str, str]]) -> str:
        """Like _facet_diagram but edges go related->center."""
        lines = ["graph LR"]
        lines.append(f"  {shape(center_type, center_id, center_name)}")
        seen = set()
        for rid, rtype, rname, rel_label in related:
            if rid not in seen:
                lines.append(f"  {shape(rtype, rid, rname)}")
                seen.add(rid)
            lines.append(f"  {_sid(rid)} {edge_style(rel_label)} {_sid(center_id)}")
        return "\n".join(lines)

    facets: dict[str, str] = {}

    if entity_type == "component":
        # Capabilities facet
        caps = []
        for rel in model.relationships:
            if rel.from_id == entity_id and _rel_type(rel) == "realizes" and rel.to_id in entity_map:
                _, rname = entity_map[rel.to_id]
                caps.append((rel.to_id, "capability", rname, "realizes"))
        if caps:
            facets["Capabilities"] = _facet_diagram("component", entity_id, ename, caps)

        # Interfaces facet
        ifaces = []
        for rel in model.relationships:
            if rel.from_id == entity_id and _rel_type(rel) == "exposes" and rel.to_id in entity_map:
                _, rname = entity_map[rel.to_id]
                ifaces.append((rel.to_id, "interface", rname, "exposes"))
        if ifaces:
            facets["Interfaces"] = _facet_diagram("component", entity_id, ename, ifaces)

        # Dependencies facet (both directions)
        deps = []
        for rel in model.relationships:
            if _rel_type(rel) == "depends-on":
                if rel.from_id == entity_id and rel.to_id in entity_map:
                    _, rname = entity_map[rel.to_id]
                    deps.append((rel.to_id, "component", rname, "depends-on"))
                elif rel.to_id == entity_id and rel.from_id in entity_map:
                    _, rname = entity_map[rel.from_id]
                    deps.append((rel.from_id, "component", rname, "depends-on"))
        if deps:
            # Mixed directions - build manually
            lines = ["graph LR"]
            lines.append(f"  {shape('component', entity_id, ename)}")
            seen = set()
            for rel in model.relationships:
                if _rel_type(rel) == "depends-on":
                    if rel.from_id == entity_id and rel.to_id in entity_map:
                        t = rel.to_id
                        if t not in seen:
                            _, rn = entity_map[t]
                            lines.append(f"  {shape('component', t, rn)}")
                            seen.add(t)
                        lines.append(f"  {_sid(entity_id)} {edge_style('depends-on')} {_sid(t)}")
                    elif rel.to_id == entity_id and rel.from_id in entity_map:
                        f = rel.from_id
                        if f not in seen:
                            _, rn = entity_map[f]
                            lines.append(f"  {shape('component', f, rn)}")
                            seen.add(f)
                        lines.append(f"  {_sid(f)} {edge_style('depends-on')} {_sid(entity_id)}")
            facets["Dependencies"] = "\n".join(lines)

        # Behaviors facet
        behs = []
        for rel in model.relationships:
            if rel.from_id == entity_id and _rel_type(rel) == "traces-to" and rel.to_id in entity_map:
                _, rname = entity_map[rel.to_id]
                behs.append((rel.to_id, "behavior", rname, "traces-to"))
        if behs:
            facets["Behaviors"] = _facet_diagram("component", entity_id, ename, behs)

        # Sub-Components facet
        subs = []
        for rel in model.relationships:
            if rel.from_id == entity_id and _rel_type(rel) == "contains" and rel.to_id in entity_map:
                rt, rname = entity_map[rel.to_id]
                if rt == "component":
                    subs.append((rel.to_id, "component", rname, "contains"))
        if subs:
            facets["Sub-Components"] = _facet_diagram("component", entity_id, ename, subs)

    elif entity_type == "capability":
        # Functional Breakdown
        children = []
        for rel in model.relationships:
            if rel.from_id == entity_id and _rel_type(rel) == "contains" and rel.to_id in entity_map:
                rt, rname = entity_map[rel.to_id]
                if rt == "capability":
                    children.append((rel.to_id, "capability", rname, "contains"))
        if children:
            facets["Functional Breakdown"] = _facet_diagram("capability", entity_id, ename, children)

        # Components that realize this capability
        comps = []
        for rel in model.relationships:
            if _rel_type(rel) == "realizes" and rel.to_id == entity_id and rel.from_id in entity_map:
                _, rname = entity_map[rel.from_id]
                comps.append((rel.from_id, "component", rname, "realizes"))
        if comps:
            facets["Components"] = _facet_diagram_reverse("capability", entity_id, ename, comps)

        # Behaviors
        behs = []
        for rel in model.relationships:
            if _rel_type(rel) == "traces-to" and rel.to_id == entity_id and rel.from_id in entity_map:
                rt, rname = entity_map[rel.from_id]
                if rt == "behavior":
                    behs.append((rel.from_id, "behavior", rname, "traces-to"))
        if behs:
            facets["Behaviors"] = _facet_diagram_reverse("capability", entity_id, ename, behs)

    elif entity_type == "behavior":
        # Sub-Behaviors
        children = []
        for rel in model.relationships:
            if rel.from_id == entity_id and _rel_type(rel) == "contains" and rel.to_id in entity_map:
                rt, rname = entity_map[rel.to_id]
                if rt == "behavior":
                    children.append((rel.to_id, "behavior", rname, "contains"))
        if children:
            facets["Sub-Behaviors"] = _facet_diagram("behavior", entity_id, ename, children)

        # Triggers (both directions)
        triggers = []
        for rel in model.relationships:
            if _rel_type(rel) == "triggers":
                if rel.from_id == entity_id and rel.to_id in entity_map:
                    _, rname = entity_map[rel.to_id]
                    triggers.append(("out", rel.to_id, rname))
                elif rel.to_id == entity_id and rel.from_id in entity_map:
                    _, rname = entity_map[rel.from_id]
                    triggers.append(("in", rel.from_id, rname))
        if triggers:
            lines = ["graph LR"]
            lines.append(f"  {shape('behavior', entity_id, ename)}")
            seen = set()
            for direction, tid, tname in triggers:
                if tid not in seen:
                    lines.append(f"  {shape('behavior', tid, tname)}")
                    seen.add(tid)
                if direction == "out":
                    lines.append(f"  {_sid(entity_id)} {edge_style('triggers')} {_sid(tid)}")
                else:
                    lines.append(f"  {_sid(tid)} {edge_style('triggers')} {_sid(entity_id)}")
            facets["Triggers"] = "\n".join(lines)

        # Components (via traces-to)
        comps = []
        for rel in model.relationships:
            if _rel_type(rel) == "traces-to" and rel.to_id == entity_id and rel.from_id in entity_map:
                rt, rname = entity_map[rel.from_id]
                if rt == "component":
                    comps.append((rel.from_id, "component", rname, "traces-to"))
        if comps:
            facets["Components"] = _facet_diagram_reverse("behavior", entity_id, ename, comps)

    elif entity_type == "layer":
        # Components this layer contains
        comps = []
        for rel in model.relationships:
            if rel.from_id == entity_id and _rel_type(rel) == "contains" and rel.to_id in entity_map:
                rt, rname = entity_map[rel.to_id]
                if rt == "component":
                    comps.append((rel.to_id, "component", rname, "contains"))
        if comps:
            facets["Components"] = _facet_diagram("layer", entity_id, ename, comps)

        # Dependencies
        deps = []
        for rel in model.relationships:
            if _rel_type(rel) == "depends-on":
                if rel.from_id == entity_id and rel.to_id in entity_map:
                    rt, rname = entity_map[rel.to_id]
                    deps.append((rel.to_id, rt, rname, "depends-on"))
                elif rel.to_id == entity_id and rel.from_id in entity_map:
                    rt, rname = entity_map[rel.from_id]
                    deps.append((rel.from_id, rt, rname, "depends-on"))
        if deps:
            facets["Dependencies"] = _facet_diagram("layer", entity_id, ename, deps)

    elif entity_type == "interface":
        # Provider
        for rel in model.relationships:
            if _rel_type(rel) == "exposes" and rel.to_id == entity_id and rel.from_id in entity_map:
                rt, rname = entity_map[rel.from_id]
                facets["Provider"] = _facet_diagram_reverse("interface", entity_id, ename,
                    [(rel.from_id, rt, rname, "exposes")])
                break

        # Consumers
        consumers = []
        for rel in model.relationships:
            if _rel_type(rel) == "consumes" and rel.to_id == entity_id and rel.from_id in entity_map:
                rt, rname = entity_map[rel.from_id]
                consumers.append((rel.from_id, rt, rname, "consumes"))
        if consumers:
            facets["Consumers"] = _facet_diagram_reverse("interface", entity_id, ename, consumers)

    elif entity_type == "actor":
        # Capabilities - via explicit relationships or fallback to L1 groups
        caps = []
        for rel in model.relationships:
            if rel.from_id == entity_id and rel.to_id in entity_map:
                rt, rname = entity_map[rel.to_id]
                if rt == "capability":
                    caps.append((rel.to_id, "capability", rname, _rel_type(rel)))
        if not caps:
            # Fallback: show L1 capability groups (CAP-0.x children)
            for rel in model.relationships:
                if rel.from_id == "CAP-0" and _rel_type(rel) == "contains" and rel.to_id in entity_map:
                    rt, rname = entity_map[rel.to_id]
                    if rt == "capability":
                        caps.append((rel.to_id, "capability", rname, "interacts-with"))
        if caps:
            facets["Capabilities"] = _facet_diagram("actor", entity_id, ename, caps)

        # Interfaces
        ifaces = []
        for rel in model.relationships:
            if rel.from_id == entity_id and _rel_type(rel) == "consumes" and rel.to_id in entity_map:
                rt, rname = entity_map[rel.to_id]
                if rt == "interface":
                    ifaces.append((rel.to_id, "interface", rname, "consumes"))
        if ifaces:
            facets["Interfaces"] = _facet_diagram("actor", entity_id, ename, ifaces)

    return facets


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
    # Per-component detail diagrams
    for comp in model.entities.components:
        name = f"component-{comp.id}"
        content = generate_component_detail_diagram(model, comp.id)
        path = output_dir / f"{name}.mmd"
        path.write_text(content + "\n")
        paths[name] = path

    # Per-behavior use-case diagrams
    for beh in model.entities.behaviors:
        name = f"use-case-{beh.id}"
        content = generate_use_case_diagram(model, beh.id)
        path = output_dir / f"{name}.mmd"
        path.write_text(content + "\n")
        paths[name] = path

    return paths
