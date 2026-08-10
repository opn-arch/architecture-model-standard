"""Regen Score pipeline stage — computes regeneration readiness from enriched model."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)


@dataclass
class RegenScoreResult:
    overall: float
    grade: str
    component_scores: dict[str, float] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    recommendation: str = ""


class RegenScoreStage:
    name: str = "regen_score"
    requires: list[str] = ["validate"]
    version: str = "1.0"

    def run(self, ctx: PipelineContext) -> StageResult[RegenScoreResult]:
        start = time.perf_counter_ns()

        from architecture_model.core.parser import load_model
        from architecture_model.core.regen_readiness import compute_regen_readiness

        model_path = ctx.repo_path / ".architecture-model.yaml"
        model = load_model(model_path)
        result = compute_regen_readiness(model)

        component_scores = {cr.name: cr.score for cr in result.components}

        diagnostics: list[Diagnostic] = []
        # Check if model is enriched (at least one component has signatures)
        components = model.entities.components if model.entities else []
        has_enrichment = any(
            getattr(comp, "signatures", None) for comp in components
        )
        if not has_enrichment:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="REGEN_NOT_ENRICHED",
                    message="Model not enriched — no components have signatures",
                )
            )

        duration_ms = int((time.perf_counter_ns() - start) / 1_000_000)

        return StageResult(
            output=RegenScoreResult(
                overall=result.overall,
                grade=result.grade,
                component_scores=component_scores,
                blockers=result.blockers,
                recommendation=result.recommendation,
            ),
            quality=QualityMetrics(
                score=result.overall,
                sub_scores={"grade": ord(result.grade[0]) if result.grade else 0},
            ),
            diagnostics=diagnostics,
            uncertainties=[],
            input_hash="",
            duration_ms=duration_ms,
            version=self.version,
        )

    def can_run(self, ctx: PipelineContext) -> bool:
        model_path = ctx.repo_path / ".architecture-model.yaml"
        return model_path.exists()

    def output_path(self, ctx: PipelineContext) -> Path:
        return ctx.output_dir / "regen_score.json"
