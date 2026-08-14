"""Data Model document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def generate_data_model(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Data Model: {project}")
    lines.append("")

    # Data-layer components
    data_comps = [c for c in model.entities.components
                  if (getattr(c, "layer", "") or "").lower() in ("data", "db", "database")
                  or (getattr(c, "kind", None) and
                      str(getattr(c.kind, "value", c.kind)) in ("data-store", "data-model"))]

    lines.append("## Data Components")
    lines.append("")
    if data_comps:
        for comp in data_comps:
            lines.append(f"### {comp.name} ({comp.id})")
            if comp.files:
                lines.append(f"**Files:** {', '.join(f'`{f}`' for f in comp.files[:5])}")
            if hasattr(comp, "symbols") and comp.symbols:
                lines.append("**Models/Classes:**")
                for sym in comp.symbols[:20]:
                    lines.append(f"- `{sym.name}`")
            if hasattr(comp, "fields") and comp.fields:
                lines.append("**Fields:**")
                lines.append("| Name | Type |")
                lines.append("|------|------|")
                for field in comp.fields:
                    lines.append(f"| {field.name} | {getattr(field, 'type', '—')} |")
            lines.append("")
    else:
        lines.append("*No data-layer components identified.*")
    lines.append("")

    return "\n".join(lines)
