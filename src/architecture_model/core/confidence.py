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


def compute_model_confidence(model: ArchitectureModel) -> ArchitectureModel:
    """Compute and set confidence on all entities in the model."""
    realized_caps = set()
    for rel in model.relationships:
        if rel.type == "realizes" or (hasattr(rel.type, 'value') and rel.type.value == "realizes"):
            realized_caps.add(rel.to_id)

    for comp in model.entities.components:
        comp.confidence = compute_component_confidence(comp)
    for beh in model.entities.behaviors:
        beh.confidence = compute_behavior_confidence(beh)
    for cap in model.entities.capabilities:
        cap.confidence = compute_capability_confidence(cap, realized=cap.id in realized_caps)
    for iface in model.entities.interfaces:
        iface.confidence = compute_interface_confidence(iface)

    return model
