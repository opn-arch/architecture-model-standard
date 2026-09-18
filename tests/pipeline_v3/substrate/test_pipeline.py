"""Tests for the Pipeline runner."""

from __future__ import annotations

import pytest

from architecture_model.pipeline_v3.substrate import (
    Pipeline,
    StageContext,
    wrap_function,
)


def test_pipeline_threads_outputs_left_to_right() -> None:
    p = Pipeline(
        [
            wrap_function("plus_one", lambda x: x + 1),
            wrap_function("times_two", lambda x: x * 2),
            wrap_function("stringify", lambda x: f"={x}"),
        ]
    )
    result = p.run(3)
    assert result.final is not None
    assert result.final.value == "=8"


def test_pipeline_result_by_name_returns_stage_result() -> None:
    p = Pipeline(
        [
            wrap_function("a", lambda x: x + 1),
            wrap_function("b", lambda x: x * 2),
        ]
    )
    result = p.run(1)
    a = result.by_name("a")
    b = result.by_name("b")
    assert a is not None and a.value == 2
    assert b is not None and b.value == 4
    assert result.by_name("missing") is None


def test_pipeline_rejects_duplicate_stage_names() -> None:
    with pytest.raises(ValueError):
        Pipeline(
            [
                wrap_function("dup", lambda x: x),
                wrap_function("dup", lambda x: x),
            ]
        )


def test_pipeline_final_none_when_empty() -> None:
    p = Pipeline([])
    result = p.run(42)
    assert result.final is None
    assert result.stages == ()


def test_pipeline_deterministic() -> None:
    p = Pipeline(
        [
            wrap_function("plus_one", lambda x: x + 1),
            wrap_function("times_two", lambda x: x * 2),
        ]
    )
    r1 = p.run(5)
    r2 = p.run(5)
    assert r1.final is not None and r2.final is not None
    assert r1.final.value == r2.final.value


def test_pipeline_accepts_stage_context() -> None:
    p = Pipeline([wrap_function("noop", lambda x: x)])
    result = p.run(42, StageContext(run_id="test"))
    assert result.final is not None
    assert result.final.value == 42
