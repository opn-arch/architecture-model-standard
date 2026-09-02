# src/architecture_model/docs/se/use_cases.py
"""Use Cases document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_use_cases(
    model: ArchitectureModel, manifest: object | None = None, *, diagram_reference: str = "",
) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Use Cases: {project}")
    lines.append("")

    actor_map = {a.id: a for a in model.entities.actors}

    # Build relationship lookup maps for v2.1 fields
    beh_to_comps: dict[str, list[str]] = {}
    comp_to_caps: dict[str, list[str]] = {}
    for r in model.relationships:
        rt = _rel_type_str(r.type)
        if rt == "traces-to":
            beh_to_comps.setdefault(r.from_id, []).append(r.to_id)
        elif rt == "realizes":
            comp_to_caps.setdefault(r.from_id, []).append(r.to_id)

    comp_map = {c.id: c for c in model.entities.components}
    cap_map = {c.id: c for c in model.entities.capabilities}

    use_case_behaviors = [b for b in model.entities.behaviors if getattr(b, "actor", None)]
    other_behaviors = [b for b in model.entities.behaviors if not getattr(b, "actor", None)]

    # --- Actor-Goal Matrix ---
    lines.append("## Actor-Goal Matrix")
    lines.append("")
    if model.entities.actors and use_case_behaviors:
        actors = model.entities.actors
        lines.append("| Actor | Use Cases |")
        lines.append("|-------|----------|")
        for actor in actors:
            actor_ucs = [b.name for b in use_case_behaviors if b.actor == actor.id or b.actor == actor.name]
            if not actor_ucs:
                # Fallback: any behavior mentioning actor
                actor_ucs = [b.name for b in use_case_behaviors]
            lines.append(f"| {actor.name} | {'; '.join(actor_ucs[:10])} |")
    elif model.entities.actors:
        lines.append("| Actor | Goals |")
        lines.append("|-------|-------|")
        for actor in model.entities.actors:
            goals = "; ".join(actor.goals) if actor.goals else "—"
            lines.append(f"| {actor.name} | {goals} |")
    else:
        lines.append("*No actors defined.*")
    lines.append("")

    # --- Use Case Specifications ---
    lines.append("## Use Case Specifications")
    lines.append("")
    all_ucs = use_case_behaviors or other_behaviors[:20]
    for beh in all_ucs:
        lines.append(f"### UC: {beh.name}")
        lines.append("")
        lines.append(f"**ID:** {beh.id}")
        if beh.actor:
            actor = actor_map.get(beh.actor)
            lines.append(f"**Actor:** {actor.name if actor else beh.actor}")
        if beh.trigger:
            lines.append(f"**Trigger:** {beh.trigger}")
        if beh.preconditions:
            lines.append(f"**Preconditions:**")
            for pc in beh.preconditions:
                lines.append(f"- {pc}")
        if beh.steps:
            lines.append("**Main Flow:**")
            for i, step in enumerate(beh.steps, 1):
                lines.append(f"  {i}. {step}")
        if beh.postconditions:
            lines.append("**Postconditions:**")
            for pc in beh.postconditions:
                lines.append(f"- {pc}")
        # Show triggered behaviors
        triggers = [r for r in model.relationships
                    if r.from_id == beh.id and _rel_type_str(r.type) == "triggers"]
        if triggers:
            beh_map = {b.id: b for b in model.entities.behaviors}
            lines.append("**Triggers:**")
            for t in triggers:
                target = beh_map.get(t.to_id)
                lines.append(f"- {target.name if target else t.to_id}")

        # v2.1: Success criteria from MOEs via relationship chain
        linked_comps = beh_to_comps.get(beh.id, [])
        linked_caps: set[str] = set()
        for comp_id in linked_comps:
            for cap_id in comp_to_caps.get(comp_id, []):
                linked_caps.add(cap_id)

        moes: list[str] = []
        for cap_id in linked_caps:
            cap = cap_map.get(cap_id)
            if cap and getattr(cap, 'moes', None):
                moes.extend(cap.moes)

        failure_modes: list[str] = []
        for comp_id in linked_comps:
            comp = comp_map.get(comp_id)
            if comp and getattr(comp, 'failure_modes', None):
                failure_modes.extend(comp.failure_modes)

        if moes:
            lines.append("")
            lines.append("**Success Criteria:**")
            for moe in moes:
                lines.append(f"- {moe}")

        if failure_modes:
            lines.append("")
            lines.append("**Failure Modes:**")
            for fm in failure_modes:
                lines.append(f"- {fm}")

        lines.append("")

    if not all_ucs:
        lines.append("*No use case behaviors defined.*")
        lines.append("")

    # --- Use Case Diagram ---
    lines.append("## Use Case Diagram")
    lines.append("")
    if diagram_reference:
        lines.extend([diagram_reference, ""])
    if model.entities.actors and (use_case_behaviors or other_behaviors):
        lines.append("```mermaid")
        lines.append("graph LR")
        for actor in model.entities.actors:
            lines.append(f'    {actor.id}(("{actor.name}"))')
        for beh in (use_case_behaviors or other_behaviors)[:15]:
            safe_name = beh.name.replace('"', "'")
            lines.append(f'    {beh.id}["{safe_name}"]')
            if beh.actor:
                actor_id = beh.actor if beh.actor.startswith("ACT-") else None
                if not actor_id:
                    for a in model.entities.actors:
                        if a.name == beh.actor:
                            actor_id = a.id
                            break
                if actor_id:
                    lines.append(f"    {actor_id} --> {beh.id}")
        lines.append("```")
    else:
        lines.append("*Insufficient data for use case diagram.*")
    lines.append("")

    return "\n".join(lines)
