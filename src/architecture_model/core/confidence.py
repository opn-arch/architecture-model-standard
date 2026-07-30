"""Confidence scoring engine for architecture entities.

Computes a 0.0-1.0 confidence score per entity based on weighted field
completeness. Higher confidence = higher likelihood we could regenerate
the entity's implementation from the model alone.
"""
from __future__ import annotations

from architecture_model.core.types import (
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    Interface,
)


def compute_component_confidence(comp: Component) -> float:
    """Compute confidence for a Component. Returns 0.0-1.0."""
    score = 0.0
    if comp.contract:
        score += 0.25
    if comp.signatures:
        has_returns = any(s.returns for s in comp.signatures)
        score += 0.20 if has_returns else 0.15
    if comp.pattern:
        score += 0.15
    if comp.test_contracts:
        score += 0.15
    if comp.symbols:
        has_members = any(s.members for s in comp.symbols)
        score += 0.10 if has_members else 0.07
    if comp.constants:
        score += 0.05
    if comp.responsibilities:
        score += 0.05
    if comp.files:
        score += 0.05
    return min(score, 1.0)


def compute_behavior_confidence(behavior: Behavior) -> float:
    """Compute confidence for a Behavior. Returns 0.0-1.0."""
    score = 0.0
    if behavior.steps:
        score += 0.30 if len(behavior.steps) >= 2 else 0.15
    if behavior.preconditions:
        score += 0.15
    if behavior.postconditions:
        score += 0.15
    if behavior.trigger:
        score += 0.15
    if behavior.states:
        score += 0.15
    if behavior.actor:
        score += 0.10
    return min(score, 1.0)


def compute_capability_confidence(capability: Capability, *, realized: bool = False) -> float:
    """Compute confidence for a Capability. Returns 0.0-1.0."""
    score = 0.0
    if capability.requirements:
        score += 0.40
    if capability.description:
        score += 0.30
    if realized:
        score += 0.30
    return min(score, 1.0)


def compute_interface_confidence(interface: Interface) -> float:
    """Compute confidence for an Interface. Returns 0.0-1.0."""
    score = 0.0
    if interface.protocol:
        score += 0.20
    if interface.endpoints:
        score += 0.25
    if interface.schema:
        score += 0.20
    if interface.provider and interface.consumer:
        score += 0.20
    elif interface.provider or interface.consumer:
        score += 0.10
    if interface.data_format:
        score += 0.15
    return min(score, 1.0)


from architecture_model.monitoring import monitored


@monitored(
    module="core.confidence",
    outputs=lambda r: {"total_entities": len(r.entities.components) + len(r.entities.behaviors) + len(r.entities.capabilities) + len(r.entities.interfaces)},
)
def compute_model_confidence(model: ArchitectureModel) -> ArchitectureModel:
    """Compute and set confidence on all entities in the model."""
    realized_caps = set()
    for rel in model.relationships:
        if rel.type == "realizes" or (hasattr(rel.type, 'value') and rel.type.value == "realizes"):
            realized_caps.add(rel.to_id)

    for comp in model.entities.components:
        if comp.confidence == 0.0:
            comp.confidence = compute_component_confidence(comp)
    for beh in model.entities.behaviors:
        if beh.confidence == 0.0:
            beh.confidence = compute_behavior_confidence(beh)
    for cap in model.entities.capabilities:
        if cap.confidence == 0.0:
            cap.confidence = compute_capability_confidence(cap, realized=cap.id in realized_caps)
    for iface in model.entities.interfaces:
        if iface.confidence == 0.0:
            iface.confidence = compute_interface_confidence(iface)

    return model


def aggregate_block_confidence(model: ArchitectureModel) -> dict[str, dict]:
    """Aggregate confidence scores per F-block."""
    from collections import defaultdict
    blocks: dict[str, list[float]] = defaultdict(list)

    for comp in model.entities.components:
        block = comp.f_block or "unassigned"
        blocks[block].append(comp.confidence)

    for beh in model.entities.behaviors:
        blocks["behaviors"].append(beh.confidence)

    result = {}
    for block_id, scores in blocks.items():
        if not scores:
            continue
        result[block_id] = {
            "avg_confidence": sum(scores) / len(scores),
            "min_confidence": min(scores),
            "max_confidence": max(scores),
            "entity_count": len(scores),
        }
    return result


def model_confidence_summary(model: ArchitectureModel) -> dict:
    """Generate overall confidence summary for the model."""
    all_scores = []

    for comp in model.entities.components:
        all_scores.append((comp.id, comp.name, comp.confidence))
    for beh in model.entities.behaviors:
        all_scores.append((beh.id, beh.name, beh.confidence))
    for cap in model.entities.capabilities:
        all_scores.append((cap.id, cap.name, cap.confidence))
    for iface in model.entities.interfaces:
        all_scores.append((iface.id, iface.name, iface.confidence))

    if not all_scores:
        return {"overall": 0.0, "high_confidence": 0, "low_confidence": 0, "total_entities": 0, "gaps": []}

    scores_only = [s[2] for s in all_scores]
    high = sum(1 for s in scores_only if s >= 0.8)
    low = sum(1 for s in scores_only if s < 0.3)

    sorted_entities = sorted(all_scores, key=lambda x: x[2])
    gaps = [{"id": e[0], "name": e[1], "confidence": e[2]} for e in sorted_entities[:5]]

    return {
        "overall": sum(scores_only) / len(scores_only),
        "high_confidence": high,
        "low_confidence": low,
        "total_entities": len(all_scores),
        "gaps": gaps,
    }


def compute_function_confidence(func_info) -> float:
    """Compute confidence for a function from manifest FunctionInfo.

    Factors:
    - Has typed signature (params with types, return type): 30%
    - Has docstring: 25%
    - Has call graph (calls list): 20%
    - Has raises info: 15%
    - Has parameters at all: 10%
    """
    score = 0.0
    sig = func_info.signature or ""

    # Typed signature (30%)
    has_return_type = "->" in sig
    has_typed_params = ":" in sig.split("->")[0] if sig else False
    if has_return_type and has_typed_params:
        score += 0.30
    elif has_return_type or has_typed_params:
        score += 0.15

    # Docstring (25%)
    if func_info.docstring:
        score += 0.25

    # Call graph (20%)
    if func_info.calls:
        score += 0.20 if len(func_info.calls) >= 2 else 0.10

    # Raises (15%)
    if func_info.raises:
        score += 0.15

    # Has parameters (10%)
    inner = sig.split("(")[1].split(")")[0].strip() if "(" in sig else ""
    if inner and inner != "self":
        score += 0.10

    return min(score, 1.0)
