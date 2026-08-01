"""Generate Interface Control Document."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_icd(model: "ArchitectureModel") -> str:
    """Generate ICD documenting inter-component interfaces."""
    lines = ["# Interface Control Document", ""]
    lines.append(f"**Project:** {model.meta.project}")
    lines.append("")

    components = model.entities.components if hasattr(model.entities, 'components') else []
    comp_map = {c.id: c for c in components}

    interfaces = []
    for comp in components:
        for iface in (comp.interfaces or []):
            if iface.kind == "provides" and iface.target_component:
                consumer = comp_map.get(iface.target_component)
                sigs = [s for s in (comp.signatures or []) if s.name in (iface.symbols or [])]
                interfaces.append((comp, consumer, iface.symbols or [], sigs))

    if not interfaces:
        lines.append("No inter-component interfaces detected.")
        return "\n".join(lines)

    lines.append(f"**Total Interfaces:** {len(interfaces)}")
    lines.append("")

    by_provider: dict[str, list] = {}
    for provider, consumer, syms, sigs in interfaces:
        by_provider.setdefault(provider.id, []).append((provider, consumer, syms, sigs))

    for provider_id in sorted(by_provider.keys()):
        entries = by_provider[provider_id]
        provider = comp_map[provider_id]
        lines.append(f"## {provider.name} ({provider.id})")
        lines.append("")
        if provider.contract:
            lines.append(f"**Contract:** {provider.contract}")
            lines.append("")

        for _, consumer, syms, sigs in entries:
            cname = f"{consumer.name} ({consumer.id})" if consumer else "Unknown"
            lines.append(f"### → {cname}")
            lines.append("")
            lines.append(f"**Symbols:** {', '.join(f'`{s}`' for s in syms) if syms else 'N/A'}")
            lines.append("")
            if sigs:
                lines.append("| Function | Signature | Description |")
                lines.append("|----------|-----------|-------------|")
                for sig in sigs:
                    params = ", ".join(sig.params) if sig.params else ""
                    doc = (getattr(sig, 'docstring', '') or getattr(sig, 'body_hint', '') or "")[:60]
                    lines.append(f"| `{sig.name}` | `({params}) → {sig.returns or 'None'}` | {doc} |")
                lines.append("")

    return "\n".join(lines)
