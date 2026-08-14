"""Security Analysis document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_security_analysis(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Security Analysis: {project}")
    lines.append("")

    sec_constraints = [c for c in model.entities.constraints if _constraint_type_str(c.type) == "security"]
    sec_comps = [c for c in model.entities.components
                 if any(kw in c.name.lower() for kw in ("auth", "security", "csrf", "permission", "token"))]

    lines.append("## Security Constraints")
    lines.append("")
    if sec_constraints:
        for con in sec_constraints:
            lines.append(f"- **{con.name}**: {con.rationale or '—'}")
    else:
        lines.append("*No explicit security constraints defined.*")
    lines.append("")

    lines.append("## Security-Related Components")
    lines.append("")
    if sec_comps:
        for comp in sec_comps:
            lines.append(f"### {comp.name} ({comp.id})")
            if comp.responsibilities:
                lines.append(f"Responsibilities: {'; '.join(comp.responsibilities)}")
            if comp.files:
                lines.append(f"Files: {', '.join(f'`{f}`' for f in comp.files[:5])}")
            lines.append("")
    else:
        lines.append("*No security-related components identified.*")
    lines.append("")

    return "\n".join(lines)
