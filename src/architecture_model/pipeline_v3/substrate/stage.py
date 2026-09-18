"""pipeline_v3.substrate.stage — Stage protocol + result types.

A Stage is a pure function ``run(input, ctx) -> output``. Inputs and
outputs are stage-specific; the substrate stays type-neutral. Stages
compose into Pipelines that thread outputs through.

`wrap_function` lifts an existing plain function (like the pipeline_v3
stage functions ``scan_repo``, ``cluster_modules``, etc.) into a Stage
with a declared name and optional input adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Protocol, TypeVar, runtime_checkable

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")

__all__ = [
    "Stage",
    "StageContext",
    "StageResult",
    "wrap_function",
]


@dataclass(frozen=True)
class StageContext:
    """Immutable context threaded through a Pipeline run.

    - ``run_id``: opaque identifier for cache scoping.
    - ``metadata``: free-form dict for stage-specific overrides
      (predicates, flags, thresholds). Never mutated.
    """

    run_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StageResult(Generic[TOut]):
    """Result envelope for a single stage.

    ``skipped=True`` indicates silent-skip (L7/L10). Value is None when
    skipped; downstream stages must tolerate ``None``.
    """

    name: str
    value: TOut | None
    skipped: bool = False
    notes: tuple[str, ...] = ()


@runtime_checkable
class Stage(Protocol[TIn, TOut]):
    """Pure staged-pipeline unit.

    Contract:
      - ``name`` is stable, unique within a Pipeline.
      - ``run(input, ctx)`` is deterministic given identical inputs.
      - ``run`` returns a ``StageResult``.
      - No side effects beyond returning the result.
    """

    name: str

    def run(self, input: TIn, ctx: StageContext) -> StageResult[TOut]: ...


@dataclass(frozen=True)
class _FunctionStage(Generic[TIn, TOut]):
    """Concrete Stage adapter wrapping a plain callable."""

    name: str
    fn: Callable[[TIn], TOut]

    def run(self, input: TIn, ctx: StageContext) -> StageResult[TOut]:
        value = self.fn(input)
        return StageResult(name=self.name, value=value)


def wrap_function(name: str, fn: Callable[[TIn], TOut]) -> Stage[TIn, TOut]:
    """Lift a plain callable into a Stage with the given name.

    The wrapped function is invoked with a single input argument. Use
    ``functools.partial`` or a closure to bind additional parameters
    (e.g., cluster_depth for cluster_modules).
    """
    return _FunctionStage(name=name, fn=fn)
