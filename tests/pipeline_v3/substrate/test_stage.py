"""Tests for the Stage protocol and wrap_function adapter."""

from __future__ import annotations

from architecture_model.pipeline_v3.substrate import (
    Stage,
    StageContext,
    StageResult,
    wrap_function,
)


def test_wrap_function_produces_stage() -> None:
    stage = wrap_function("double", lambda x: x * 2)
    assert isinstance(stage, Stage)
    assert stage.name == "double"


def test_wrapped_stage_run_returns_result() -> None:
    stage = wrap_function("double", lambda x: x * 2)
    result = stage.run(3, StageContext())
    assert isinstance(result, StageResult)
    assert result.name == "double"
    assert result.value == 6
    assert result.skipped is False


def test_stage_context_is_frozen() -> None:
    ctx = StageContext(run_id="r1", metadata={"k": "v"})
    # frozen dataclass: assignment must fail
    import dataclasses

    assert dataclasses.is_dataclass(ctx)
    try:
        ctx.run_id = "r2"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("StageContext should be frozen")


def test_stage_determinism_same_input_same_output() -> None:
    stage = wrap_function("sum", lambda xs: sum(xs))
    r1 = stage.run([1, 2, 3], StageContext())
    r2 = stage.run([1, 2, 3], StageContext())
    assert r1.value == r2.value == 6
