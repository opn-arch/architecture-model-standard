"""Modular extraction pipeline for architecture models."""

from architecture_model.pipeline.coordinator import PipelineCoordinator
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
    "Claim",
    "PipelineCoordinator",
    "Diagnostic",
    "Evidence",
    "PipelineContext",
    "QualityMetrics",
    "SOURCE_WEIGHTS",
    "Stage",
    "StageResult",
    "Uncertainty",
]
