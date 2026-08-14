# src/architecture_model/docs/se/risk_assessment.py
"""Risk Assessment document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)

def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_risk_assessment(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Risk Assessment: {project}")
    lines.append("")

    comp_map = {c.id: c for c in model.entities.components}
    deps = [r for r in model.relationships if _rel_type_str(r.type) == "depends-on"]

    # --- Risk Register ---
    lines.append("## Risk Register")
    lines.append("")
    risks: list[dict] = []

    # High fan-in components (single point of failure)
    for comp in model.entities.components:
        fan_in = sum(1 for r in deps if r.to_id == comp.id)
        if fan_in >= 5:
            risks.append({
                "id": f"RISK-DEP-{comp.id}",
                "category": "Dependency",
                "description": f"{comp.name} has {fan_in} dependents — single point of failure",
                "severity": "HIGH",
                "mitigation": f"Ensure thorough testing of {comp.name}; consider interface abstraction",
            })
        elif fan_in >= 3:
            risks.append({
                "id": f"RISK-DEP-{comp.id}",
                "category": "Dependency",
                "description": f"{comp.name} has {fan_in} dependents",
                "severity": "MEDIUM",
                "mitigation": "Monitor for breaking changes",
            })

    # Unverified constraints
    constrained = [r for r in model.relationships if _rel_type_str(r.type) == "constrained-by"]
    verified = {r.to_id for r in model.relationships if _rel_type_str(r.type) == "verifies"}
    for con in model.entities.constraints:
        if con.id not in verified:
            ctype = _constraint_type_str(con.type)
            severity = "HIGH" if ctype in ("security", "reliability", "performance") else "MEDIUM"
            risks.append({
                "id": f"RISK-CON-{con.id}",
                "category": "Constraint",
                "description": f"Constraint '{con.name}' ({ctype}) has no verification",
                "severity": severity,
                "mitigation": "Add verification tests or monitoring",
            })

    # Unrealized capabilities
    realizes = [r for r in model.relationships if _rel_type_str(r.type) == "realizes"]
    realized_ids = {r.to_id for r in realizes}
    for cap in model.entities.capabilities:
        if cap.id not in realized_ids:
            risks.append({
                "id": f"RISK-CAP-{cap.id}",
                "category": "Capability",
                "description": f"Capability '{cap.name}' has no realizing component",
                "severity": "HIGH",
                "mitigation": "Allocate to component or remove if not needed",
            })

    if risks:
        lines.append("| Risk ID | Category | Severity | Description | Mitigation |")
        lines.append("|---------|----------|----------|-------------|------------|")
        for risk in sorted(risks, key=lambda r: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(r["severity"], 3)):
            lines.append(f"| {risk['id']} | {risk['category']} | {risk['severity']} | {risk['description']} | {risk['mitigation']} |")
    else:
        lines.append("*No risks identified.*")
    lines.append("")

    # --- Dependency Risks ---
    lines.append("## Dependency Risks")
    lines.append("")
    # Components with high fan-out (fragile, many dependencies)
    high_fanout = [(c, sum(1 for r in deps if r.from_id == c.id))
                   for c in model.entities.components]
    high_fanout = [(c, n) for c, n in high_fanout if n >= 3]
    high_fanout.sort(key=lambda x: -x[1])

    if high_fanout:
        lines.append("Components with high dependency count (fragile to upstream changes):")
        lines.append("")
        lines.append("| Component | Dependencies (fan-out) |")
        lines.append("|-----------|----------------------|")
        for comp, count in high_fanout:
            lines.append(f"| {comp.name} | {count} |")
    else:
        lines.append("*No high fan-out components.*")
    lines.append("")

    # --- Constraint Risks ---
    lines.append("## Constraint Risks")
    lines.append("")
    if model.entities.constraints:
        unallocated = [c for c in model.entities.constraints
                       if c.id not in {r.to_id for r in constrained}]
        if unallocated:
            lines.append("**Unallocated constraints (no component owns them):**")
            lines.append("")
            for con in unallocated:
                lines.append(f"- {con.name} ({_constraint_type_str(con.type)})")
        else:
            lines.append("*All constraints allocated.*")
    else:
        lines.append("*No constraints defined.*")
    lines.append("")

    return "\n".join(lines)
