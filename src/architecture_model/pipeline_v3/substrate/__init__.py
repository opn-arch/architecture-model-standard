"""pipeline_v3.substrate — Shared staged-pipeline substrate.

Provides the generic Stage / Pipeline / Cache / Contract primitives used
by both extraction (pipeline_v3) and walks (architecture_model.walks).

Design intent: minimal, composable, byte-deterministic. Each Stage is a
pure function wrapped in a Protocol; a Pipeline threads outputs through
stages left-to-right; the Cache is content-addressed; Contracts are
decorators that enforce silent-skip, purity, and determinism.

Ships in support of L18–L21 (walk-as-capability, attribute-driven
rollup, verdict taxonomy, attribute categories + lifecycle).
"""

from architecture_model.pipeline_v3.substrate.cache import ContentCache
from architecture_model.pipeline_v3.substrate.contract import (
    ContractViolation,
    silent_skip,
)
from architecture_model.pipeline_v3.substrate.pipeline import (
    Pipeline,
    PipelineResult,
)
from architecture_model.pipeline_v3.substrate.stage import (
    Stage,
    StageContext,
    StageResult,
    wrap_function,
)

__all__ = [
    "ContentCache",
    "ContractViolation",
    "Pipeline",
    "PipelineResult",
    "Stage",
    "StageContext",
    "StageResult",
    "silent_skip",
    "wrap_function",
]
