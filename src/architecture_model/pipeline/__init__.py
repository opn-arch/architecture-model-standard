"""Modular extraction pipeline for architecture models."""

from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.decompose import DecomposeStage
from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.emit import EmitStage
from architecture_model.pipeline.emit_types import EmitResult
from architecture_model.pipeline.learning import (
    Calibration,
    Correction,
    LearningStore,
    QualityTrend,
    ResolutionOutcome,
)
from architecture_model.pipeline.lessons import LessonEntry, generate_lessons
from architecture_model.pipeline.protocol import (
    Claim,
    Diagnostic,
    Evidence,
    LLMCallRecord,
    PipelineContext,
    QualityMetrics,
    SOURCE_WEIGHTS,
    Stage,
    StageResult,
    Uncertainty,
)
from architecture_model.pipeline.report import StageReport, generate_pipeline_report
from architecture_model.pipeline.synthesize import SynthesizeStage
from architecture_model.pipeline.synthesize_types import SoSModel, SynthesizeResult, SystemModel

__all__ = [
    "Calibration",
    "Claim",
    "Correction",
    "DecomposeResult",
    "DecomposeStage",
    "Diagnostic",
    "EmitResult",
    "EmitStage",
    "Evidence",
    "LLMCallRecord",
    "LearningStore",
    "LessonEntry",
    "PipelineCoordinator",
    "PipelineContext",
    "QualityMetrics",
    "QualityTrend",
    "ResolutionOutcome",
    "SOURCE_WEIGHTS",
    "SoSModel",
    "Stage",
    "StageReport",
    "StageResult",
    "SynthesizeResult",
    "SynthesizeStage",
    "SystemBoundary",
    "SystemModel",
    "Uncertainty",
    "generate_lessons",
    "generate_pipeline_report",
]
