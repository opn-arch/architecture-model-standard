"""Deployment Guide document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_deployment_guide(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Deployment Guide: {project}")
    lines.append("")

    lines.append("## Technology Constraints")
    lines.append("")
    tech = [c for c in model.entities.constraints if _constraint_type_str(c.type) == "technology"]
    ops = [c for c in model.entities.constraints if _constraint_type_str(c.type) == "operational"]
    for con in tech + ops:
        lines.append(f"- **{con.name}** ({_constraint_type_str(con.type)}): {con.rationale or '—'}")
    if not tech and not ops:
        lines.append("*No deployment constraints defined.*")
    lines.append("")

    lines.append("## Component Deployment")
    lines.append("")
    lines.append("| Component | Kind | Layer |")
    lines.append("|-----------|------|-------|")
    for comp in model.entities.components:
        kind = comp.kind.value if hasattr(comp.kind, "value") else str(comp.kind) if comp.kind else "—"
        lines.append(f"| {comp.name} | {kind} | {getattr(comp, 'layer', '—') or '—'} |")
    lines.append("")

    return "\n".join(lines)
