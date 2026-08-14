"""API Reference document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def generate_api_reference(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# API Reference: {project}")
    lines.append("")

    # Collect REST/HTTP interfaces
    rest_interfaces = [i for i in model.entities.interfaces
                       if str(getattr(i.type, "value", i.type)).upper() in ("REST", "WEBSOCKET")]

    lines.append("## Endpoints")
    lines.append("")
    if rest_interfaces:
        for iface in rest_interfaces:
            lines.append(f"### {iface.name}")
            lines.append("")
            if iface.endpoints:
                lines.append("| Method | Path | Description |")
                lines.append("|--------|------|-------------|")
                for ep in iface.endpoints:
                    lines.append(f"| {ep.get('method', '—')} | `{ep.get('path', '—')}` | {ep.get('description', '—')} |")
            lines.append("")
    else:
        lines.append("*No REST/HTTP interfaces defined.*")
    lines.append("")

    # Component signatures that look like API handlers
    lines.append("## Handler Signatures")
    lines.append("")
    for comp in model.entities.components:
        if hasattr(comp, "signatures") and comp.signatures:
            api_sigs = [s for s in comp.signatures
                        if any(d in str(getattr(s, "decorators", []))
                               for d in ("route", "api_view", "get", "post", "put", "delete"))]
            if api_sigs:
                lines.append(f"### {comp.name}")
                for sig in api_sigs:
                    lines.append(f"- `{sig.name}({', '.join(getattr(sig, 'params', []))})`")
                    if getattr(sig, "returns", None):
                        lines.append(f"  Returns: `{sig.returns}`")
                lines.append("")

    return "\n".join(lines)
