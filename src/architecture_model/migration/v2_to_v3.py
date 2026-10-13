"""v2 (schema 2.1) → v3 (Promise-graph) migration — T0.14 Phase 2.

Field-by-field lift of an entity's semantic content (intent, goals,
success_criteria, ...) into Promise records. This is the PoC path:
CAP-PB-PIPELINE first, then the full plan-b entity set in later phases.

The migration is deliberately **additive** during PoC — the original
2.1 semantic fields are left in place next to a new ``promises`` list.
Phase 6+ replaces the fields entirely once the pipeline_v3 orchestrator
consumes Promise records as first-class inputs.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from architecture_model.core.promise import Promise, PromiseStatus

__all__ = [
    "SEMANTIC_FIELDS",
    "migrate_entity_semantic_fields",
    "migrate_model_entity",
]

#: Semantic fields recognized by AMS 2.1 and lifted into Promises.
#: Ordered by canonical rendering order (matches BaseEntity in
#: ``core/semantic_types.py`` — intent first, then aspirational goals,
#: then criteria, then risk framing, then trade-space, then meta).
SEMANTIC_FIELDS: tuple[str, ...] = (
    "intent",
    "goals",
    "stakeholders",
    "success_criteria",
    "failure_modes",
    "trade_offs",
    "assumptions",
    "open_questions",
    "requirements",
    "verification",
    "slos",
    "moes",
    "owner",
    "maturity",
    "dependencies_rationale",
)


def _content_is_meaningful(value: Any) -> bool:
    """Skip fields that are None or empty containers.

    Empty strings and empty lists count as "not asserted" — no Promise
    is emitted. This matches the walk-instance #1 finding that missing
    fields are typed gaps to be discovered by chain-closure, not
    proactively synthesized during migration.
    """
    if value is None:
        return False
    if isinstance(value, (str, list, tuple, dict)) and len(value) == 0:
        return False
    return True


def migrate_entity_semantic_fields(
    entity: dict, *, provenance: str
) -> list[Promise]:
    """Return one Promise per semantic field asserted on ``entity``.

    Only fields present in :data:`SEMANTIC_FIELDS` **and** meaningfully
    populated (see :func:`_content_is_meaningful`) produce a Promise.
    All emitted Promises are :class:`PromiseStatus.OPEN` — chain-closure
    (Phase 3) is responsible for advancing them to ``delivered`` /
    ``verified`` / ``typed-gap``.
    """
    owner = entity["id"]
    promises: list[Promise] = []
    for field in SEMANTIC_FIELDS:
        if field not in entity:
            continue
        value = entity[field]
        if not _content_is_meaningful(value):
            continue
        promises.append(
            Promise(
                attribute=field,
                content=value,
                owner_entity=owner,
                status=PromiseStatus.OPEN,
                provenance=provenance,
            )
        )
    return promises


def migrate_model_entity(entity: dict, *, provenance: str) -> dict:
    """Return a v3-shaped entity dict: original 2.1 fields plus ``promises``.

    Additive during PoC — pruning of the source fields is deferred to
    Phase 6 when pipeline_v3 consumes the Promise records directly.
    """
    out = deepcopy(entity)
    out["promises"] = [
        p.to_dict()
        for p in migrate_entity_semantic_fields(entity, provenance=provenance)
    ]
    return out
