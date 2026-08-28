"""Tests for LLM refinement wiring in PipelineCoordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.llm_refine import RefinementLog, _LLM_REFINABLE_STAGES
from architecture_model.pipeline.protocol import (
    PipelineContext,
    QualityMetrics,
    StageResult,
)


@dataclass
class FakeOutput:
    modules: list = field(default_factory=list)
    capabilities: list = field(default_factory=list)
    components: list = field(default_factory=list)


class FakeStage:
    def __init__(self, name: str, requires: list[str] | None = None):
        self.name = name
        self.version = "1.0"
        self.requires = requires or []
        self._result = StageResult(
            output=FakeOutput(),
            quality=QualityMetrics(score=80.0),
        )

    def run(self, context):
        return self._result

    def can_run(self, context):
        return True

    def output_path(self, context):
        return context.output_dir / f"{self.name}.json"


def _make_ctx(llm_callback=None) -> PipelineContext:
    return PipelineContext(
        repo_path=Path("/tmp/test"),
        output_dir=Path("/tmp/test/out"),
        llm_callback=llm_callback,
    )


@patch("architecture_model.pipeline.coordinator.refine_with_llm", new_callable=AsyncMock)
def test_refinement_called_for_infer(mock_refine):
    """Refinement is called for 'infer' stage when llm_callback is set."""
    mock_refine.return_value = (
        StageResult(output=FakeOutput(), quality=QualityMetrics(score=85.0)),
        RefinementLog(stage="infer"),
    )

    stages = {
        "observe": FakeStage("observe"),
        "infer": FakeStage("infer", requires=["observe"]),
    }
    coord = PipelineCoordinator(stages)
    coord._evaluate_gates = MagicMock()
    ctx = _make_ctx(llm_callback=AsyncMock(return_value="{}"))

    coord.run_stage("infer", ctx)

    mock_refine.assert_called_once()
    call_args = mock_refine.call_args
    assert call_args[0][1] == "infer"  # stage_name
    assert len(ctx.refinement_logs) == 1
    assert ctx.refinement_logs[0].stage == "infer"


@patch("architecture_model.pipeline.coordinator.refine_with_llm", new_callable=AsyncMock)
def test_refinement_not_called_for_observe(mock_refine):
    """Refinement is NOT called for 'observe' stage (AST-only)."""
    stages = {"observe": FakeStage("observe")}
    coord = PipelineCoordinator(stages)
    coord._evaluate_gates = MagicMock()
    ctx = _make_ctx(llm_callback=AsyncMock(return_value="{}"))

    coord.run_stage("observe", ctx)

    mock_refine.assert_not_called()
    assert len(ctx.refinement_logs) == 0


@patch("architecture_model.pipeline.coordinator.refine_with_llm", new_callable=AsyncMock)
def test_refinement_not_called_without_llm_callback(mock_refine):
    """Refinement is NOT called when llm_callback is None."""
    stages = {
        "observe": FakeStage("observe"),
        "infer": FakeStage("infer", requires=["observe"]),
    }
    coord = PipelineCoordinator(stages)
    coord._evaluate_gates = MagicMock()
    ctx = _make_ctx(llm_callback=None)

    coord.run_stage("infer", ctx)

    mock_refine.assert_not_called()


@patch("architecture_model.pipeline.coordinator.refine_with_llm", new_callable=AsyncMock)
def test_refinement_log_none_not_appended(mock_refine):
    """When refinement returns None log, nothing is appended."""
    mock_refine.return_value = (
        StageResult(output=FakeOutput(), quality=QualityMetrics(score=80.0)),
        None,
    )

    stages = {
        "observe": FakeStage("observe"),
        "infer": FakeStage("infer", requires=["observe"]),
    }
    coord = PipelineCoordinator(stages)
    coord._evaluate_gates = MagicMock()
    ctx = _make_ctx(llm_callback=AsyncMock(return_value="{}"))

    coord.run_stage("infer", ctx)

    assert len(ctx.refinement_logs) == 0


def test_llm_review_skipped_for_refined_stages():
    """LLM review in _evaluate_gates is skipped for refinable stages."""
    stages = {"observe": FakeStage("observe")}
    coord = PipelineCoordinator(stages)
    callback = AsyncMock(return_value="{}")
    ctx = _make_ctx(llm_callback=callback)

    result = StageResult(output=FakeOutput(), quality=QualityMetrics(score=80.0))

    # _evaluate_gates imports get_gates_for_stage internally
    with patch("architecture_model.pipeline.gates.get_gates_for_stage", return_value=[]):
        coord._evaluate_gates("infer", result, ctx)

    # Review should have empty llm_review since infer is in _LLM_REFINABLE_STAGES
    assert len(ctx.review_log) == 1
    assert ctx.review_log[0].llm_review == ""


def test_llm_review_runs_for_non_refined_stages():
    """LLM review in _evaluate_gates runs for stages NOT in _LLM_REFINABLE_STAGES."""
    stages = {"observe": FakeStage("observe")}
    coord = PipelineCoordinator(stages)

    # observe is not in _LLM_REFINABLE_STAGES, so LLM review should attempt to run
    assert "observe" not in _LLM_REFINABLE_STAGES


@patch("architecture_model.pipeline.coordinator.refine_with_llm", new_callable=AsyncMock)
def test_refinement_called_for_all_refinable_stages(mock_refine):
    """Refinement is called for all 4 refinable stages."""
    mock_refine.return_value = (
        StageResult(output=FakeOutput(), quality=QualityMetrics(score=85.0)),
        RefinementLog(stage="test"),
    )

    stages = {
        "observe": FakeStage("observe"),
        "infer": FakeStage("infer", requires=["observe"]),
        "allocate": FakeStage("allocate", requires=["infer"]),
        "relate": FakeStage("relate", requires=["allocate"]),
        "specify": FakeStage("specify", requires=["allocate"]),
    }
    coord = PipelineCoordinator(stages)
    coord._evaluate_gates = MagicMock()
    ctx = _make_ctx(llm_callback=AsyncMock(return_value="{}"))

    coord.run_to("specify", ctx)

    # observe is not refined, but infer, allocate, relate, specify are
    # However specify depends on allocate (not relate), so run_to("specify")
    # runs: observe, infer, allocate, specify (not relate)
    assert mock_refine.call_count == 3  # infer, allocate, specify
    assert len(ctx.refinement_logs) == 3


def test_build_refinement_inputs():
    """_build_refinement_inputs extracts data from cached stage results."""
    stages = {"observe": FakeStage("observe")}
    coord = PipelineCoordinator(stages)
    ctx = _make_ctx()

    @dataclass
    class FakeModule:
        path: str = "src/foo.py"
        functions: list = field(default_factory=list)
        imports: list = field(default_factory=list)

    @dataclass
    class FakeCap:
        id: str = "CAP-F1"
        name: str = "Foo"

    ctx.cache["observe"] = StageResult(
        output=MagicMock(modules=[FakeModule()]),
        quality=QualityMetrics(score=90.0),
    )
    ctx.cache["infer"] = StageResult(
        output=MagicMock(capabilities=[FakeCap()]),
        quality=QualityMetrics(score=85.0),
    )

    inputs = coord._build_refinement_inputs("allocate", ctx)

    assert "modules" in inputs
    assert "capabilities" in inputs
    assert len(inputs["capabilities"]) == 1
    assert inputs["capabilities"][0]["id"] == "CAP-F1"
