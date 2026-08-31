"""Behavior Flows document generator.

Generates detailed behavior flow diagrams showing how behaviors connect to
components with step-by-step tracing and mermaid sequence diagrams.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_behavior_flows(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Behavior Flows: {project}")
    lines.append("")

    if not model.entities.behaviors:
        lines.append("*No behaviors defined in the model.*")
        lines.append("")
        return "\n".join(lines)

    # Build component lookup
    comp_map: dict[str, str] = {}  # id -> name
    for c in model.entities.components:
        comp_map[c.id] = c.name

    # Build behavior→component mapping via relationships
    beh_to_comps: dict[str, list[str]] = {}
    beh_triggers: dict[str, list[str]] = {}  # beh_id -> [triggered beh_ids]
    for rel in model.relationships:
        rt = _rel_type_str(rel.type)
        if rt in ("realizes", "traces-to") and rel.from_id.startswith("BEH"):
            beh_to_comps.setdefault(rel.from_id, []).append(rel.to_id)
        elif rt in ("realizes", "traces-to") and rel.to_id.startswith("BEH"):
            beh_to_comps.setdefault(rel.to_id, []).append(rel.from_id)
        elif rt == "triggers":
            beh_triggers.setdefault(rel.from_id, []).append(rel.to_id)
        elif rt == "contains" and rel.to_id.startswith("BEH"):
            # parent behavior contains child
            beh_triggers.setdefault(rel.from_id, []).append(rel.to_id)

    # --- Overview ---
    lines.append("## Behavior Overview")
    lines.append("")
    lines.append("| ID | Behavior | Type | Steps | Linked Components | Triggers |")
    lines.append("|----|----------|------|-------|-------------------|----------|")
    for beh in model.entities.behaviors:
        btype = getattr(beh, "behavior_type", "") or "—"
        steps = getattr(beh, "steps", []) or []
        linked = beh_to_comps.get(beh.id, [])
        linked_names = [comp_map.get(c, c) for c in linked]
        triggers = beh_triggers.get(beh.id, [])
        lines.append(
            f"| {beh.id} | {beh.name} | {btype} | {len(steps)} | "
            f"{', '.join(linked_names) or '—'} | {len(triggers)} |"
        )
    lines.append("")

    # --- Trigger Graph ---
    if beh_triggers:
        lines.append("## Behavior Trigger Graph")
        lines.append("")
        lines.append("```mermaid")
        lines.append("graph LR")
        beh_names: dict[str, str] = {}
        for beh in model.entities.behaviors:
            safe_name = beh.name.replace('"', "'")
            beh_names[beh.id] = safe_name
            lines.append(f'    {beh.id}["{safe_name}"]')
        for from_id, to_ids in beh_triggers.items():
            for to_id in to_ids:
                lines.append(f"    {from_id} --> {to_id}")
        lines.append("```")
        lines.append("")

    # --- Detailed Flows ---
    lines.append("## Detailed Behavior Flows")
    lines.append("")

    for beh in model.entities.behaviors:
        lines.append(f"### {beh.id}: {beh.name}")
        lines.append("")

        btype = getattr(beh, "behavior_type", "") or "unspecified"
        desc = getattr(beh, "description", "") or ""
        actor_id = getattr(beh, "actor_id", "") or ""
        cap_id = getattr(beh, "capability_id", "") or ""

        if desc:
            lines.append(f"**Description:** {desc}")
            lines.append("")
        lines.append(f"**Type:** {btype}")
        if actor_id:
            actor_name = next(
                (a.name for a in model.entities.actors if a.id == actor_id), actor_id
            )
            lines.append(f"**Actor:** {actor_name}")
        if cap_id:
            cap_name = next(
                (c.name for c in model.entities.capabilities if c.id == cap_id), cap_id
            )
            lines.append(f"**Capability:** {cap_name}")
        lines.append("")

        # Steps
        steps = getattr(beh, "steps", []) or []
        if steps:
            lines.append("**Steps:**")
            lines.append("")
            for i, step in enumerate(steps, 1):
                # Try to identify component references in step text
                step_str = str(step)
                comp_refs = [
                    f"`{cid}` ({comp_map[cid]})"
                    for cid in comp_map
                    if cid in step_str
                ]
                comp_note = f" → {', '.join(comp_refs)}" if comp_refs else ""
                lines.append(f"{i}. {step_str}{comp_note}")
            lines.append("")

        # Triggers
        triggered = beh_triggers.get(beh.id, [])
        if triggered:
            lines.append("**Triggers:**")
            for tid in triggered:
                tname = next(
                    (b.name for b in model.entities.behaviors if b.id == tid), tid
                )
                lines.append(f"- → {tname} (`{tid}`)")
            lines.append("")

        # Linked components
        linked = beh_to_comps.get(beh.id, [])
        if linked:
            lines.append("**Components involved:**")
            for cid in linked:
                cname = comp_map.get(cid, cid)
                lines.append(f"- `{cid}` — {cname}")
            lines.append("")

    return "\n".join(lines)
