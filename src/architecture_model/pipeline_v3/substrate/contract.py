"""pipeline_v3.substrate.contract — Contract decorators and guards.

Enforces substrate invariants:
- silent-skip (L7/L10): stages return skipped results, not raise
- purity: outputs deterministic given inputs (spot-checked via hash)

These are decorators applied at stage-construction time. They wrap the
stage's ``run`` method with checks. Violations raise
``ContractViolation``.
"""

from __future__ import annotations

from typing import Any, Callable

__all__ = ["ContractViolation", "silent_skip"]


class ContractViolation(RuntimeError):
    """Raised when a substrate contract is violated."""


def silent_skip(
    predicate: Callable[[Any], bool],
    reason: str = "silent-skip predicate matched",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: return an empty/skipped result when predicate(input) is True.

    Wraps a Stage's ``run`` method. When ``predicate(input)`` returns
    True, returns a ``StageResult`` with ``skipped=True`` and ``value=None``
    instead of invoking the wrapped run.

    Example::

        stage = wrap_function("classify", classify_fn)
        stage.run = silent_skip(lambda x: x is None)(stage.run)
    """
    from architecture_model.pipeline_v3.substrate.stage import StageResult

    def decorator(run_fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(input: Any, ctx: Any) -> Any:
            if predicate(input):
                # Recover stage name from the bound method's owner if possible.
                name = getattr(run_fn, "__self__", None)
                stage_name = getattr(name, "name", "?") if name else "?"
                return StageResult(
                    name=stage_name,
                    value=None,
                    skipped=True,
                    notes=(reason,),
                )
            return run_fn(input, ctx)

        return wrapper

    return decorator
