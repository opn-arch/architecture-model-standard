"""Correction consumption helpers for pipeline stages.

Loads structured Correction objects from the LearningStore and filters
them by stage/module name for post-processing stage outputs.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .learning import Correction, LearningStore
    from .protocol import PipelineContext


def get_resolutions_for_stage(ctx: PipelineContext, stage_name: str) -> list:
    """Return structured invocation resolutions intended for a stage."""
    categories = {
        "infer": {"complex_behavior"},
        "allocate": {"ambiguous_module"},
    }.get(stage_name, set())
    resolutions = []
    for evidence in ctx.prior_corrections:
        if evidence.location not in categories:
            continue
        if evidence.metadata.get("for_stage", stage_name) != stage_name:
            continue
        if not evidence.metadata.get("files_sent") and evidence.metadata.get("resolution_id"):
            resolution_id = evidence.metadata["resolution_id"]
            call = next(
                (item for item in ctx.llm_calls if item.resolution_id == resolution_id),
                None,
            )
            if call:
                evidence.metadata["files_sent"] = list(call.files_sent)
        resolutions.append(evidence)
    return resolutions


def get_corrections_for_stage(
    ctx: PipelineContext, stage_name: str
) -> list[Correction]:
    """Return corrections applicable to *stage_name* from the LearningStore.

    Falls back to an empty list when no store is attached.
    """
    if ctx.learning_store is None:
        return []
    return ctx.learning_store.get_corrections(module=stage_name)
