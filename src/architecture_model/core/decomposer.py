"""Complexity scoring and system identification for architecture decomposition.

Provides functions to compute weighted complexity scores for components and
identify F-block groups that should be promoted to System entities.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    RelationType,
)

# Aggregate complexity score above which an F-block group becomes a System
SYSTEM_THRESHOLD = 10.0


@dataclass
class SystemCandidate:
    """A proposed system identified from F-block complexity analysis."""
    f_block: str
    name: str
    component_ids: list[str]
    complexity_score: float


def compute_complexity(comp: Component, model: ArchitectureModel) -> float:
    """Weighted complexity score for determining if a component should be in a System.

    Factors:
        - Number of symbols x 2.0
        - Total members (sum of all symbol members) x 0.3
        - Number of functions x 0.5
        - Number of depends-on relationships (inbound + outbound) x 1.5
    """
    symbol_weight = len(comp.symbols) * 2.0
    member_weight = sum(len(s.members) for s in comp.symbols) * 0.3
    function_weight = len(comp.functions) * 0.5

    # Count depends-on relationships involving this component
    deps = sum(
        1 for r in model.relationships
        if r.type == RelationType.DEPENDS_ON
        and (r.from_id == comp.id or r.to_id == comp.id)
    )
    dep_weight = deps * 1.5

    return symbol_weight + member_weight + function_weight + dep_weight


def identify_systems(
    model: ArchitectureModel,
    manifest: dict,
) -> list[SystemCandidate]:
    """Identify F-block groups that should become Systems.

    Groups components by f_block, computes aggregate complexity per group,
    and returns SystemCandidates for groups exceeding SYSTEM_THRESHOLD.

    For components without an f_block field, they are skipped (remain as
    top-level components).

    Args:
        model: The architecture model with enriched components.
        manifest: Manifest dict containing functional_blocks metadata.

    Returns:
        List of SystemCandidate for groups exceeding threshold.
    """
    # Group components by f_block (skip empty f_block)
    groups: dict[str, list[Component]] = defaultdict(list)
    for comp in model.entities.components:
        if comp.f_block:
            groups[comp.f_block].append(comp)

    # Get functional_blocks metadata for naming
    fblocks_meta = manifest.get("functional_blocks", {})

    candidates: list[SystemCandidate] = []
    for fblock_id, components in groups.items():
        # Sum complexity across all components in this F-block
        total_complexity = sum(
            compute_complexity(comp, model) for comp in components
        )

        if total_complexity > SYSTEM_THRESHOLD:
            # Resolve name from manifest, fall back to f_block ID
            block_info = fblocks_meta.get(fblock_id)
            name = block_info["name"] if block_info else fblock_id

            candidates.append(SystemCandidate(
                f_block=fblock_id,
                name=name,
                component_ids=[c.id for c in components],
                complexity_score=total_complexity,
            ))

    return candidates
