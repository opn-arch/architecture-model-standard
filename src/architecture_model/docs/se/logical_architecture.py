"""Logical Architecture document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_logical_architecture(
    model: ArchitectureModel, manifest: object | None = None, *, diagram_reference: str = "",
) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Logical Architecture: {project}")
    lines.append("")

    # --- Layer Structure ---
    lines.append("## Layer Structure")
    lines.append("")
    if diagram_reference:
        lines.extend([diagram_reference, ""])
    if model.entities.layers:
        sorted_layers = sorted(model.entities.layers, key=lambda la: getattr(la, "order", 0))
        lines.append("| Order | Layer | Technologies | Directories |")
        lines.append("|-------|-------|-------------|-------------|")
        for layer in sorted_layers:
            tech = ", ".join(layer.technology) if layer.technology else "—"
            dirs = ", ".join(layer.directories) if layer.directories else "—"
            lines.append(f"| {getattr(layer, 'order', '—')} | {layer.name} | {tech} | {dirs} |")
    else:
        lines.append("*No layers defined.*")
    lines.append("")

    # --- Component Allocation ---
    lines.append("## Component Allocation")
    lines.append("")
    # Group components by layer
    by_layer: dict[str, list] = {}
    for comp in model.entities.components:
        layer = getattr(comp, "layer", "") or "unassigned"
        by_layer.setdefault(layer, []).append(comp)

    for layer_name, comps in sorted(by_layer.items()):
        lines.append(f"### {layer_name}")
        lines.append("")
        lines.append("| Component | Kind | Files | Responsibilities |")
        lines.append("|-----------|------|-------|------------------|")
        for comp in comps:
            kind = comp.kind.value if hasattr(comp.kind, "value") else str(comp.kind) if comp.kind else "—"
            files = len(comp.files) if comp.files else 0
            resps = "; ".join(comp.responsibilities[:3]) if comp.responsibilities else "—"
            lines.append(f"| {comp.name} ({comp.id}) | {kind} | {files} files | {resps} |")
            if getattr(comp, 'intent', None):
                lines.append(f"")
                lines.append(f"*Intent:* {comp.intent}")
            if getattr(comp, 'trade_offs', None):
                lines.append(f"")
                lines.append(f"*Trade-offs:*")
                for t in comp.trade_offs:
                    lines.append(f"- {t}")
                lines.append(f"")
        lines.append("")

    # --- Inter-Component Interfaces ---
    lines.append("## Inter-Component Interfaces")
    lines.append("")
    if model.entities.interfaces:
        lines.append("| Interface | Type | Protocol | Provider | Consumer |")
        lines.append("|-----------|------|----------|----------|----------|")
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"| {iface.name} | {itype} | {iface.protocol or '—'} | {iface.provider or '—'} | {iface.consumer or '—'} |")
            if getattr(iface, 'contract', None):
                lines.append(f"")
                lines.append(f"*Contract:* {iface.contract}")
                lines.append(f"")
    else:
        lines.append("*No interfaces defined.*")
    lines.append("")

    # --- Dependency Graph ---
    lines.append("## Dependency Graph")
    lines.append("")
    deps = [r for r in model.relationships if _rel_type_str(r.type) == "depends-on"]
    comp_map = {c.id: c for c in model.entities.components}

    if deps:
        lines.append("```mermaid")
        lines.append("graph TD")
        seen_comps: set[str] = set()
        for rel in deps:
            if rel.from_id in comp_map and rel.to_id in comp_map:
                from_name = comp_map[rel.from_id].name.replace('"', "'")
                to_name = comp_map[rel.to_id].name.replace('"', "'")
                if rel.from_id not in seen_comps:
                    lines.append(f'    {rel.from_id}["{from_name}"]')
                    seen_comps.add(rel.from_id)
                if rel.to_id not in seen_comps:
                    lines.append(f'    {rel.to_id}["{to_name}"]')
                    seen_comps.add(rel.to_id)
                lines.append(f"    {rel.from_id} --> {rel.to_id}")
        lines.append("```")
    else:
        lines.append("*No dependency relationships defined.*")
    lines.append("")

    return "\n".join(lines)
