"""Functional (Capability) Analysis document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_functional_analysis(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Functional Analysis: {project}")
    lines.append("")

    # --- Capability Inventory ---
    lines.append("## Capability Inventory")
    lines.append("")
    if model.entities.capabilities:
        lines.append("| ID | Capability | Priority | Status | Description |")
        lines.append("|----|-----------|----------|--------|-------------|")
        for cap in model.entities.capabilities:
            prio = cap.priority.value if hasattr(cap.priority, "value") else str(cap.priority) if cap.priority else "—"
            desc = cap.description or "—"
            status = cap.status.value if hasattr(cap.status, "value") else str(cap.status)
            lines.append(f"| {cap.id} | {cap.name} | {prio} | {status} | {desc} |")
    else:
        lines.append("*No capabilities defined.*")
    lines.append("")

    # --- Functional Decomposition ---
    lines.append("## Functional Decomposition")
    lines.append("")
    # Build hierarchy from contains relationships
    contains = [r for r in model.relationships if _rel_type_str(r.type) == "contains"]
    cap_map = {c.id: c for c in model.entities.capabilities}
    children: dict[str, list[str]] = {}
    for rel in contains:
        if rel.from_id in cap_map and rel.to_id in cap_map:
            children.setdefault(rel.from_id, []).append(rel.to_id)

    top_level = [c for c in model.entities.capabilities
                 if c.id not in {rel.to_id for rel in contains if rel.from_id in cap_map}]

    if top_level:
        lines.append("```mermaid")
        lines.append("graph TD")
        for cap in top_level:
            safe_name = cap.name.replace('"', "'")
            lines.append(f'    {cap.id}["{safe_name}"]')
            for child_id in children.get(cap.id, []):
                if child_id in cap_map:
                    child_name = cap_map[child_id].name.replace('"', "'")
                    lines.append(f'    {cap.id} --> {child_id}["{child_name}"]')
        lines.append("```")
    lines.append("")

    # --- Capability-Component Mapping ---
    lines.append("## Capability-Component Mapping")
    lines.append("")
    realizes = [r for r in model.relationships if _rel_type_str(r.type) == "realizes"]
    comp_map = {c.id: c for c in model.entities.components}

    if realizes:
        lines.append("| Capability | Realized By | Component Kind |")
        lines.append("|-----------|------------|----------------|")
        for cap in model.entities.capabilities:
            realizers = [r.from_id for r in realizes if r.to_id == cap.id]
            for comp_id in realizers:
                comp = comp_map.get(comp_id)
                if comp:
                    kind = comp.kind.value if hasattr(comp.kind, "value") else str(comp.kind) if comp.kind else "—"
                    lines.append(f"| {cap.name} | {comp.name} ({comp.id}) | {kind} |")
            if not realizers:
                lines.append(f"| {cap.name} | *unrealized* | — |")
    else:
        lines.append("*No realizes relationships defined.*")
    lines.append("")

    # --- Behavioral Coverage ---
    lines.append("## Behavioral Coverage")
    lines.append("")
    traces = [r for r in model.relationships if _rel_type_str(r.type) == "traces-to"]
    beh_map = {b.id: b for b in model.entities.behaviors}
    if model.entities.behaviors:
        lines.append(f"Total behaviors: {len(model.entities.behaviors)}")
        lines.append("")
        traced = {r.to_id for r in traces if r.to_id in beh_map}
        untraced = [b for b in model.entities.behaviors if b.id not in traced]
        if untraced:
            lines.append(f"**Untraced behaviors:** {len(untraced)}")
            for b in untraced[:10]:
                lines.append(f"- {b.name} ({b.id})")
            if len(untraced) > 10:
                lines.append(f"- *...and {len(untraced) - 10} more*")
    else:
        lines.append("*No behaviors defined.*")
    lines.append("")

    return "\n".join(lines)
