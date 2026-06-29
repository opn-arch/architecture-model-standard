"""
LLM Context Formatter: Produce compact model representations for LLM prompt injection.

Implements the LLM Integration Protocol:
- LOAD: Serialize model (or slice) into compact text for system prompt
- QUERY: Answer structural questions from model data
- IMPACT: Determine what entities are affected by a proposed change

The key constraint is TOKEN BUDGET — we need maximum information density.
Format: structured YAML-like text, ~25:1 compression vs full artifact markdown.
"""

from __future__ import annotations

from typing import Optional

from ..core.types import (
    ArchitectureModel,
    Actor,
    Behavior,
    Capability,
    Component,
    Constraint,
    Interface,
    Layer,
    Relationship,
    Status,
)
from ..core.slicer import slice_by_fblock, slice_for_artifact


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def format_model_context(
    model: ArchitectureModel,
    max_tokens: int = 4000,
    detail_level: str = "standard",
) -> str:
    """
    Format the full model as compact LLM context.

    Args:
        model: Architecture model to format.
        max_tokens: Approximate token budget (1 token ~ 4 chars).
        detail_level: "minimal", "standard", or "full".

    Returns:
        Formatted text suitable for LLM system prompt injection.
    """
    char_budget = max_tokens * 4

    sections: list[str] = []
    sections.append(_format_header(model))

    if detail_level in ("standard", "full"):
        sections.append(_format_capabilities(model))
        sections.append(_format_actors(model))

    if detail_level == "full":
        sections.append(_format_behaviors(model))
        sections.append(_format_interfaces(model))
        sections.append(_format_layers(model))
        sections.append(_format_components(model))
        sections.append(_format_constraints(model))
    elif detail_level == "standard":
        sections.append(_format_behaviors_compact(model))
        sections.append(_format_interfaces_compact(model))
        sections.append(_format_layers_compact(model))

    sections.append(_format_relationships_compact(model))

    result = "\n".join(s for s in sections if s)

    # Truncate if over budget
    if len(result) > char_budget:
        result = result[: char_budget - 20] + "\n[... truncated]"

    return result


def format_fblock_context(
    model: ArchitectureModel,
    f_block: str,
    max_tokens: int = 2000,
) -> str:
    """
    Format context for a single F-block (for artifact section regeneration).

    Produces: capability description, related UCs, components, interfaces.
    """
    sliced = slice_by_fblock(model, f_block)
    return format_model_context(sliced, max_tokens=max_tokens, detail_level="full")


def format_artifact_context(
    model: ArchitectureModel,
    artifact_name: str,
    max_tokens: int = 3000,
) -> str:
    """
    Format context appropriate for regenerating a specific artifact.

    Uses artifact-specific slicing then formats at appropriate detail level.
    """
    sliced = slice_for_artifact(model, artifact_name)

    detail_map = {
        "functional-architecture": "full",
        "logical-architecture": "full",
        "use-cases": "full",
        "icd": "full",
        "requirements-analysis": "standard",
        "readme": "minimal",
    }
    detail = detail_map.get(artifact_name, "standard")

    return format_model_context(sliced, max_tokens=max_tokens, detail_level=detail)


