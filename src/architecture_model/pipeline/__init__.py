"""Modular extraction pipeline for architecture models."""

from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.learning import (
    Calibration,
    Correction,
    LearningStore,
    QualityTrend,
    ResolutionOutcome,
)
from architecture_model.pipeline.protocol import (
    Claim,
    Diagnostic,
    Evidence,
    PipelineContext,
    QualityMetrics,
    SOURCE_WEIGHTS,
    Stage,
    StageResult,
    Uncertainty,
)

__all__ = [
    "Calibration",
    "Claim",
    "Correction",
    "Diagnostic",
    "Evidence",
    "LearningStore",
    "PipelineCoordinator",
    "PipelineContext",
    "QualityMetrics",
    "QualityTrend",
    "ResolutionOutcome",
    "SOURCE_WEIGHTS",
    "Stage",
    "StageResult",
    "Uncertainty",
]
