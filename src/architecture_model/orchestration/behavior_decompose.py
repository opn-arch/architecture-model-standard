"""Decompose behaviors with raw AST steps into structured Step objects."""
from __future__ import annotations

from dataclasses import replace as dc_replace

from architecture_model.core.types import (
    ArchitectureModel, Behavior, Component, Step
)


def decompose_behavior(
    behavior: Behavior,
    model: ArchitectureModel,
    manifest=None,
) -> Behavior:
    """Promote behavior's raw steps to structured Steps.
    
    For each raw step (a function/method name):
    1. Find which component contains a function with that name
    2. Use the function name as the action (titlecase, underscores to spaces)
    3. Set component_ref to the owning component's ID
    
    If manifest is provided, also look up function signatures for richer descriptions.
    
    Returns a NEW Behavior with structured_steps populated.
    """
    if not behavior.steps:
        return behavior
    
    # Build function->component index from model
    func_to_comp: dict[str, str] = {}
    components = model.entities.components or []
    
    # If manifest provided, use it to find function locations
    if manifest:
        # Build file->component map
        file_to_comp: dict[str, str] = {}
        for comp in components:
            for f in (comp.files or []):
                file_to_comp[f] = comp.id
        
        # Build function->file map from manifest modules
        for mod in manifest.modules:
            comp_id = file_to_comp.get(mod.file, "")
            for func in mod.functions:
                func_to_comp[func.name] = comp_id
    
    # Also check component.functions (if populated)
    for comp in components:
        if hasattr(comp, 'functions'):
            for func in (comp.functions or []):
                if hasattr(func, 'name'):
                    func_to_comp[func.name] = comp.id
    
    # Build structured steps
    structured = []
    for i, step_name in enumerate(behavior.steps, 1):
        action = step_name.replace("_", " ").replace("-", " ").title()
        comp_ref = func_to_comp.get(step_name, "")
        structured.append(Step(
            order=i,
            action=action,
            component_ref=comp_ref,
            actor="system",
        ))
    
    return dc_replace(behavior, structured_steps=structured)


def decompose_all_behaviors(
    model: ArchitectureModel,
    manifest=None,
) -> ArchitectureModel:
    """Decompose all behaviors in a model."""
    behaviors = model.entities.behaviors or []
    if not behaviors:
        return model
    
    new_behaviors = [decompose_behavior(b, model, manifest) for b in behaviors]
    
    new_entities = dc_replace(model.entities, behaviors=new_behaviors)
    return dc_replace(model, entities=new_entities)
