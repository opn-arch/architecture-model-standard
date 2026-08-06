"""Mermaid diagram generators for architecture models."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def _rel_type_str(rel_type: object) -> str:
    """Extract string value from a relationship type."""
    return rel_type.value if hasattr(rel_type, "value") else str(rel_type)


def generate_component_diagram(model: "ArchitectureModel") -> str:
    """Generate a Mermaid graph TD showing components and their relationships."""
    lines = ["# Component Diagram", "", "```mermaid", "graph TD"]

    for comp in model.entities.components:
        lines.append(f"    {comp.id}[{comp.name}]")

    for rel in model.relationships:
        rt = _rel_type_str(rel.type)
        if rt in ("depends-on", "uses"):
            lines.append(f"    {rel.from_id} -->|{rt}| {rel.to_id}")

    lines.append("```")
    return "\n".join(lines) + "\n"


def generate_use_case_diagram(model: "ArchitectureModel") -> str:
    """Generate Mermaid sequence diagrams for use-case behaviors."""
    use_cases = [b for b in model.entities.behaviors if b.id.startswith("UC-")]
    if not use_cases:
        return "# Use Case Diagrams\n\nNo use cases found.\n"

    # Build behavior-name -> component mapping via realizes relationships
    beh_map: dict[str, str] = {}
    for beh in model.entities.behaviors:
        beh_map[beh.name] = beh.id

    comp_for_beh: dict[str, str] = {}
    comp_name_map: dict[str, str] = {c.id: c.name for c in model.entities.components}
    for rel in model.relationships:
        rt = _rel_type_str(rel.type)
        if rt == "realizes":
            comp_for_beh[rel.to_id] = rel.from_id

    sections: list[str] = ["# Use Case Diagrams"]

    for uc in use_cases:
        sections.append(f"\n## {uc.id}: {uc.name}\n")
        if uc.trigger:
            sections.append(f"**Trigger:** {uc.trigger}\n")
        sections.append("```mermaid")
        sections.append("sequenceDiagram")

        actor = uc.actor or "User"
        sections.append(f"    actor {actor}")

        prev_comp: str | None = None
        for step_name in uc.steps:
            beh_id = beh_map.get(step_name, "")
            comp_id = comp_for_beh.get(beh_id, "")
            comp_name = comp_name_map.get(comp_id, step_name)

            if prev_comp is None:
                sections.append(f"    {actor}->>+{comp_name}: {step_name}")
            elif comp_id == prev_comp:
                sections.append(f"    Note over {comp_name}: {step_name}")
            else:
                prev_name = comp_name_map.get(prev_comp, prev_comp)
                sections.append(f"    {prev_name}->>+{comp_name}: {step_name}")

            prev_comp = comp_id

        sections.append("```")

    return "\n".join(sections) + "\n"


def generate_system_boundary_diagram(model: "ArchitectureModel") -> str:
    """Generate a Mermaid graph TD with subgraph per system."""
    comp_name_map = {c.id: c.name for c in model.entities.components}

    lines = ["# System Boundary Diagram", "", "```mermaid", "graph TD"]

    systems = getattr(model.entities, "systems", []) or []
    assigned: set[str] = set()

    for sys in systems:
        lines.append(f"    subgraph {sys.id}[{sys.name}]")
        for cid in sys.component_ids:
            name = comp_name_map.get(cid, cid)
            lines.append(f"        {cid}[{name}]")
            assigned.add(cid)
        lines.append("    end")

    # Unassigned components
    for comp in model.entities.components:
        if comp.id not in assigned:
            lines.append(f"    {comp.id}[{comp.name}]")

    # Edges
    for rel in model.relationships:
        rt = _rel_type_str(rel.type)
        if rt in ("depends-on", "uses"):
            lines.append(f"    {rel.from_id} -->|{rt}| {rel.to_id}")

    lines.append("```")
    return "\n".join(lines) + "\n"


def generate_all_diagrams(
    model: "ArchitectureModel", output_dir: Path
) -> list[Path]:
    """Generate all diagrams, write to output_dir, return list of paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []

    generators = [
        ("component-diagram.md", generate_component_diagram),
        ("use-case-diagrams.md", generate_use_case_diagram),
        ("system-boundary-diagram.md", generate_system_boundary_diagram),
    ]

    for filename, gen_fn in generators:
        md = gen_fn(model)
        p = output_dir / filename
        p.write_text(md)
        paths.append(p)

    return paths