def query_model(model: ArchitectureModel, question: str) -> str:
    """
    Answer a structural question from model data.

    Supports questions like:
    - "What realizes F3?" → list behaviors with tag F3
    - "What does UC-14 depend on?" → follow depends-on relationships
    - "What interfaces does F4 expose?" → filter interfaces by provider
    """
    q = question.lower().strip()

    # Pattern: "what realizes <X>?"
    if "realizes" in q:
        import re

        m = re.search(r"(f\d+|cap-\w+)", q, re.IGNORECASE)
        if m:
            target = m.group(1).upper()
            realizers = [
                r.from_id
                for r in model.relationships
                if r.type.value == "realizes" and target in r.to_id.upper()
            ]
            if realizers:
                lines = [f"Entities realizing {target}:"]
                for rid in realizers:
                    beh = next((b for b in model.entities.behaviors if b.id == rid), None)
                    if beh:
                        lines.append(f"  - {beh.id}: {beh.name} [{beh.status.value}]")
                    else:
                        lines.append(f"  - {rid}")
                return "\n".join(lines)
            return f"No entities realize {target}"

    # Pattern: "what does <X> depend on?"
    if "depend" in q:
        import re

        m = re.search(r"(uc-\d+|[a-z][\w-]+)", q, re.IGNORECASE)
        if m:
            source = m.group(1)
            deps = [
                r.to_id
                for r in model.relationships
                if r.from_id.lower() == source.lower() and r.type.value == "depends-on"
            ]
            if deps:
                return f"{source} depends on: {', '.join(deps)}"
            return f"{source} has no recorded dependencies"

    # Pattern: count/summary
    if "how many" in q or "count" in q:
        return (
            f"Model contains: {model.entity_count} entities, {model.relationship_count} relationships\n"
            f"  Actors: {len(model.entities.actors)}\n"
            f"  Capabilities: {len(model.entities.capabilities)}\n"
            f"  Behaviors: {len(model.entities.behaviors)}\n"
            f"  Interfaces: {len(model.entities.interfaces)}\n"
            f"  Constraints: {len(model.entities.constraints)}\n"
            f"  Layers: {len(model.entities.layers)}\n"
            f"  Components: {len(model.entities.components)}"
        )

    return f"Unable to answer: {question}\nTry: 'what realizes F3?', 'what does UC-14 depend on?', 'how many entities?'"


