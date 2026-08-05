"""Integration flow generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def _rel_type_str(rel_type) -> str:
    return rel_type.value if hasattr(rel_type, 'value') else str(rel_type)


def generate_integration_flows(model: "ArchitectureModel") -> str:
    """Generate integration flow documentation for cross-component relationships."""
    lines: list[str] = []

    lines.append(f"# Integration Flows: {model.meta.project}")
    lines.append("")

    components = getattr(model.entities, 'components', []) or []
    comp_map = {c.id: c for c in components}
    comp_ids = set(comp_map.keys())

    # Cross-component relationships: both from_id and to_id are components, and different
    cross = [
        r for r in model.relationships
        if r.from_id in comp_ids and r.to_id in comp_ids and r.from_id != r.to_id
    ]

    if not cross:
        lines.append("No cross-component integration flows detected.")
        return "\n".join(lines)

    # Mermaid flowchart
    lines.append("```mermaid")
    lines.append("flowchart TD")
    for r in cross:
        src = comp_map[r.from_id]
        tgt = comp_map[r.to_id]
        lines.append(f"  {r.from_id}[{src.name}] -->|{_rel_type_str(r.type)}| {r.to_id}[{tgt.name}]")
    lines.append("```")
    lines.append("")

    # Sections per relationship
    for r in cross:
        src = comp_map[r.from_id]
        tgt = comp_map[r.to_id]
        lines.append(f"## {src.name} → {tgt.name} ({_rel_type_str(r.type)})")
        lines.append(f"{r.description or '—'}")
        lines.append("")
        lines.append(f"**Source:** {src.id} ({src.name})")
        lines.append(f"**Target:** {tgt.id} ({tgt.name})")
        lines.append("")

    return "\n".join(lines)
