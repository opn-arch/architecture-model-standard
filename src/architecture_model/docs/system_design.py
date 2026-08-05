"""System design document generator."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def _rel_type_str(rel_type) -> str:
    return rel_type.value if hasattr(rel_type, 'value') else str(rel_type)


def generate_system_design(model: "ArchitectureModel", manifest=None) -> str:
    """Generate a system design document from an architecture model."""
    lines: list[str] = []

    lines.append(f"# System Design: {model.meta.project}")
    lines.append("")

    # Architecture Overview
    lines.append("## Architecture Overview")
    lines.append("")
    desc = getattr(model.meta, 'description', None)
    lines.append(desc if desc else "—")
    lines.append(f"Schema version: {model.meta.schema_version}")
    lines.append("")

    # Component Inventory
    components = getattr(model.entities, 'components', []) or []
    lines.append("## Component Inventory")
    lines.append("")
    if components:
        lines.append("| ID | Name | Status | Files | Behaviors |")
        lines.append("|----|------|--------|-------|-----------|")
        for comp in components:
            file_count = len(comp.files) if comp.files else 0
            # Count behaviors realized by this component
            beh_count = sum(
                1 for r in model.relationships
                if r.from_id == comp.id and _rel_type_str(r.type) == "realizes"
            )
            lines.append(f"| {comp.id} | {comp.name} | {comp.status or '—'} | {file_count} | {beh_count} |")
    else:
        lines.append("No components found.")
    lines.append("")

    # Layer Structure
    layers = getattr(model.entities, 'layers', []) or []
    if layers:
        lines.append("## Layer Structure")
        lines.append("")
        for layer in layers:
            lines.append(f"- **{layer.name}** ({layer.id})")
        lines.append("")

    # Key Behaviors
    behaviors = getattr(model.entities, 'behaviors', []) or []
    if behaviors:
        lines.append("## Key Behaviors")
        lines.append("")
        for beh in behaviors:
            lines.append(f"- **{beh.name}** ({beh.id})")
        lines.append("")

    # Relationship Summary
    lines.append("## Relationship Summary")
    lines.append("")
    if model.relationships:
        type_counts = Counter(_rel_type_str(r.type) for r in model.relationships)
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for rtype, count in sorted(type_counts.items()):
            lines.append(f"| {rtype} | {count} |")
    else:
        lines.append("No relationships found.")
    lines.append("")

    # Architecture Diagram
    deps = [r for r in model.relationships if _rel_type_str(r.type) == "depends-on"]
    if deps:
        comp_map = {c.id: c for c in components}
        lines.append("## Architecture Diagram")
        lines.append("")
        lines.append("```mermaid")
        lines.append("graph TD")
        for r in deps:
            src_name = comp_map[r.from_id].name if r.from_id in comp_map else r.from_id
            tgt_name = comp_map[r.to_id].name if r.to_id in comp_map else r.to_id
            lines.append(f"  {r.from_id}[{src_name}] --> {r.to_id}[{tgt_name}]")
        lines.append("```")
        lines.append("")

    return "\n".join(lines)
