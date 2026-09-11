"""Slice anchor for viewer panels — deterministic (model, files, artifacts) scope per view.

See docs/plans/2026-09-10-track4-slice-anchor-design.md for full design.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from architecture_model.core.types import ArchitectureModel, RelationType


VIEW_TO_ARTIFACT: dict[str, str] = {
    "conops": "conops",
    "functional": "functional-architecture",
    "logical": "logical-architecture",
    "use_cases": "use-cases",
}

ARTIFACT_TO_DOC: dict[str, str] = {
    "conops": ".architecture-models/docs/se/conops.md",
    "functional-architecture": ".architecture-models/docs/se/functional-analysis.md",
    "logical-architecture": ".architecture-models/docs/se/logical-architecture.md",
    "use-cases": ".architecture-models/docs/se/use-cases.md",
}


@dataclass(frozen=True)
class SliceAnchor:
    view_name: str
    artifact_name: str
    model: ArchitectureModel
    files: tuple[str, ...]
    artifacts: tuple[str, ...]


_CLOSURE_TYPES = frozenset({
    RelationType.REALIZES,
    RelationType.CONTAINS,
    RelationType.DEPENDS_ON,
})


def _all_entities(model: ArchitectureModel):
    """Yield (kind, entity) for every entity in the model."""
    for kind in (
        "actors", "capabilities", "behaviors", "interfaces",
        "constraints", "layers", "components", "systems",
    ):
        for entity in getattr(model.entities, kind, []) or []:
            yield kind, entity


def apply_one_hop_closure(full: ArchitectureModel, sliced: ArchitectureModel) -> ArchitectureModel:
    """Expand sliced with one hop of realizes/contains/depends-on neighbors from full.

    One pass, no transitive expansion. Deterministic by sorted iteration.
    """
    slice_ids: set[str] = set()
    for _, entity in _all_entities(sliced):
        slice_ids.add(entity.id)

    id_to_kind_entity: dict[str, tuple[str, object]] = {}
    for kind, entity in _all_entities(full):
        id_to_kind_entity[entity.id] = (kind, entity)

    to_add: set[str] = set()
    rels_to_add: list = []
    sorted_rels = sorted(
        (r for r in full.relationships if r.type in _CLOSURE_TYPES),
        key=lambda r: (r.type.value, r.from_id, r.to_id),
    )
    for rel in sorted_rels:
        f, t = rel.from_id, rel.to_id
        if f in slice_ids and t not in slice_ids and t in id_to_kind_entity:
            to_add.add(t)
            rels_to_add.append(rel)
        elif t in slice_ids and f not in slice_ids and f in id_to_kind_entity:
            to_add.add(f)
            rels_to_add.append(rel)

    result = deepcopy(sliced)
    for eid in sorted(to_add):
        kind, entity = id_to_kind_entity[eid]
        bucket = getattr(result.entities, kind)
        bucket.append(deepcopy(entity))
    for rel in rels_to_add:
        result.relationships.append(deepcopy(rel))
    return result
