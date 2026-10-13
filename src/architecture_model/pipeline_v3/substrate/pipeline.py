"""pipeline_v3.substrate.pipeline — Pipeline runner.

Threads a list of Stages left-to-right. Each stage's output feeds the
next stage's input, wrapped in a StageResult. Silent-skip propagates:
a skipped stage passes ``None`` downstream; downstream stages decide
how to handle it (typically skip too, per L7/L10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from architecture_model.pipeline_v3.substrate.stage import (
    Stage,
    StageContext,
    StageResult,
)

__all__ = ["Pipeline", "PipelineResult"]


@dataclass(frozen=True)
class PipelineResult:
    """All stage results from a Pipeline run, keyed by stage name."""

    stages: tuple[StageResult[Any], ...]

    def by_name(self, name: str) -> StageResult[Any] | None:
        for r in self.stages:
            if r.name == name:
                return r
        return None

    @property
    def final(self) -> StageResult[Any] | None:
        return self.stages[-1] if self.stages else None


class Pipeline:
    """Ordered sequence of Stages that thread outputs through."""

    def __init__(self, stages: list[Stage[Any, Any]]) -> None:
        names = [s.name for s in stages]
        if len(names) != len(set(names)):
            raise ValueError(
                f"Pipeline stage names must be unique; got {names}"
            )
        self._stages = tuple(stages)

    @property
    def stages(self) -> tuple[Stage[Any, Any], ...]:
        return self._stages

    def run(self, initial: Any, ctx: StageContext | None = None) -> PipelineResult:
        """Run all stages left-to-right.

        Each stage receives the previous stage's ``StageResult.value``
        as input (or ``initial`` for the first stage). Skipped stages
        emit ``None`` values; downstream stages receive ``None`` and
        must handle it explicitly.
        """
        context = ctx or StageContext()
        results: list[StageResult[Any]] = []
        current: Any = initial
        for stage in self._stages:
            result = stage.run(current, context)
            results.append(result)
            current = result.value
        return PipelineResult(stages=tuple(results))
