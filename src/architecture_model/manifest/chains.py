"""Hierarchical event chain building.

Builds intra-block chains (within one F-block) and cross-block chains
(spanning multiple F-blocks). Chains trace call_order across component
boundaries to show how a request flows through the system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.manifest.types import Manifest, RecursiveManifest
    from architecture_model.manifest.grouping import ModuleGroup


@dataclass
class EventChain:
    """A sequence of calls that crosses component boundaries."""
    trigger: str  # "Component.function" that starts the chain
    steps: list[str]  # ["Comp.func", "Comp2.func2", ...]
    components_involved: list[str]  # unique component names in chain
    scope: str = "intra"  # "intra" or "cross"
    block_id: str = ""  # which block (if intra)


def build_block_chains(
    block_manifest: "Manifest",
    groups: list["ModuleGroup"],
    block_id: str,
) -> list[EventChain]:
    """Build intra-block event chains (all within one F-block).
    
    Traces call_order across component group boundaries within the block.
    Only returns chains that span 2+ components (single-component calls
    are not interesting for architecture).
    """
    # Build lookup: function_name -> component_name
    func_to_component: dict[str, str] = {}
    # Build lookup: module_path -> component_name
    path_to_component: dict[str, str] = {}
    for group in groups:
        for mod_path in group.modules:
            path_to_component[mod_path] = group.name

    for module in block_manifest.modules:
        comp_name = path_to_component.get(module.file, "unknown")
        for func in module.functions:
            func_to_component[func.name] = comp_name
            # Also register as "module_name.func_name" for attribute calls
            func_to_component[f"{module.name}.{func.name}"] = comp_name
        for cls in module.classes:
            for method in cls.method_details:
                func_to_component[f"{cls.name}.{method.name}"] = comp_name
                func_to_component[method.name] = comp_name

    chains: list[EventChain] = []

    # For each function with call_order, trace the chain
    for module in block_manifest.modules:
        comp_name = path_to_component.get(module.file, "unknown")
        for func in module.functions:
            if not func.call_order:
                continue
            chain = _trace_chain(func.name, comp_name, func.call_order, func_to_component)
            if chain and len(chain.components_involved) >= 2:
                chain.scope = "intra"
                chain.block_id = block_id
                chains.append(chain)

    return chains


def build_cross_block_chains(
    recursive_manifests: dict[str, "RecursiveManifest"],
    block_groups: dict[str, list["ModuleGroup"]],
) -> list[EventChain]:
    """Build cross-block event chains (spanning 2+ F-blocks).
    
    Uses block_dependencies to identify cross-boundary call paths.
    A cross-block chain occurs when a function's call_order references
    a function that lives in a different block.
    """
    # Build lookup: function_name -> block_id
    func_to_block: dict[str, str] = {}
    # Build lookup: module_name -> block_id (for "module.func" style calls)
    module_to_block: dict[str, str] = {}

    for block_id, rm in recursive_manifests.items():
        for module in rm.manifest.modules:
            module_to_block[module.name] = block_id
            for func in module.functions:
                func_to_block[func.name] = block_id
                func_to_block[f"{module.name}.{func.name}"] = block_id
            for cls in module.classes:
                for method in cls.method_details:
                    func_to_block[f"{cls.name}.{method.name}"] = block_id

    chains: list[EventChain] = []

    for block_id, rm in recursive_manifests.items():
        if not rm.block_dependencies:
            continue
        for module in rm.manifest.modules:
            for func in module.functions:
                if not func.call_order:
                    continue
                # Check if any call resolves to a different block
                cross_steps: list[str] = []
                blocks_hit: set[str] = {block_id}
                for call in func.call_order:
                    target_block = _resolve_call_to_block(call, func_to_block, module_to_block)
                    if target_block and target_block != block_id:
                        cross_steps.append(f"{target_block}.{call}")
                        blocks_hit.add(target_block)
                    else:
                        cross_steps.append(f"{block_id}.{call}")

                if len(blocks_hit) >= 2:
                    trigger = f"{block_id}.{module.name}.{func.name}"
                    chains.append(EventChain(
                        trigger=trigger,
                        steps=cross_steps,
                        components_involved=sorted(blocks_hit),
                        scope="cross",
                        block_id="",
                    ))

    return chains


def _trace_chain(
    func_name: str,
    source_component: str,
    call_order: list[str],
    func_to_component: dict[str, str],
) -> EventChain | None:
    """Trace a single chain from a function through its call_order."""
    steps: list[str] = [f"{source_component}.{func_name}"]
    components: set[str] = {source_component}

    for call in call_order:
        # Strip "self." prefix for component resolution
        lookup_name = call
        if call.startswith("self."):
            lookup_name = call[5:]  # remove "self."

        target_comp = func_to_component.get(lookup_name, func_to_component.get(call))
        if target_comp:
            steps.append(f"{target_comp}.{call}")
            components.add(target_comp)
        else:
            # Unknown target — still part of the chain but can't resolve component
            steps.append(f"?.{call}")

    if len(steps) <= 1:
        return None

    return EventChain(
        trigger=steps[0],
        steps=steps[1:],
        components_involved=sorted(components),
    )


def _resolve_call_to_block(
    call: str,
    func_to_block: dict[str, str],
    module_to_block: dict[str, str],
) -> str | None:
    """Resolve a call name to its owning block."""
    # Direct function match
    if call in func_to_block:
        return func_to_block[call]
    # Try "module.func" pattern — check if module part maps to a block
    if "." in call:
        module_part = call.split(".")[0]
        if module_part in module_to_block:
            return module_to_block[module_part]
    return None
