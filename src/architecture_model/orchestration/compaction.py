"""Model compaction – offload leaf behaviors to per-component groups."""
from __future__ import annotations

from dataclasses import replace as dc_replace

from architecture_model.core.types import (
    ArchitectureModel,
    Behavior,
    Entities,
    Relationship,
)


def _rel_type_str(rel_type) -> str:
    return rel_type.value if hasattr(rel_type, "value") else str(rel_type)


def compact_for_storage(
    model: ArchitectureModel,
) -> tuple[ArchitectureModel, dict[str, list[Behavior]]]:
    """Compact a model by offloading leaf behaviors to per-component groups."""
    # 1. Separate use cases from leaf behaviors
    use_cases = [b for b in model.entities.behaviors if b.id.startswith("UC-")]
    leaf_behaviors = [b for b in model.entities.behaviors if not b.id.startswith("UC-")]
    leaf_ids = {b.id for b in leaf_behaviors}

    # 2. Build beh_to_comp mapping from realizes relationships
    beh_to_comp: dict[str, str] = {}
    for r in model.relationships:
        if _rel_type_str(r.type) == "realizes" and r.to_id in leaf_ids:
            beh_to_comp[r.to_id] = r.from_id

    # 3. Group leaf behaviors by component ID
    comp_groups: dict[str, list[Behavior]] = {}
    for b in leaf_behaviors:
        comp_id = beh_to_comp.get(b.id)
        if comp_id:
            comp_groups.setdefault(comp_id, []).append(b)

    # Look up component names
    comp_names = {c.id: c.name for c in model.entities.components}

    # 4. Create summary behaviors
    summaries: list[Behavior] = []
    for comp_id, behs in comp_groups.items():
        comp_name = comp_names.get(comp_id, comp_id)
        top_5_names = [b.name for b in behs[:5]]
        summaries.append(
            Behavior(
                id=f"BEH-SUMMARY-{comp_id}",
                name=f"{comp_name} Operations",
                status="ACTIVE",
                steps=[b.name for b in behs[:10]],
                description=f"Key operations: {', '.join(top_5_names)}",
            )
        )

    # 5. Keep use cases + summaries
    kept_behaviors = use_cases + summaries

    # 6. Filter relationships – remove realizes edges to offloaded leaf IDs
    offloaded_ids = {b.id for behs in comp_groups.values() for b in behs}
    kept_rels = [
        r
        for r in model.relationships
        if not (_rel_type_str(r.type) == "realizes" and r.to_id in offloaded_ids)
    ]

    compact = dc_replace(
        model,
        entities=dc_replace(model.entities, behaviors=kept_behaviors),
        relationships=kept_rels,
    )
    return compact, comp_groups
