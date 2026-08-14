# src/architecture_model/docs/se/requirements_analysis.py
"""Requirements Analysis document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)

def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_requirements_analysis(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Requirements Analysis: {project}")
    lines.append("")

    # --- Constraint Inventory ---
    lines.append("## Constraint Inventory")
    lines.append("")
    if model.entities.constraints:
        lines.append("| ID | Constraint | Type | Metric | Threshold | Rationale |")
        lines.append("|----|-----------|------|--------|-----------|-----------|")
        for con in model.entities.constraints:
            ctype = _constraint_type_str(con.type)
            lines.append(f"| {con.id} | {con.name} | {ctype} | {con.metric or '—'} | {con.threshold or '—'} | {con.rationale or '—'} |")
    else:
        lines.append("*No constraints defined.*")
    lines.append("")

    # --- Capability-Derived Requirements ---
    lines.append("## Capability-Derived Requirements")
    lines.append("")
    if model.entities.capabilities:
        for cap in model.entities.capabilities:
            if cap.requirements:
                lines.append(f"### {cap.name} ({cap.id})")
                for req in cap.requirements:
                    lines.append(f"- {req}")
                lines.append("")
        if not any(c.requirements for c in model.entities.capabilities):
            lines.append("*No explicit requirements on capabilities.*")
            lines.append("")
    else:
        lines.append("*No capabilities defined.*")
        lines.append("")

    # --- Requirements Traceability ---
    lines.append("## Requirements Traceability")
    lines.append("")
    constrained_by = [r for r in model.relationships if _rel_type_str(r.type) == "constrained-by"]
    traces_to = [r for r in model.relationships if _rel_type_str(r.type) == "traces-to"]
    satisfies = [r for r in model.relationships if _rel_type_str(r.type) == "satisfies"]

    all_trace_rels = constrained_by + traces_to + satisfies
    if all_trace_rels:
        lines.append("| From | Relationship | To | Description |")
        lines.append("|------|-------------|-----|-------------|")
        entity_map = {e.id: e.name for e in (list(model.entities.components) +
                      list(model.entities.capabilities) + list(model.entities.constraints) +
                      list(model.entities.behaviors))}
        for rel in all_trace_rels:
            from_name = entity_map.get(rel.from_id, rel.from_id)
            to_name = entity_map.get(rel.to_id, rel.to_id)
            rtype = _rel_type_str(rel.type)
            lines.append(f"| {from_name} | {rtype} | {to_name} | {rel.description or '—'} |")
    else:
        lines.append("*No traceability relationships defined.*")
    lines.append("")

    # --- Constraint Allocation ---
    lines.append("## Constraint Allocation")
    lines.append("")
    con_map = {c.id: c for c in model.entities.constraints}
    allocated = {r.to_id for r in constrained_by}
    unallocated = [c for c in model.entities.constraints if c.id not in allocated]

    if constrained_by:
        comp_map = {c.id: c for c in model.entities.components}
        lines.append("| Constraint | Allocated To |")
        lines.append("|-----------|-------------|")
        for con in model.entities.constraints:
            targets = [r.from_id for r in constrained_by if r.to_id == con.id]
            target_names = [comp_map[t].name if t in comp_map else t for t in targets]
            lines.append(f"| {con.name} | {', '.join(target_names) or '*unallocated*'} |")
    lines.append("")

    # --- Coverage Gaps ---
    lines.append("## Coverage Gaps")
    lines.append("")
    gaps: list[str] = []
    if unallocated:
        for c in unallocated:
            gaps.append(f"Constraint **{c.name}** ({c.id}) is not allocated to any component")
    unrealized_caps = []
    realizes = [r for r in model.relationships if _rel_type_str(r.type) == "realizes"]
    realized_ids = {r.to_id for r in realizes}
    for cap in model.entities.capabilities:
        if cap.id not in realized_ids:
            gaps.append(f"Capability **{cap.name}** ({cap.id}) has no realizing component")

    if gaps:
        for g in gaps:
            lines.append(f"- {g}")
    else:
        lines.append("*No coverage gaps detected.*")
    lines.append("")

    return "\n".join(lines)