def impact_analysis(model: ArchitectureModel, entity_id: str, depth: int = 2) -> str:
    """
    Determine what entities are affected if a given entity changes.

    Traces relationships transitively up to `depth` levels.
    """
    affected: dict[str, int] = {}  # entity_id -> distance
    frontier = {entity_id}
    current_depth = 0

    while frontier and current_depth < depth:
        next_frontier: set[str] = set()
        for eid in frontier:
            for rel in model.relationships:
                # Forward direction: what depends on this?
                if rel.to_id == eid and rel.from_id not in affected and rel.from_id != entity_id:
                    affected[rel.from_id] = current_depth + 1
                    next_frontier.add(rel.from_id)
                # Reverse for 'realizes': if this behavior changes, its capability is affected
                if rel.from_id == eid and rel.to_id not in affected and rel.to_id != entity_id:
                    if rel.type.value in ("realizes", "contains", "exposes"):
                        affected[rel.to_id] = current_depth + 1
                        next_frontier.add(rel.to_id)
        frontier = next_frontier
        current_depth += 1

    if not affected:
        return f"No entities are directly affected by changes to {entity_id}"

    lines = [f"Impact analysis for {entity_id} (depth={depth}):"]
    for eid, dist in sorted(affected.items(), key=lambda x: x[1]):
        # Try to find name
        name = _find_entity_name(model, eid)
        lines.append(f"  {'  ' * dist}[depth {dist}] {eid}: {name}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _format_header(model: ArchitectureModel) -> str:
    return (
        f"# Architecture Model: {model.meta.project}\n"
        f"System: {model.meta.system} | Schema: {model.meta.schema_version}\n"
        f"Entities: {model.entity_count} | Relationships: {model.relationship_count}\n"
        f"Sources: {', '.join(model.meta.source_artifacts)}"
    )


def _format_capabilities(model: ArchitectureModel) -> str:
    if not model.entities.capabilities:
        return ""
    lines = ["\n## Capabilities (F-blocks)"]
    for cap in model.entities.capabilities:
        lines.append(f"  {cap.id} ({cap.f_block}): {cap.name} [{cap.status.value}]")
    return "\n".join(lines)


def _format_actors(model: ArchitectureModel) -> str:
    if not model.entities.actors:
        return ""
    lines = ["\n## Actors"]
    for actor in model.entities.actors:
        goals = "; ".join(actor.goals[:3]) if actor.goals else ""
        lines.append(f"  {actor.id}: {actor.name} ({actor.type.value}) — {goals}")
    return "\n".join(lines)


def _format_behaviors(model: ArchitectureModel) -> str:
    if not model.entities.behaviors:
        return ""
    lines = ["\n## Behaviors (Use Cases)"]
    for beh in model.entities.behaviors:
        post = beh.postconditions[0][:60] if beh.postconditions else ""
        lines.append(
            f"  {beh.id}: {beh.name} [{beh.status.value}] "
            f"actor={beh.actor} freq={beh.frequency} pri={beh.priority.value}"
        )
        if post:
            lines.append(f"    acceptance: {post}")
    return "\n".join(lines)


def _format_behaviors_compact(model: ArchitectureModel) -> str:
    if not model.entities.behaviors:
        return ""
    lines = ["\n## Behaviors (30 UCs)"]
    for beh in model.entities.behaviors:
        tag = beh.tags[0] if beh.tags else "?"
        lines.append(f"  {beh.id}: {beh.name} [{beh.status.value}] {tag} pri={beh.priority.value}")
    return "\n".join(lines)


def _format_interfaces(model: ArchitectureModel) -> str:
    if not model.entities.interfaces:
        return ""
    lines = ["\n## Interfaces"]
    for iface in model.entities.interfaces:
        lines.append(
            f"  {iface.id}: {iface.type.value} | {iface.provider} -> {iface.consumer} "
            f"via {iface.protocol} [{iface.status.value}]"
        )
    return "\n".join(lines)


def _format_interfaces_compact(model: ArchitectureModel) -> str:
    if not model.entities.interfaces:
        return ""
    lines = [f"\n## Interfaces ({len(model.entities.interfaces)})"]
    for iface in model.entities.interfaces:
        lines.append(f"  {iface.id}: {iface.provider} -> {iface.consumer} ({iface.type.value})")
    return "\n".join(lines)


def _format_layers(model: ArchitectureModel) -> str:
    if not model.entities.layers:
        return ""
    lines = ["\n## Layers"]
    for layer in model.entities.layers:
        comp_count = sum(1 for c in model.entities.components if c.layer == layer.id)
        lines.append(f"  {layer.id}: {layer.name} (order={layer.order}, {comp_count} components)")
        if layer.directories:
            lines.append(f"    dirs: {', '.join(layer.directories)}")
    return "\n".join(lines)


def _format_layers_compact(model: ArchitectureModel) -> str:
    if not model.entities.layers:
        return ""
    lines = [f"\n## Layers ({len(model.entities.layers)})"]
    for layer in model.entities.layers:
        lines.append(f"  {layer.id}: {layer.name}")
    return "\n".join(lines)


def _format_components(model: ArchitectureModel) -> str:
    if not model.entities.components:
        return ""
    lines = [f"\n## Components ({len(model.entities.components)})"]
    for comp in model.entities.components:
        files = ", ".join(comp.files[:2]) if comp.files else ""
        lines.append(f"  {comp.id}: {comp.name} (layer={comp.layer}, {comp.f_block}) [{files}]")
    return "\n".join(lines)


def _format_constraints(model: ArchitectureModel) -> str:
    if not model.entities.constraints:
        return ""
    lines = [f"\n## Constraints ({len(model.entities.constraints)})"]
    for con in model.entities.constraints:
        lines.append(f"  {con.id}: {con.name} ({con.type.value}) threshold={con.threshold}")
    return "\n".join(lines)


def _format_relationships_compact(model: ArchitectureModel) -> str:
    if not model.relationships:
        return ""
    # Group by type
    by_type: dict[str, list[Relationship]] = {}
    for rel in model.relationships:
        by_type.setdefault(rel.type.value, []).append(rel)

    lines = [f"\n## Relationships ({len(model.relationships)})"]
    for rtype, rels in by_type.items():
        lines.append(f"  {rtype} ({len(rels)}):")
        for rel in rels[:10]:  # Limit per type
            lines.append(f"    {rel.from_id} -> {rel.to_id}")
        if len(rels) > 10:
            lines.append(f"    ... +{len(rels) - 10} more")
    return "\n".join(lines)


def _find_entity_name(model: ArchitectureModel, entity_id: str) -> str:
    """Find the human-readable name for an entity ID."""
    for lst in [
        model.entities.actors,
        model.entities.capabilities,
        model.entities.behaviors,
        model.entities.interfaces,
        model.entities.constraints,
        model.entities.layers,
        model.entities.components,
    ]:
        for e in lst:
            if e.id == entity_id:
                return e.name
    return entity_id
