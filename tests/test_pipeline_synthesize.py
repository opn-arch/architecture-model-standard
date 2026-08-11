"""Tests for the synthesize pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.protocol import (
    LLMCallRecord,
    PipelineContext,
    QualityMetrics,
    StageResult,
)
from architecture_model.pipeline.synthesize import (
    ABBREVIATED_STAGES,
    FULL_PIPELINE_STAGES,
    SynthesizeStage,
    _build_manifest_json,
    _build_sos_model,
    _build_system_model_yaml,
    _decide_stages,
)
from architecture_model.pipeline.synthesize_types import (
    SoSModel,
    SynthesizeResult,
    SystemModel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _FakeComponent:
    id: str = "COMP-1"
    name: str = "TestComp"
    files: list[str] = field(default_factory=lambda: ["a.py", "b.py"])


@dataclass
class _FakeCapability:
    id: str = "CAP-1"
    name: str = "TestCap"


@dataclass
class _FakeRelationship:
    from_id: str = "COMP-1"
    to_id: str = "CAP-1"
    rel_type: str = "realizes"
    evidence: list = field(default_factory=list)


@dataclass
class _FakeAllocOutput:
    components: list = field(default_factory=list)
    file_coverage: float = 1.0


@dataclass
class _FakeInferOutput:
    capabilities: list = field(default_factory=list)
    actors: list = field(default_factory=list)
    behaviors: list = field(default_factory=list)


@dataclass
class _FakeRelateOutput:
    relationships: list = field(default_factory=list)


@dataclass
class _FakeModule:
    file_path: str = "mod.py"
    functions: list = field(default_factory=list)
    classes: list = field(default_factory=list)


@dataclass
class _FakeObserveOutput:
    modules: list = field(default_factory=list)


def _make_ctx(tmp_path: Path, **cache_extras: StageResult) -> PipelineContext:
    ctx = PipelineContext(repo_path=tmp_path, output_dir=tmp_path / "out")
    for k, v in cache_extras.items():
        ctx.cache[k] = v
    return ctx


def _quality() -> QualityMetrics:
    return QualityMetrics(score=100.0)


def _stage_result(output: Any) -> StageResult:
    return StageResult(output=output, quality=_quality())


class MockCoordinator:
    def __init__(self, results: dict[str, StageResult] | None = None):
        self.calls: list[tuple[str, str]] = []
        self._results = results or {}

    def run_to(self, target: str, ctx: PipelineContext) -> dict[str, StageResult]:
        self.calls.append((target, ctx.scope))
        return dict(self._results)


# ---------------------------------------------------------------------------
# Type defaults
# ---------------------------------------------------------------------------

class TestTypeDefaults:
    def test_system_model_defaults(self):
        sm = SystemModel(system_id="SYS-1", name="Test")
        assert sm.system_id == "SYS-1"
        assert sm.model_yaml == ""
        assert sm.stage_results == {}
        assert sm.llm_calls == []

    def test_sos_model_defaults(self):
        sos = SoSModel()
        assert sos.model_yaml == ""
        assert sos.actors == []
        assert sos.inter_system_interfaces == []

    def test_synthesize_result_defaults(self):
        sr = SynthesizeResult()
        assert sr.sos_model is None
        assert sr.system_models == []
        assert sr.all_llm_calls == []


# ---------------------------------------------------------------------------
# Stage metadata
# ---------------------------------------------------------------------------

class TestStageMetadata:
    def test_name_and_version(self):
        stage = SynthesizeStage()
        assert stage.name == "synthesize"
        assert stage.version == "1.0"

    def test_requires(self):
        stage = SynthesizeStage()
        assert "decompose" in stage.requires
        assert "observe" in stage.requires

    def test_can_run_needs_decompose(self, tmp_path):
        stage = SynthesizeStage()
        ctx = _make_ctx(tmp_path)
        assert not stage.can_run(ctx)

        ctx.cache["decompose"] = _stage_result(DecomposeResult())
        assert stage.can_run(ctx)


# ---------------------------------------------------------------------------
# _decide_stages
# ---------------------------------------------------------------------------

class TestDecideStages:
    def test_large_system_gets_full(self):
        b = SystemBoundary(system_id="S1", name="Big", files=[f"f{i}.py" for i in range(10)])
        assert _decide_stages(b) == FULL_PIPELINE_STAGES

    def test_small_system_gets_abbreviated(self):
        b = SystemBoundary(system_id="S1", name="Small", files=["a.py", "b.py"])
        assert _decide_stages(b) == ABBREVIATED_STAGES

    def test_boundary_at_8(self):
        b = SystemBoundary(system_id="S1", name="Edge", files=[f"f{i}.py" for i in range(8)])
        assert _decide_stages(b) == FULL_PIPELINE_STAGES

    def test_boundary_at_7(self):
        b = SystemBoundary(system_id="S1", name="Edge", files=[f"f{i}.py" for i in range(7)])
        assert _decide_stages(b) == ABBREVIATED_STAGES


# ---------------------------------------------------------------------------
# _build_system_model_yaml
# ---------------------------------------------------------------------------

class TestBuildSystemModelYaml:
    def test_produces_valid_yaml(self):
        boundary = SystemBoundary(system_id="SYS-core", name="Core")
        results = {
            "allocate": _stage_result(_FakeAllocOutput(components=[_FakeComponent()])),
            "infer": _stage_result(_FakeInferOutput(capabilities=[_FakeCapability()])),
            "relate": _stage_result(_FakeRelateOutput(relationships=[_FakeRelationship()])),
        }
        yaml_str = _build_system_model_yaml(boundary, results)
        parsed = yaml.safe_load(yaml_str)

        assert parsed["meta"]["system"] == "Core"
        assert parsed["meta"]["schema_version"] == "2.0"
        assert len(parsed["entities"]["components"]) == 1
        assert len(parsed["entities"]["capabilities"]) == 1
        assert len(parsed["relationships"]) == 1

    def test_empty_results(self):
        boundary = SystemBoundary(system_id="SYS-x", name="Empty")
        yaml_str = _build_system_model_yaml(boundary, {})
        parsed = yaml.safe_load(yaml_str)
        assert parsed["meta"]["system"] == "Empty"
        assert parsed["relationships"] == []


# ---------------------------------------------------------------------------
# _build_manifest_json
# ---------------------------------------------------------------------------

class TestBuildManifestJson:
    def test_with_observe_output(self):
        results = {
            "observe": _stage_result(_FakeObserveOutput(modules=[_FakeModule()]))
        }
        import json
        data = json.loads(_build_manifest_json(results))
        assert len(data["modules"]) == 1

    def test_no_observe(self):
        assert _build_manifest_json({}) == "{}"


# ---------------------------------------------------------------------------
# run() without coordinator
# ---------------------------------------------------------------------------

class TestRunWithoutCoordinator:
    def test_produces_sos_from_top_level(self, tmp_path):
        stage = SynthesizeStage()
        decompose = DecomposeResult(
            systems=[
                SystemBoundary(
                    system_id="SYS-core",
                    name="Core",
                    files=[f"f{i}.py" for i in range(10)],
                    is_full_system=True,
                ),
            ],
            inter_system_edges=[("SYS-core", "SYS-utils", "depends-on")],
        )
        ctx = _make_ctx(
            tmp_path,
            decompose=_stage_result(decompose),
            observe=_stage_result(_FakeObserveOutput()),
            infer=_stage_result(_FakeInferOutput(actors=[_FakeCapability(id="ACT-1", name="User")])),
            allocate=_stage_result(_FakeAllocOutput()),
            relate=_stage_result(_FakeRelateOutput()),
        )

        result = stage.run(ctx)
        synth: SynthesizeResult = result.output

        assert synth.sos_model is not None
        assert synth.sos_model_yaml != ""
        assert len(synth.system_models) == 1
        assert synth.system_models[0].model_yaml == ""  # no coordinator
        assert synth.pipeline_report_md != ""
        assert synth.lessons_md != ""

        # SoS should have inter-system edge
        sos_parsed = yaml.safe_load(synth.sos_model_yaml)
        assert len(sos_parsed["relationships"]) == 1
        assert sos_parsed["relationships"][0]["from"] == "SYS-core"

    def test_no_coordinator_diagnostic(self, tmp_path):
        stage = SynthesizeStage()
        decompose = DecomposeResult(
            systems=[SystemBoundary(system_id="S1", name="A", files=["a.py"] * 10, is_full_system=True)]
        )
        ctx = _make_ctx(
            tmp_path,
            decompose=_stage_result(decompose),
            observe=_stage_result(_FakeObserveOutput()),
            infer=_stage_result(_FakeInferOutput()),
            allocate=_stage_result(_FakeAllocOutput()),
            relate=_stage_result(_FakeRelateOutput()),
        )
        result = stage.run(ctx)
        codes = [d.code for d in result.diagnostics]
        assert "NO_COORDINATOR" in codes


# ---------------------------------------------------------------------------
# run() with mock coordinator
# ---------------------------------------------------------------------------

class TestRunWithCoordinator:
    def test_scoped_runs(self, tmp_path):
        sub_results = {
            "observe": _stage_result(_FakeObserveOutput(modules=[_FakeModule()])),
            "infer": _stage_result(_FakeInferOutput(capabilities=[_FakeCapability()])),
            "allocate": _stage_result(_FakeAllocOutput(components=[_FakeComponent()])),
            "relate": _stage_result(_FakeRelateOutput(relationships=[_FakeRelationship()])),
        }
        coordinator = MockCoordinator(results=sub_results)

        decompose = DecomposeResult(
            systems=[
                SystemBoundary(system_id="SYS-a", name="Alpha", files=[f"f{i}.py" for i in range(10)], is_full_system=True),
                SystemBoundary(system_id="SYS-b", name="Beta", files=["x.py", "y.py"], is_full_system=True),
            ],
            inter_system_edges=[("SYS-a", "SYS-b", "depends-on")],
        )
        ctx = _make_ctx(
            tmp_path,
            decompose=_stage_result(decompose),
            observe=_stage_result(_FakeObserveOutput()),
            infer=_stage_result(_FakeInferOutput()),
            allocate=_stage_result(_FakeAllocOutput()),
            relate=_stage_result(_FakeRelateOutput()),
        )
        ctx.config["coordinator"] = coordinator

        stage = SynthesizeStage()
        result = stage.run(ctx)
        synth: SynthesizeResult = result.output

        # Coordinator was called for both systems
        assert len(coordinator.calls) == 2
        scopes = {c[1] for c in coordinator.calls}
        assert "SYS-a" in scopes
        assert "SYS-b" in scopes

        # Full system gets validate as last stage
        alpha_call = [c for c in coordinator.calls if c[1] == "SYS-a"][0]
        assert alpha_call[0] == "validate"  # >= 8 files

        # Small system gets infer as last stage
        beta_call = [c for c in coordinator.calls if c[1] == "SYS-b"][0]
        assert beta_call[0] == "infer"  # < 8 files

        # System models have YAML
        for sm in synth.system_models:
            assert sm.model_yaml != ""
            assert sm.pipeline_report_md != ""

    def test_inline_components_no_scoped_run(self, tmp_path):
        coordinator = MockCoordinator()
        decompose = DecomposeResult(
            inline_components=[
                SystemBoundary(system_id="SYS-utils", name="Utils", files=["u.py"], is_full_system=False),
            ],
        )
        ctx = _make_ctx(
            tmp_path,
            decompose=_stage_result(decompose),
            observe=_stage_result(_FakeObserveOutput()),
            infer=_stage_result(_FakeInferOutput()),
            allocate=_stage_result(_FakeAllocOutput()),
            relate=_stage_result(_FakeRelateOutput()),
        )
        ctx.config["coordinator"] = coordinator

        stage = SynthesizeStage()
        result = stage.run(ctx)

        assert len(coordinator.calls) == 0
        assert len(result.output.system_models) == 1
        assert result.output.system_models[0].name == "Utils"


# ---------------------------------------------------------------------------
# SoS model structure
# ---------------------------------------------------------------------------

class TestSoSModel:
    def test_inter_system_edges(self):
        systems = [SystemModel(system_id="SYS-a", name="A"), SystemModel(system_id="SYS-b", name="B")]
        decompose = DecomposeResult(
            inter_system_edges=[("SYS-a", "SYS-b", "depends-on")]
        )
        sos = _build_sos_model(systems, [], decompose, {})
        assert len(sos.inter_system_interfaces) == 1
        assert sos.inter_system_interfaces[0]["from"] == "SYS-a"

        parsed = yaml.safe_load(sos.model_yaml)
        assert parsed["meta"]["system_of_systems"] is True
        assert len(parsed["entities"]["systems"]) == 2

    def test_actors_from_infer(self):
        infer_out = _FakeInferOutput(actors=[_FakeCapability(id="ACT-1", name="Admin")])
        top_results = {"infer": _stage_result(infer_out)}
        sos = _build_sos_model([], [], DecomposeResult(), top_results)
        assert len(sos.actors) == 1
        assert sos.actors[0]["name"] == "Admin"


# ---------------------------------------------------------------------------
# Pipeline reports
# ---------------------------------------------------------------------------

class TestPipelineReports:
    def test_reports_generated(self, tmp_path):
        stage = SynthesizeStage()
        decompose = DecomposeResult()
        ctx = _make_ctx(
            tmp_path,
            decompose=_stage_result(decompose),
            observe=_stage_result(_FakeObserveOutput()),
            infer=_stage_result(_FakeInferOutput()),
            allocate=_stage_result(_FakeAllocOutput()),
            relate=_stage_result(_FakeRelateOutput()),
        )
        result = stage.run(ctx)
        assert "Pipeline Report" in result.output.pipeline_report_md
        assert "Lessons" in result.output.lessons_md
