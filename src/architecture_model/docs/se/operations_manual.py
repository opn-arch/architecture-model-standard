# src/architecture_model/docs/se/operations_manual.py
"""Operations Manual document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)

def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_operations_manual(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Operations Manual: {project}")
    lines.append("")

    # --- Interface Catalog ---
    lines.append("## Interface Catalog")
    lines.append("")
    if model.entities.interfaces:
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"### {iface.name} ({itype})")
            lines.append("")
            if iface.protocol:
                lines.append(f"**Protocol:** {iface.protocol}")
            if iface.provider:
                lines.append(f"**Provider:** {iface.provider}")
            if iface.consumer:
                lines.append(f"**Consumer:** {iface.consumer}")
            if iface.endpoints:
                lines.append("")
                lines.append("| Method | Path |")
                lines.append("|--------|------|")
                for ep in iface.endpoints:
                    method = ep.get("method", "—")
                    path = ep.get("path", "—")
                    lines.append(f"| {method} | {path} |")
            lines.append("")
    else:
        lines.append("*No interfaces defined.*")
        lines.append("")

    # --- Operational Workflows ---
    lines.append("## Operational Workflows")
    lines.append("")
    workflows = [b for b in model.entities.behaviors if b.steps]
    if workflows:
        for beh in workflows[:20]:
            lines.append(f"### {beh.name}")
            if beh.trigger:
                lines.append(f"**Trigger:** {beh.trigger}")
            lines.append("")
            for i, step in enumerate(beh.steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")
        if len(workflows) > 20:
            lines.append(f"*...and {len(workflows) - 20} more workflows.*")
            lines.append("")
    else:
        lines.append("*No workflows with defined steps.*")
        lines.append("")

    # --- Configuration & Constraints ---
    lines.append("## Configuration & Constraints")
    lines.append("")
    op_constraints = [c for c in model.entities.constraints
                      if _constraint_type_str(c.type) in ("operational", "technology")]
    if op_constraints:
        for con in op_constraints:
            ctype = _constraint_type_str(con.type)
            lines.append(f"- **{con.name}** [{ctype}]")
            if con.rationale:
                lines.append(f"  - Rationale: {con.rationale}")
            if con.metric and con.threshold:
                lines.append(f"  - Metric: {con.metric} (threshold: {con.threshold})")
    else:
        lines.append("*No operational constraints defined.*")
    lines.append("")

    # --- Error Handling ---
    lines.append("## Error Handling")
    lines.append("")
    # Derive from behaviors with compensations or error steps
    error_behaviors = [b for b in model.entities.behaviors
                       if b.compensations or any("error" in s.lower() for s in b.steps)]
    if error_behaviors:
        for beh in error_behaviors[:10]:
            lines.append(f"### {beh.name}")
            if beh.compensations:
                lines.append("**Compensations:**")
                for comp in beh.compensations:
                    lines.append(f"- Step: {comp.step} -> Compensate: {comp.compensate}")
            lines.append("")
    else:
        lines.append("*No explicit error handling behaviors defined.*")
    lines.append("")

    return "\n".join(lines)
