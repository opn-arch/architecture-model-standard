"""Generate NxN component dependency matrix."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_dependency_matrix(model: "ArchitectureModel") -> str:
    """Generate an NxN dependency matrix as markdown."""
    lines = ["# Dependency Matrix", ""]
    components = model.entities.components if hasattr(model.entities, 'components') else []
    if not components:
        lines.append("No components found.")
        return "\n".join(lines)

    # Build adjacency from ComponentInterface
    requires_from: dict[str, set[str]] = {}
    for comp in components:
        for iface in (comp.interfaces or []):
            if iface.kind == "requires" and iface.target_component:
                requires_from.setdefault(comp.id, set()).add(iface.target_component)
            elif iface.kind == "provides" and iface.target_component:
                requires_from.setdefault(iface.target_component, set()).add(comp.id)

    # Also from relationships
    for rel in (model.relationships or []):
        rt = rel.type if hasattr(rel, 'type') else str(rel.get('type', ''))
        if 'depends' in str(rt).lower() or 'uses' in str(rt).lower():
            from_id = rel.from_id if hasattr(rel, 'from_id') else rel.get('from', '')
            to_id = rel.to_id if hasattr(rel, 'to_id') else rel.get('to', '')
            if from_id and to_id:
                requires_from.setdefault(from_id, set()).add(to_id)

    active_ids = set()
    for k, v in requires_from.items():
        active_ids.add(k)
        active_ids.update(v)

    if not active_ids:
        lines.append("No dependencies detected.")
        return "\n".join(lines)

    active_comps = sorted([c for c in components if c.id in active_ids], key=lambda c: c.id)
    
    # Header row
    header = "| | " + " | ".join(f"**{c.name}**" for c in active_comps) + " |"
    sep = "|---|" + "|".join("---" for _ in active_comps) + "|"
    lines.extend([header, sep])

    for row in active_comps:
        cells = []
        for col in active_comps:
            if row.id == col.id:
                cells.append("·")
            elif col.id in requires_from.get(row.id, set()):
                cells.append("→")
            elif row.id in requires_from.get(col.id, set()):
                cells.append("←")
            else:
                cells.append("")
        lines.append(f"| **{row.name}** | " + " | ".join(cells) + " |")

    lines.extend(["", "**Legend:** → = requires from column, ← = provides to column, · = self", ""])
    return "\n".join(lines)
