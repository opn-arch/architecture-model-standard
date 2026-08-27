"""Bidirectional feedback: code analysis findings -> architecture model updates."""
from __future__ import annotations

from dataclasses import dataclass, field
from architecture_model.core.types import Component
from architecture_model.quality.code_review import CodeAnalysis


@dataclass
class ModelFeedback:
    """Suggested model updates derived from code analysis."""
    component_id: str
    suggested_failure_modes: list[str] = field(default_factory=list)
    suggested_trade_offs: list[str] = field(default_factory=list)
    suggested_moes: list[str] = field(default_factory=list)
    suggested_goals: list[str] = field(default_factory=list)
    code_quality_score: int = 0


def code_to_model_feedback(
    component: Component,
    analyses: list[CodeAnalysis],
) -> ModelFeedback:
    """Derive architecture model field suggestions from code analysis.

    Maps code-level findings to model-level semantic fields:
    - Missing error handling -> failure_modes
    - High complexity -> trade_offs
    - Test coverage patterns -> moes
    - Function purposes -> goals
    """
    feedback = ModelFeedback(component_id=component.id)

    if not analyses:
        return feedback

    avg_score = sum(a.score for a in analyses) // len(analyses)
    feedback.code_quality_score = avg_score

    # Failure modes from error handling gaps
    for analysis in analyses:
        for fn in analysis.functions:
            # Heuristic: undocumented functions with branching logic
            if not fn.has_docstring and fn.complexity > 1:
                feedback.suggested_failure_modes.append(
                    f"Unhandled error in {fn.name}() — no documented error behavior"
                )

    # Dedup
    feedback.suggested_failure_modes = list(set(feedback.suggested_failure_modes))

    # Trade-offs from complexity
    complex_fns = [fn for a in analyses for fn in a.functions if fn.complexity > 8]
    if complex_fns:
        feedback.suggested_trade_offs.append(
            f"Complexity vs maintainability: {len(complex_fns)} functions with high cyclomatic complexity"
        )

    long_fns = [fn for a in analyses for fn in a.functions if fn.length > 50]
    if long_fns:
        feedback.suggested_trade_offs.append(
            f"Monolithic vs modular: {len(long_fns)} functions exceed 50 lines"
        )

    # MOEs from test coverage
    if getattr(component, 'test_contracts', None):
        feedback.suggested_moes.append(
            f"{len(component.test_contracts)} test contracts define expected behavior"
        )

    # Goals from function purposes (docstrings)
    documented_fns = [fn for a in analyses for fn in a.functions if fn.has_docstring]
    if documented_fns and not getattr(component, 'goals', None):
        feedback.suggested_goals = [
            f"Provide {fn.name} functionality" for fn in documented_fns[:3]
        ]

    return feedback


def apply_feedback(component: Component, feedback: ModelFeedback) -> Component:
    """Apply feedback suggestions to component (non-destructive — only adds to empty fields)."""
    import copy
    updated = copy.deepcopy(component)

    if not getattr(updated, 'failure_modes', None) and feedback.suggested_failure_modes:
        updated.failure_modes = feedback.suggested_failure_modes
    if not getattr(updated, 'trade_offs', None) and feedback.suggested_trade_offs:
        updated.trade_offs = feedback.suggested_trade_offs
    if not getattr(updated, 'moes', None) and feedback.suggested_moes:
        updated.moes = feedback.suggested_moes
    if not getattr(updated, 'goals', None) and feedback.suggested_goals:
        updated.goals = feedback.suggested_goals

    return updated
