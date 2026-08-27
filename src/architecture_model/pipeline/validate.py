"""Validate pipeline stage — checks structural correctness of extracted model.

Runs checks: orphan components, unrealized capabilities, missing relationships,
file coverage, naming conventions.
"""

from __future__ import annotations

import time

from .allocate_types import AllocationResult
from .infer_types import InferenceResult
from .protocol import (
    Diagnostic,
    PipelineContext,
    QualityMetrics,
    StageResult,
    Uncertainty,
)
from .relate_types import RelateResult
from .validate_types import ValidateResult, ValidationIssue


class ValidateStage:
    """Validates the extracted architecture model for structural correctness."""

    name: str = "validate"
    requires: list[str] = ["infer", "allocate", "relate", "specify", "contract"]

    def run(self, ctx: PipelineContext) -> StageResult[ValidateResult]:
        start = time.time()
        diagnostics: list[Diagnostic] = []
        uncertainties: list[Uncertainty] = []
        issues: list[ValidationIssue] = []

        infer_result = ctx.get("infer")
        allocate_result = ctx.get("allocate")
        relate_result = ctx.get("relate")
        if not all([infer_result, allocate_result, relate_result]):
            raise RuntimeError("validate requires infer, allocate, relate")

        inference: InferenceResult = infer_result.output
        allocation: AllocationResult = allocate_result.output
        relationships: RelateResult = relate_result.output

        # Check 1: Every capability has a realizing component
        realized_caps = {r.to_id for r in relationships.relationships if r.rel_type == "realizes"}
        for cap in inference.capabilities:
            if cap.id not in realized_caps:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        message=f"Capability {cap.name} ({cap.id}) has no realizing component",
                        entity_id=cap.id,
                        rule="capability_realization",
                    )
                )

        # Check 2: No orphan components (components with no relationships)
        related_comps = set()
        for r in relationships.relationships:
            related_comps.add(r.from_id)
            related_comps.add(r.to_id)
        for comp in allocation.components:
            if comp.id not in related_comps:
                issues.append(
                    ValidationIssue(
                        severity="info",
                        message=f"Component {comp.name} ({comp.id}) has no relationships",
                        entity_id=comp.id,
                        rule="orphan_detection",
                    )
                )

        # Check 3: File coverage
        if allocation.file_coverage < 95.0:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=f"File coverage is {allocation.file_coverage:.1f}% (target: 95%)",
                    rule="file_coverage",
                )
            )

        # Check 4: Boundary coherence
        if allocation.boundary_coherence < 50.0:
            issues.append(
                ValidationIssue(
                    severity="info",
                    message=f"Boundary coherence is {allocation.boundary_coherence:.1f}% (target: 50%)",
                    rule="boundary_coherence",
                )
            )

        # Check 5: Confidence-driven re-extraction candidates
        # Flag components with low confidence for LLM enrichment
        for comp in allocation.components:
            confidence = getattr(comp, "confidence", 1.0)
            if confidence < 0.5:
                uncertainties.append(
                    Uncertainty(
                        category="low_confidence_component",
                        description=(
                            f"Component '{comp.name}' ({comp.id}) has confidence {confidence:.2f}. "
                            f"Files: {comp.files[:3]}. Consider LLM analysis to improve naming/boundaries."
                        ),
                        context={
                            "component_id": comp.id,
                            "confidence": confidence,
                            "files": comp.files[:5],
                        },
                        suggested_fallback="llm_analysis",
                        priority="enriching",
                    )
                )

        for cap in inference.capabilities:
            # Check if capability name is generic (heuristic: very short or common)
            generic_names = {"Web Routes", "Domain Logic", "CLI Commands", "Core", "Utils", "Misc"}
            if cap.name in generic_names:
                uncertainties.append(
                    Uncertainty(
                        category="generic_capability_name",
                        description=(
                            f"Capability '{cap.name}' ({cap.id}) has a generic name. "
                            f"LLM analysis could produce a more specific business-oriented name."
                        ),
                        context={"capability_id": cap.id, "current_name": cap.name},
                        suggested_fallback="llm_analysis",
                        priority="enriching",
                    )
                )

        # Score: 100 - penalties
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        score = max(0, 100 - error_count * 20 - warning_count * 5)
        is_valid = error_count == 0

        result = ValidateResult(score=score, issues=issues, is_valid=is_valid)

        # Per-component validation issue tracking
        comp_quality: dict[str, QualityMetrics] = {}
        alloc_quality = ctx.get("allocate")
        base_scores = alloc_quality.quality.component_scores if alloc_quality else {}
        issue_per_comp: dict[str, list[str]] = {}
        for issue in issues:
            eid = issue.entity_id or ""
            if eid.startswith("COMP-"):
                issue_per_comp.setdefault(eid, []).append(issue.severity)
        for comp in allocation.components:
            base = base_scores.get(comp.id)
            sub = dict(base.sub_scores) if base else {}
            comp_issues = issue_per_comp.get(comp.id, [])
            sub["issue_count"] = float(len(comp_issues))
            sub["error_count"] = float(comp_issues.count("error"))
            sub["warning_count"] = float(comp_issues.count("warning"))
            comp_score = base.score if base else 50.0
            # Penalize: -20 per error, -5 per warning
            comp_score = max(0, comp_score - comp_issues.count("error") * 20 - comp_issues.count("warning") * 5)
            comp_quality[comp.id] = QualityMetrics(
                score=comp_score,
                sub_scores=sub,
                component_scores=base.component_scores if base else {},
            )

        quality = QualityMetrics(
            score=score,
            sub_scores={
                "error_count": float(error_count),
                "warning_count": float(warning_count),
                "info_count": float(sum(1 for i in issues if i.severity == "info")),
            },
            thresholds={"error_count": 0.0},
            component_scores=comp_quality,
        )

        duration_ms = int((time.time() - start) * 1000)

        return StageResult(
            output=result,
            quality=quality,
            diagnostics=diagnostics,
            uncertainties=uncertainties,
            input_hash="",
            duration_ms=duration_ms,
            version="1.0",
        )
