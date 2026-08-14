"""CLI Reference document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def generate_cli_reference(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# CLI Reference: {project}")
    lines.append("")

    cli_interfaces = [i for i in model.entities.interfaces
                      if str(getattr(i.type, "value", i.type)).upper() == "CLI"]
    cli_comps = [c for c in model.entities.components
                 if getattr(c, "kind", None) and str(getattr(c.kind, "value", c.kind)) == "cli"]

    lines.append("## CLI Interfaces")
    lines.append("")
    if cli_interfaces:
        for iface in cli_interfaces:
            lines.append(f"### {iface.name}")
            if iface.endpoints:
                for ep in iface.endpoints:
                    lines.append(f"- `{ep.get('path', ep.get('command', '—'))}`")
            lines.append("")
    lines.append("")

    lines.append("## CLI Components")
    lines.append("")
    if cli_comps:
        for comp in cli_comps:
            lines.append(f"### {comp.name}")
            if comp.files:
                lines.append(f"Files: {', '.join(f'`{f}`' for f in comp.files[:10])}")
            if hasattr(comp, "signatures") and comp.signatures:
                lines.append("Commands/Functions:")
                for sig in comp.signatures[:20]:
                    lines.append(f"- `{sig.name}`")
            lines.append("")
    else:
        lines.append("*No CLI components identified.*")
    lines.append("")

    return "\n".join(lines)
