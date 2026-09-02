"""ConOps (Concept of Operations) document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_conops(
    model: ArchitectureModel, manifest: object | None = None, *, diagram_reference: str = "",
) -> str:
    """Generate Concept of Operations document from model data."""
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"

    lines.append(f"# Concept of Operations: {project}")
    lines.append("")

    # --- System Overview ---
    lines.append("## System Overview")
    lines.append("")
    cap_count = len(model.entities.capabilities)
    comp_count = len(model.entities.components)
    lines.append(f"{project} provides {cap_count} capabilities implemented across {comp_count} components.")
    lines.append("")
    if diagram_reference:
        lines.extend([diagram_reference, ""])
    if model.entities.capabilities:
        lines.append("**Core Capabilities:**")
        lines.append("")
        for cap in model.entities.capabilities:
            desc = f" - {cap.description}" if cap.description else ""
            lines.append(f"- **{cap.name}**{desc}")
            if getattr(cap, 'intent', None):
                lines.append(f"  - *Intent:* {cap.intent}")
            if getattr(cap, 'moes', None):
                lines.append(f"  - *Measures of Effectiveness:*")
                for moe in cap.moes:
                    lines.append(f"    - {moe}")
        lines.append("")

    # --- Stakeholders / Actors ---
    lines.append("## Stakeholders")
    lines.append("")
    if model.entities.actors:
        lines.append("| Actor | Type | Goals |")
        lines.append("|-------|------|-------|")
        for actor in model.entities.actors:
            atype = actor.type.value if hasattr(actor.type, "value") else str(actor.type)
            goals = "; ".join(actor.goals) if actor.goals else "—"
            lines.append(f"| {actor.name} | {atype} | {goals} |")
            if getattr(actor, 'intent', None):
                lines.append(f"")
                lines.append(f"*{actor.name} Intent:* {actor.intent}")
                lines.append(f"")
    else:
        lines.append("*No actors defined in the model.*")
    lines.append("")

    # --- Operational Scenarios (from behaviors) ---
    lines.append("## Operational Scenarios")
    lines.append("")
    use_cases = [b for b in model.entities.behaviors
                 if getattr(b, "actor", None) or "use_case" in str(getattr(b, "extensions", {}))]
    workflows = [b for b in model.entities.behaviors if b not in use_cases]

    if use_cases:
        lines.append("### User-Initiated Scenarios")
        lines.append("")
        for beh in use_cases:
            lines.append(f"#### {beh.name}")
            if beh.trigger:
                lines.append(f"**Trigger:** {beh.trigger}")
            if beh.actor:
                lines.append(f"**Actor:** {beh.actor}")
            if beh.preconditions:
                lines.append(f"**Preconditions:** {', '.join(beh.preconditions)}")
            if beh.steps:
                lines.append("**Flow:**")
                for i, step in enumerate(beh.steps, 1):
                    lines.append(f"  {i}. {step}")
            if beh.postconditions:
                lines.append(f"**Postconditions:** {', '.join(beh.postconditions)}")
            lines.append("")

    if workflows:
        lines.append("### System Workflows")
        lines.append("")
        for beh in workflows[:20]:  # cap to avoid huge docs
            trigger = f" (trigger: {beh.trigger})" if beh.trigger else ""
            steps = " -> ".join(beh.steps[:5]) if beh.steps else "—"
            lines.append(f"- **{beh.name}**{trigger}: {steps}")
        if len(workflows) > 20:
            lines.append(f"- *...and {len(workflows) - 20} more workflows*")
        lines.append("")

    if not use_cases and not workflows:
        lines.append("*No behaviors defined in the model.*")
        lines.append("")

    # --- System Context ---
    lines.append("## System Context")
    lines.append("")
    if model.entities.interfaces:
        lines.append("### External Interfaces")
        lines.append("")
        lines.append("| Interface | Type | Provider | Consumer |")
        lines.append("|-----------|------|----------|----------|")
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"| {iface.name} | {itype} | {iface.provider or '—'} | {iface.consumer or '—'} |")
        lines.append("")

        # Mermaid context diagram
        lines.append("```mermaid")
        lines.append("graph LR")
        for actor in model.entities.actors:
            lines.append(f'    {actor.id}["{actor.name}"]')
        lines.append(f'    SYS["{project}"]')
        for iface in model.entities.interfaces:
            if iface.consumer:
                lines.append(f'    {iface.consumer} -->|"{iface.name}"| SYS')
            if iface.provider:
                lines.append(f'    SYS -->|"{iface.name}"| {iface.provider}')
        lines.append("```")
        lines.append("")
    else:
        lines.append("*No interfaces defined in the model.*")
        lines.append("")

    # --- Degraded Operations & Failure Modes ---
    failure_comps = [(c.name, c.failure_modes) for c in model.entities.components
                     if getattr(c, 'failure_modes', None)]
    if failure_comps:
        lines.append("## Degraded Operations & Failure Modes")
        lines.append("")
        for comp_name, modes in failure_comps:
            lines.append(f"### {comp_name}")
            for mode in modes:
                lines.append(f"- {mode}")
            lines.append("")

    # --- Operational Constraints ---
    lines.append("## Operational Constraints")
    lines.append("")
    op_constraints = [c for c in model.entities.constraints
                      if _constraint_type_str(c.type) in ("operational", "performance", "reliability")]
    tech_constraints = [c for c in model.entities.constraints
                        if _constraint_type_str(c.type) in ("technology", "regulatory")]
    other_constraints = [c for c in model.entities.constraints
                         if c not in op_constraints and c not in tech_constraints]

    for label, items in [("Operational & Performance", op_constraints),
                         ("Technology & Regulatory", tech_constraints),
                         ("Other", other_constraints)]:
        if items:
            lines.append(f"### {label}")
            lines.append("")
            for con in items:
                ctype = _constraint_type_str(con.type)
                detail = ""
                if con.metric and con.threshold:
                    detail = f" ({con.metric}: {con.threshold})"
                rationale = f" — {con.rationale}" if con.rationale else ""
                lines.append(f"- **{con.name}** [{ctype}]{detail}{rationale}")
            lines.append("")

    if not model.entities.constraints:
        lines.append("*No constraints defined in the model.*")
        lines.append("")

    return "\n".join(lines)
