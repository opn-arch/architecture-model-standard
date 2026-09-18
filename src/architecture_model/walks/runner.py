"""architecture_model.walks.runner — Assemble and run a WalkSpec.

Composes the six stages into a Pipeline over the substrate and runs it.
Returns the emit stage's Card list.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.substrate import (
    Pipeline,
    PipelineResult,
    StageContext,
)
from architecture_model.walks.spec.loader import WalkSpec
from architecture_model.walks.stages import (
    classify_stage,
    emit_stage,
    evidence_stage,
    rollup_stage,
    select_stage,
    traverse_stage,
)

__all__ = ["run_walk", "build_walk_pipeline"]


def build_walk_pipeline() -> Pipeline:
    """Assemble the six-stage walk pipeline on the substrate."""
    return Pipeline(
        [
            select_stage(),
            traverse_stage(),
            classify_stage(),
            rollup_stage(),
            evidence_stage(),
            emit_stage(),
        ]
    )


def run_walk(
    spec: WalkSpec,
    model: dict[str, Any],
    *,
    prior_walk_output: list[dict] | None = None,
) -> dict[str, Any]:
    """Run one WalkSpec against a model. Returns the emit payload.

    Args:
        spec: the parsed WalkSpec.
        model: the architecture model as a dict (v3 YAML loaded).
        prior_walk_output: cards from a walk this one composes with
            (scope.from_walk).

    Returns:
        A dict ``{walk_id, audits, cards}`` where ``cards`` is a
        deterministically ordered list of Card dicts.
    """
    pipeline = build_walk_pipeline()
    initial = {
        "model": model,
        "spec": spec,
        "prior_walk_output": prior_walk_output or [],
    }
    result: PipelineResult = pipeline.run(
        initial, StageContext(run_id=spec.id)
    )
    final = result.final
    assert final is not None and final.value is not None, "walk produced no output"
    return final.value
