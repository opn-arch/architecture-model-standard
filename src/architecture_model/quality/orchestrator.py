"""Quality orchestrator — chains code review → model feedback → diff → dashboard."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel
    from architecture_model.core.differ import ModelDiff
    from architecture_model.quality.dashboard import QualityReport
    from architecture_model.quality.model_feedback import ModelFeedback


@dataclass
class QualityLoopResult:
    """Result of a full quality orchestration loop."""
    original_model: ArchitectureModel
    updated_model: ArchitectureModel
    feedbacks: list[ModelFeedback]
    diff: ModelDiff | None
    report: QualityReport
    files_analyzed: int = 0
    changes_applied: int = 0


def quality_loop(
    model: "ArchitectureModel",
    *,
    source_files: list[Path | str] | None = None,
    llm_callback=None,
) -> QualityLoopResult:
    """Run the full quality orchestration loop.

    Flow: analyze sources → derive model feedback → apply to model copy
          → diff old vs new → generate dashboard report

    Args:
        model: The architecture model (not mutated).
        source_files: Explicit source files. If None, discovered from model components.
        llm_callback: Optional LLM callback for code_improver (unused if None).

    Returns:
        QualityLoopResult with updated model, feedbacks, diff, and report.
    """
    from architecture_model.quality.code_review import analyze_source, CodeAnalysis
    from architecture_model.quality.model_feedback import code_to_model_feedback, apply_feedback, ModelFeedback
    from architecture_model.core.differ import diff_models
    from architecture_model.quality.dashboard import quality_report

    # 1. Discover source files from model components if not provided
    if source_files is None:
        source_files = []
        for comp in model.entities.components:
            for f in (comp.files or []):
                p = Path(f)
                if p.suffix == ".py" and p.exists():
                    source_files.append(p)

    # 2. Analyze source files, grouped by component
    comp_analyses: dict[str, list[CodeAnalysis]] = {}
    files_analyzed = 0
    for comp in model.entities.components:
        analyses = []
        for f in (comp.files or []):
            p = Path(f)
            if p.suffix == ".py" and p.exists():
                try:
                    analysis = analyze_source(p.read_text(), filename=str(p))
                    analyses.append(analysis)
                    files_analyzed += 1
                except Exception:
                    pass
        if analyses:
            comp_analyses[comp.id] = analyses

    # 3. Derive model feedback per component
    feedbacks: list[ModelFeedback] = []
    for comp in model.entities.components:
        if comp.id in comp_analyses:
            fb = code_to_model_feedback(comp, comp_analyses[comp.id])
            feedbacks.append(fb)

    # 4. Apply feedback to a deep copy of the model
    updated = copy.deepcopy(model)
    changes_applied = 0
    for i, comp in enumerate(updated.entities.components):
        for fb in feedbacks:
            if fb.component_id == comp.id:
                before = (comp.failure_modes, comp.trade_offs, comp.goals)
                updated.entities.components[i] = apply_feedback(comp, fb)
                after = (
                    updated.entities.components[i].failure_modes,
                    updated.entities.components[i].trade_offs,
                    updated.entities.components[i].goals,
                )
                if before != after:
                    changes_applied += 1

    # 5. Diff original vs updated
    diff = diff_models(model, updated)

    # 6. Generate quality report on updated model
    report = quality_report(updated)

    return QualityLoopResult(
        original_model=model,
        updated_model=updated,
        feedbacks=feedbacks,
        diff=diff,
        report=report,
        files_analyzed=files_analyzed,
        changes_applied=changes_applied,
    )
