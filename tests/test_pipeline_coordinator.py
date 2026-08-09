"""Tests for PipelineCoordinator."""

from pathlib import Path

import pytest

from architecture_model.pipeline.coordinator import PipelineCoordinator
from architecture_model.pipeline.protocol import (
    PipelineContext,
    QualityMetrics,
    StageResult,
)


class FakeStage:
    def __init__(self, name, requires, output="done"):
        self.name = name
        self.version = "1.0"
        self.requires = requires
        self._output = output
        self.run_count = 0

    def run(self, context):
        self.run_count += 1
        context.cache[self.name] = StageResult(
            output=self._output,
            quality=QualityMetrics(score=90, sub_scores={}, thresholds={}),
        )
        return context.cache[self.name]

    def can_run(self, context):
        return all(context.has(r) for r in self.requires)

    def output_path(self, context):
        return context.output_dir / f"{self.name}.json"


def make_dag():
    stages = {
        "observe": FakeStage("observe", []),
        "infer": FakeStage("infer", ["observe"]),
        "allocate": FakeStage("allocate", ["observe", "infer"]),
        "relate": FakeStage("relate", ["observe", "infer", "allocate"]),
        "specify": FakeStage("specify", ["observe", "allocate"]),
        "contract": FakeStage("contract", ["observe", "allocate"]),
        "validate": FakeStage("validate", ["observe", "infer", "allocate", "relate"]),
    }
    return stages


def make_ctx(tmp_path=None):
    p = tmp_path or Path("/tmp/test")
    return PipelineContext(repo_path=p, output_dir=p / "out")


class TestPipelineCoordinator:
    def test_run_single_stage_no_deps(self, tmp_path):
        stages = make_dag()
        coord = PipelineCoordinator(stages)
        ctx = make_ctx(tmp_path)
        coord.run_stage("observe", ctx)
        assert stages["observe"].run_count == 1

    def test_run_stage_resolves_deps(self, tmp_path):
        stages = make_dag()
        coord = PipelineCoordinator(stages)
        ctx = make_ctx(tmp_path)
        coord.run_stage("allocate", ctx)
        assert stages["observe"].run_count == 1
        assert stages["infer"].run_count == 1
        assert stages["allocate"].run_count == 1

    def test_run_to_target(self, tmp_path):
        stages = make_dag()
        coord = PipelineCoordinator(stages)
        ctx = make_ctx(tmp_path)
        results = coord.run_to("validate", ctx)
        assert stages["observe"].run_count == 1
        assert stages["infer"].run_count == 1
        assert stages["allocate"].run_count == 1
        assert stages["relate"].run_count == 1
        assert stages["validate"].run_count == 1
        assert stages["specify"].run_count == 0
        assert stages["contract"].run_count == 0
        assert "validate" in results

    def test_skips_cached_stages(self, tmp_path):
        stages = make_dag()
        coord = PipelineCoordinator(stages)
        ctx = make_ctx(tmp_path)
        # Pre-cache observe
        ctx.cache["observe"] = StageResult(
            output="cached",
            quality=QualityMetrics(score=90, sub_scores={}, thresholds={}),
        )
        coord.run_stage("infer", ctx)
        assert stages["observe"].run_count == 0
        assert stages["infer"].run_count == 1

    def test_dependency_order(self):
        stages = make_dag()
        coord = PipelineCoordinator(stages)
        order = coord.resolve_order("validate")
        # Each stage must come after its deps
        for name in order:
            idx = order.index(name)
            for dep in stages[name].requires:
                assert order.index(dep) < idx, f"{dep} must come before {name}"

    def test_specify_independent_of_relate(self):
        stages = make_dag()
        coord = PipelineCoordinator(stages)
        order = coord.resolve_order("specify")
        assert "relate" not in order
        assert "specify" in order
        assert "observe" in order
        assert "allocate" in order

    def test_unknown_stage_raises(self):
        stages = make_dag()
        coord = PipelineCoordinator(stages)
        with pytest.raises(KeyError):
            coord.resolve_order("nonexistent")

    def test_run_all_runs_everything(self, tmp_path):
        stages = make_dag()
        coord = PipelineCoordinator(stages)
        ctx = make_ctx(tmp_path)
        results = coord.run_all(ctx)
        for s in stages.values():
            assert s.run_count == 1
        assert len(results) == len(stages)

    def test_circular_dep_detection(self, tmp_path):
        stages = {
            "a": FakeStage("a", ["b"]),
            "b": FakeStage("b", ["a"]),
        }
        coord = PipelineCoordinator(stages)
        ctx = make_ctx(tmp_path)
        with pytest.raises(RuntimeError):
            coord.run_all(ctx)
