"""Generate Mermaid diagrams from architecture models."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.types import ArchitectureModel


def _sanitize_id(node_id: str) -> str:
    """Replace hyphens with underscores for Mermaid compatibility."""
    return node_id.replace("-", "_")


def _short_name(name: str) -> str:
    """Keep node labels short."""
    return name


def generate_overview_diagram(model: ArchitectureModel) -> str:
    """Generate a flowchart showing behaviors, components grouped by f_block, and traces-to edges."""
    lines = ["flowchart TB"]

    # Group components by f_block
    fblock_groups: dict[str, list] = defaultdict(list)
    for comp in model.entities.components:
        fb = comp.f_block or "ungrouped"
        fblock_groups[fb].append(comp)

    # Get f_block display names from capabilities
    fblock_names: dict[str, str] = {}
    for cap in model.entities.capabilities:
        if cap.f_block:
            fblock_names[cap.f_block] = cap.name

    # Emit subgraphs for each f_block
    for fb in sorted(fblock_groups):
        comps = fblock_groups[fb]
        label = fblock_names.get(fb, fb)
        sid = _sanitize_id(fb)
        lines.append(f"    subgraph {sid}[{label}]")
        # If >8 components, only show parent (no f_block prefix in ID typically)
        if len(comps) > 8:
            parents = [c for c in comps if "." not in c.name]
            show = parents if parents else comps[:8]
        else:
            show = comps
        for comp in show:
            cid = _sanitize_id(comp.id)
            lines.append(f"        {cid}[{_short_name(comp.name)}]")
        if len(comps) > 8 and len(show) < len(comps):
            lines.append(f"        {sid}_more[...{len(comps) - len(show)} more]")
        lines.append("    end")

    # Emit behavior nodes (stadium shape)
    for beh in model.entities.behaviors:
        bid = _sanitize_id(beh.id)
        lines.append(f"    {bid}([{_short_name(beh.name)}])")

    # Emit traces-to edges
    for rel in model.relationships:
        if rel.type.value == "traces-to":
            fid = _sanitize_id(rel.from_id)
            tid = _sanitize_id(rel.to_id)
            lines.append(f"    {fid} -->|traces-to| {tid}")

    return "\n".join(lines)


def generate_block_diagram(
    parent_model: ArchitectureModel,
    sub_behaviors: list[dict],
    block_name: str,
    parent_behavior_id: str,
) -> str:
    """Generate a flowchart for one F-block showing parent behavior, sub-behaviors, and components."""
    lines = ["flowchart TB"]

    # Find the parent behavior
    parent_beh = None
    for b in parent_model.entities.behaviors:
        if b.id == parent_behavior_id:
            parent_beh = b
            break

    if parent_beh:
        pid = _sanitize_id(parent_beh.id)
        lines.append(f"    {pid}([{_short_name(parent_beh.name)}])")

    # Filter sub-behaviors for this parent
    block_subs = [sb for sb in sub_behaviors if sb.get("parent_behavior") == parent_behavior_id]

    if not block_subs:
        return ""

    # Emit sub-behavior nodes with steps
    for sb in block_subs:
        sid = _sanitize_id(sb["id"])
        label_parts = [sb["name"]]
        steps = sb.get("steps", [])
        for step in steps[:3]:
            label_parts.append(step)
        if len(steps) > 3:
            label_parts.append("...")
        label = "<br/>".join(label_parts)
        lines.append(f'    {sid}["{label}"]')

    # Contains edges from parent to sub-behaviors
    if parent_beh:
        pid = _sanitize_id(parent_beh.id)
        for sb in block_subs:
            sid = _sanitize_id(sb["id"])
            lines.append(f"    {pid} -->|contains| {sid}")

    # Traces-to edges from components to sub-behaviors
    sub_ids = {sb["id"] for sb in block_subs}
    comp_map: dict[str, str] = {}  # sub-behavior component field
    for sb in block_subs:
        if sb.get("component"):
            comp_map[sb["id"]] = sb["component"]

    # Show component -> sub-behavior traces
    shown_comps: set[str] = set()
    for sb_id, comp_id in comp_map.items():
        cid = _sanitize_id(comp_id)
        sid = _sanitize_id(sb_id)
        if comp_id not in shown_comps:
            # Find component name
            comp_name = comp_id
            for c in parent_model.entities.components:
                if c.id == comp_id:
                    comp_name = c.name
                    break
            lines.append(f"    {cid}[{comp_name}] -->|traces-to| {sid}")
            shown_comps.add(comp_id)
        else:
            lines.append(f"    {cid} -->|traces-to| {sid}")

    return "\n".join(lines)


def generate_dependency_diagram(model: ArchitectureModel) -> str:
    """Generate a flowchart showing inter-component dependencies grouped by f_block."""
    lines = ["flowchart LR"]

    # Group components by f_block
    fblock_groups: dict[str, list] = defaultdict(list)
    for comp in model.entities.components:
        fb = comp.f_block or "ungrouped"
        fblock_groups[fb].append(comp)

    # Get f_block display names
    fblock_names: dict[str, str] = {}
    for cap in model.entities.capabilities:
        if cap.f_block:
            fblock_names[cap.f_block] = cap.name

    # Emit subgraphs
    for fb in sorted(fblock_groups):
        comps = fblock_groups[fb]
        label = fblock_names.get(fb, fb)
        sid = _sanitize_id(fb)
        lines.append(f"    subgraph {sid}[{label}]")
        for comp in comps:
            cid = _sanitize_id(comp.id)
            lines.append(f"        {cid}[{_short_name(comp.name)}]")
        lines.append("    end")

    # Emit depends-on edges
    for rel in model.relationships:
        if rel.type.value == "depends-on":
            fid = _sanitize_id(rel.from_id)
            tid = _sanitize_id(rel.to_id)
            lines.append(f"    {fid} -->|depends-on| {tid}")

    return "\n".join(lines)
