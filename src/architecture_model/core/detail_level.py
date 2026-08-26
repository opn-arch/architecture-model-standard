"""Detail level scoring for architecture entities.

Levels:
  L0 (Skeleton)  - id, name, status only
  L1 (Described) - has description
  L2 (Specified) - has intent + responsibilities/steps/protocol/moes
  L3 (Enriched)  - has signatures + test_contracts
  L4 (Reviewed)  - has been LLM-reviewed (extensions['_llm_review'] present)
"""
from enum import IntEnum

from architecture_model.core.types import BaseEntity, Component, Capability, Behavior, Interface


class DetailLevel(IntEnum):
    L0_SKELETON = 0
    L1_DESCRIBED = 1
    L2_SPECIFIED = 2
    L3_ENRICHED = 3
    L4_REVIEWED = 4


def compute_detail_level(entity: BaseEntity) -> DetailLevel:
    """Compute detail level from field population. Not stored - always derived."""
    if entity.extensions.get("_llm_review"):
        return DetailLevel.L4_REVIEWED

    if isinstance(entity, Component):
        if entity.signatures and entity.test_contracts:
            return DetailLevel.L3_ENRICHED

    has_intent = bool(entity.intent)
    has_detail = False
    if isinstance(entity, Component):
        has_detail = bool(entity.responsibilities)
    elif isinstance(entity, Behavior):
        has_detail = bool(entity.steps)
    elif isinstance(entity, Interface):
        has_detail = bool(entity.protocol)
    elif isinstance(entity, Capability):
        has_detail = bool(getattr(entity, "moes", None))
    else:
        has_detail = has_intent

    if has_intent and has_detail:
        return DetailLevel.L2_SPECIFIED

    if entity.description:
        return DetailLevel.L1_DESCRIBED

    return DetailLevel.L0_SKELETON
