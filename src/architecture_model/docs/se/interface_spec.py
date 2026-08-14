# src/architecture_model/docs/se/interface_spec.py
"""Interface Specification document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_interface_spec(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Interface Specification: {project}")
    lines.append("")

    comp_map = {c.id: c for c in model.entities.components}

    # --- Interface Inventory ---
    lines.append("## Interface Inventory")
    lines.append("")
    if model.entities.interfaces:
        lines.append("| ID | Interface | Type | Protocol | Provider | Consumer |")
        lines.append("|----|-----------|------|----------|----------|----------|")
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"| {iface.id} | {iface.name} | {itype} | {iface.protocol or '—'} | {iface.provider or '—'} | {iface.consumer or '—'} |")
    else:
        lines.append("*No interfaces defined in the model.*")
    lines.append("")

    # --- Interface Details ---
    lines.append("## Interface Details")
    lines.append("")
    if model.entities.interfaces:
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"### {iface.name}")
            lines.append("")
            lines.append(f"- **ID:** {iface.id}")
            lines.append(f"- **Type:** {itype}")
            if iface.protocol:
                lines.append(f"- **Protocol:** {iface.protocol}")
            if iface.data_format:
                lines.append(f"- **Data Format:** {iface.data_format}")
            if iface.provider:
                prov = comp_map.get(iface.provider)
                lines.append(f"- **Provider:** {prov.name if prov else iface.provider}")
            if iface.consumer:
                cons = comp_map.get(iface.consumer)
                lines.append(f"- **Consumer:** {cons.name if cons else iface.consumer}")
            lines.append("")

            if iface.endpoints:
                lines.append("**Endpoints:**")
                lines.append("")
                lines.append("| Method | Path | Description |")
                lines.append("|--------|------|-------------|")
                for ep in iface.endpoints:
                    method = ep.get("method", "—")
                    path = ep.get("path", "—")
                    desc = ep.get("description", "—")
                    lines.append(f"| {method} | `{path}` | {desc} |")
                lines.append("")

            if iface.schema:
                lines.append(f"**Schema:** `{iface.schema}`")
                lines.append("")
    else:
        lines.append("*No interfaces to detail.*")
        lines.append("")

    # --- Component-Level Interfaces ---
    lines.append("## Component-Level Interfaces")
    lines.append("")
    comps_with_ifaces = [(c, c.interfaces) for c in model.entities.components
                         if hasattr(c, "interfaces") and c.interfaces]
    if comps_with_ifaces:
        for comp, ifaces in comps_with_ifaces:
            lines.append(f"### {comp.name} ({comp.id})")
            lines.append("")
            lines.append("| Name | Kind | Target | Signature |")
            lines.append("|------|------|--------|-----------|")
            for ci in ifaces[:20]:
                kind = getattr(ci, "kind", "—")
                target = getattr(ci, "target_component", "—")
                sig = getattr(ci, "signature", "—")
                lines.append(f"| {ci.name} | {kind} | {target} | `{sig}` |")
            if len(ifaces) > 20:
                lines.append(f"| ... | | | *{len(ifaces) - 20} more* |")
            lines.append("")
    else:
        lines.append("*No component-level interfaces defined.*")
    lines.append("")

    return "\n".join(lines)
