# src/architecture_model/docs/se/maintenance_manual.py
"""Maintenance Manual document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_maintenance_manual(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Maintenance Manual: {project}")
    lines.append("")

    comp_map = {c.id: c for c in model.entities.components}
    deps = [r for r in model.relationships if _rel_type_str(r.type) == "depends-on"]

    # --- Component Inventory ---
    lines.append("## Component Inventory")
    lines.append("")
    if model.entities.components:
        lines.append("| Component | Kind | Layer | Files | Signatures | Test Contracts |")
        lines.append("|-----------|------|-------|-------|-----------|----------------|")
        for comp in model.entities.components:
            kind = comp.kind.value if hasattr(comp.kind, "value") else str(comp.kind) if comp.kind else "—"
            layer = getattr(comp, "layer", "—") or "—"
            files = len(comp.files) if comp.files else 0
            sigs = len(comp.signatures) if hasattr(comp, "signatures") and comp.signatures else 0
            tests = len(comp.test_contracts) if hasattr(comp, "test_contracts") and comp.test_contracts else 0
            lines.append(f"| {comp.name} ({comp.id}) | {kind} | {layer} | {files} | {sigs} | {tests} |")
    else:
        lines.append("*No components defined.*")
    lines.append("")

    # --- Dependency Impact Analysis ---
    lines.append("## Dependency Impact Analysis")
    lines.append("")
    # For each component, show what depends on it (fan-in) and what it depends on (fan-out)
    if deps:
        lines.append("| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |")
        lines.append("|-----------|---------------------|---------------------|-------------|")
        for comp in model.entities.components:
            fan_out = [r.to_id for r in deps if r.from_id == comp.id]
            fan_in = [r.from_id for r in deps if r.to_id == comp.id]
            risk = "HIGH" if len(fan_in) >= 5 else "MEDIUM" if len(fan_in) >= 2 else "LOW"
            out_names = ", ".join(comp_map[x].name for x in fan_out if x in comp_map) or "—"
            in_names = ", ".join(comp_map[x].name for x in fan_in if x in comp_map) or "—"
            lines.append(f"| {comp.name} | {out_names} | {in_names} | {risk} |")
    else:
        lines.append("*No dependency relationships defined.*")
    lines.append("")

    # --- Modification Procedures ---
    lines.append("## Modification Procedures")
    lines.append("")
    lines.append("For each component, the following files and dependencies must be considered:")
    lines.append("")
    for comp in model.entities.components:
        lines.append(f"### {comp.name} ({comp.id})")
        lines.append("")
        if comp.files:
            lines.append("**Files:**")
            for f in comp.files[:20]:
                lines.append(f"- `{f}`")
            if len(comp.files) > 20:
                lines.append(f"- *...and {len(comp.files) - 20} more files*")
        downstream = [comp_map[r.from_id].name for r in deps
                      if r.to_id == comp.id and r.from_id in comp_map]
        if downstream:
            lines.append(f"**Downstream dependents (must re-test):** {', '.join(downstream)}")
        if comp.responsibilities:
            lines.append(f"**Responsibilities:** {'; '.join(comp.responsibilities)}")
        lines.append("")

    # --- Known Constraints ---
    lines.append("## Known Constraints")
    lines.append("")
    constrained = [r for r in model.relationships if _rel_type_str(r.type) == "constrained-by"]
    con_map = {c.id: c for c in model.entities.constraints}
    if constrained:
        lines.append("| Component | Constraint | Type | Detail |")
        lines.append("|-----------|-----------|------|--------|")
        for rel in constrained:
            comp_name = comp_map[rel.from_id].name if rel.from_id in comp_map else rel.from_id
            con = con_map.get(rel.to_id)
            if con:
                from architecture_model.docs.se.requirements_analysis import _constraint_type_str
                ctype = _constraint_type_str(con.type)
                detail = f"{con.metric}: {con.threshold}" if con.metric else con.rationale or "—"
                lines.append(f"| {comp_name} | {con.name} | {ctype} | {detail} |")
    else:
        lines.append("*No constraint allocations defined.*")
    lines.append("")

    return "\n".join(lines)
