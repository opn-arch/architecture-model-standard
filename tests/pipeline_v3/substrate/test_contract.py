"""Tests for the contract decorators (silent_skip)."""

from __future__ import annotations

from architecture_model.pipeline_v3.substrate import (
    StageContext,
    silent_skip,
    wrap_function,
)


def test_silent_skip_returns_skipped_when_predicate_true() -> None:
    stage = wrap_function("double", lambda x: x * 2)
    # Rebind the stage's run through the decorator.
    original_run = stage.run
    wrapped = silent_skip(lambda x: x is None, reason="input was None")(original_run)

    result = wrapped(None, StageContext())
    assert result.skipped is True
    assert result.value is None
    assert "input was None" in result.notes


def test_silent_skip_invokes_wrapped_when_predicate_false() -> None:
    stage = wrap_function("double", lambda x: x * 2)
    wrapped = silent_skip(lambda x: x is None)(stage.run)

    result = wrapped(5, StageContext())
    assert result.skipped is False
    assert result.value == 10


def test_silent_skip_preserves_reason_in_notes() -> None:
    stage = wrap_function("noop", lambda x: x)
    wrapped = silent_skip(lambda x: True, reason="always")(stage.run)
    result = wrapped(42, StageContext())
    assert result.notes == ("always",)
