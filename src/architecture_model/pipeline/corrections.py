"""Correction consumption helpers for pipeline stages.

Loads structured Correction objects from the LearningStore and filters
them by stage/module name for post-processing stage outputs.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .learning import Correction, LearningStore
    from .protocol import PipelineContext


def get_corrections_for_stage(
    ctx: PipelineContext, stage_name: str
) -> list[Correction]:
    """Return corrections applicable to *stage_name* from the LearningStore.

    Falls back to an empty list when no store is attached.
    """
    if ctx.learning_store is None:
        return []
    return ctx.learning_store.get_corrections(module=stage_name)
