"""Plugin / Extension Guide document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def generate_plugin_guide(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Plugin / Extension Guide: {project}")
    lines.append("")

    ext_comps = [c for c in model.entities.components
                 if any(kw in c.name.lower() for kw in ("plugin", "extension", "backend", "adapter"))]

    lines.append("## Extension Points")
    lines.append("")
    if ext_comps:
        for comp in ext_comps:
            lines.append(f"### {comp.name} ({comp.id})")
            if comp.responsibilities:
                lines.append(f"**Purpose:** {'; '.join(comp.responsibilities)}")
            if comp.files:
                lines.append(f"**Files:** {', '.join(f'`{f}`' for f in comp.files[:5])}")
            if hasattr(comp, "interfaces") and comp.interfaces:
                lines.append("**Interfaces:**")
                for ci in comp.interfaces[:10]:
                    lines.append(f"- {ci.name} ({getattr(ci, 'kind', '—')})")
            lines.append("")
    else:
        lines.append("*No plugin/extension components identified.*")
    lines.append("")

    return "\n".join(lines)
