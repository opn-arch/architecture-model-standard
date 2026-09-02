"""Tests for the synthesize pipeline stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from architecture_model.pipeline.decompose_types import DecomposeResult, SystemBoundary
from architecture_model.pipeline.protocol import (
    Evidence,
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
    _merge_requirements,
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
    interfaces: list[dict] = field(default_factory=list)


@dataclass
class _FakeCapability:
    id: str = "CAP-1"
    name: str = "TestCap"
    description: str = ""
    intent: str = ""
    goals: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    monitored: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=lambda: ["a.py"])
    moes: list[str] = field(default_factory=list)
    value_function: str = ""
    trade_offs: list[str] = field(default_factory=list)


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
    path: str = "mod.py"
    functions: list = field(default_factory=list)
    classes: list = field(default_factory=list)


@dataclass
class _FakeObserveOutput:
    modules: list = field(default_factory=list)
    constraints: list = field(default_factory=list)


@dataclass
class _FakeInterface:
    id: str
    name: str
    component_id: str
    interface_type: str = "library"
    methods: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class _FakeRequirement:
    id: str
    name: str
    source_file: str
    text: str = "Value must be at least 5"
    rationale: str = "Source constant defines the supported minimum"
    moe: str = "Observed value is >= 5"
    source_type: str = "constant"
    value_function: str = "min(1, actual / 5)"
    priority: str = "must"
    status: str = "ACTIVE"


@dataclass
class _FakeSpecifyOutput:
    interfaces: list = field(default_factory=list)
    requirements: list = field(default_factory=list)


@dataclass
class _FakeBehavior:
    id: str = "BEH-1"
    name: str = "Process request"
    capability_id: str = "CAP-1"
    actor_id: str = ""
    steps: list[str] = field(default_factory=lambda: ["Validate", "Persist"])
    triggers: list[str] = field(default_factory=list)
    behavior_type: str = "workflow"
    source_file: str = "a.py"
    intent: str = "Safely process a request"
    description: str = "Request workflow"
    trigger: str = "request received"
    preconditions: list[str] = field(default_factory=lambda: ["request is valid"])
    postconditions: list[str] = field(default_factory=lambda: ["request is stored"])
    frequency: str = "per request"
    pattern: str = "sequential"


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
        self.contexts: list[PipelineContext] = []
        self._results = results or {}

    def run_to(self, target: str, ctx: PipelineContext) -> dict[str, StageResult]:
        self.calls.append((target, ctx.scope))
        self.contexts.append(ctx)
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
        b = SystemBoundary(
            system_id="S1", name="Big", files=[f"f{i}.py" for i in range(10)]
        )
        assert _decide_stages(b) == FULL_PIPELINE_STAGES

    def test_small_full_system_gets_complete_pipeline(self):
        b = SystemBoundary(system_id="S1", name="Small", files=["a.py", "b.py"])
        assert _decide_stages(b) == FULL_PIPELINE_STAGES

    def test_boundary_at_8(self):
        b = SystemBoundary(
            system_id="S1", name="Edge", files=[f"f{i}.py" for i in range(8)]
        )
        assert _decide_stages(b) == FULL_PIPELINE_STAGES

    def test_boundary_at_7(self):
        b = SystemBoundary(
            system_id="S1", name="Edge", files=[f"f{i}.py" for i in range(7)]
        )
        assert _decide_stages(b) == FULL_PIPELINE_STAGES

    def test_five_file_full_system_runs_through_validate(self):
        boundary = SystemBoundary(
            system_id="SYS-5", name="Five", files=[f"f{i}.py" for i in range(5)],
            is_full_system=True,
        )
        assert _decide_stages(boundary) == FULL_PIPELINE_STAGES


# ---------------------------------------------------------------------------
# _build_system_model_yaml
# ---------------------------------------------------------------------------


class TestBuildSystemModelYaml:
    def test_normalization_collisions_are_unique_within_projection(self):
        results = {
            "allocate": _stage_result(_FakeAllocOutput([
                _FakeComponent("ITEM A", "Worker", ["worker.py"]),
            ])),
            "infer": _stage_result(_FakeInferOutput(capabilities=[
                _FakeCapability("ITEM-A", "Work", source_files=["worker.py"]),
            ])),
            "relate": _stage_result(_FakeRelateOutput([
                _FakeRelationship("ITEM A", "ITEM-A", "realizes"),
            ])),
        }

        parsed = yaml.safe_load(_build_system_model_yaml(
            SystemBoundary("COMP-inline", "Inline", files=["worker.py"]), results,
        ))

        component_id = parsed["entities"]["components"][0]["id"]
        capability_id = parsed["entities"]["capabilities"][0]["id"]
        assert component_id != capability_id
        assert parsed["relationships"] == [{
            "from": component_id, "to": capability_id, "type": "realizes",
        }]

    def test_projects_only_boundary_entities_and_derives_local_semantics(self):
        local = _FakeComponent(
            id="COMP-1", name="Worker", files=["inline/worker.py"],
            interfaces=[{"name": "typed", "kind": "provides", "signature": "() -> int"}],
        )
        foreign = _FakeComponent(id="COMP-2", name="Foreign", files=["other.py"])
        capability = _FakeCapability(
            id="CAP-1", name="Process jobs", intent="Process jobs reliably",
            goals=["Complete each job"], failure_modes=["Queue stalls"],
            monitored=["queue_depth"], source_files=["inline/worker.py"],
            moes=["95 percent complete"], value_function="completed / total",
            trade_offs=["Latency versus throughput"],
        )
        foreign_capability = _FakeCapability(
            id="CAP-2", name="Foreign", source_files=["other.py"],
        )
        behavior = _FakeBehavior(
            id="BEH-1", name="Run worker", source_file="inline/worker.py",
            capability_id="CAP-1", steps=["Read queue", "Process job"],
        )
        foreign_behavior = _FakeBehavior(
            id="BEH-2", name="Foreign flow", source_file="other.py",
            capability_id="CAP-2",
        )
        results = {
            "allocate": _stage_result(_FakeAllocOutput([local, foreign])),
            "infer": _stage_result(_FakeInferOutput(
                capabilities=[capability, foreign_capability],
                behaviors=[behavior, foreign_behavior],
            )),
            "specify": _stage_result(_FakeSpecifyOutput(
                interfaces=[
                    _FakeInterface("IF-1", "Worker API", "COMP-1", methods=["run"]),
                    _FakeInterface("IF-2", "Foreign API", "COMP-2"),
                ],
                requirements=[
                    _FakeRequirement("REQ-1", "MIN_JOBS", "inline/worker.py"),
                    _FakeRequirement("REQ-2", "OTHER", "other.py"),
                ],
            )),
            "relate": _stage_result(_FakeRelateOutput([
                _FakeRelationship("COMP-1", "CAP-1", "realizes"),
                _FakeRelationship("COMP-2", "CAP-2", "realizes"),
            ])),
        }

        parsed = yaml.safe_load(_build_system_model_yaml(
            SystemBoundary(
                system_id="COMP-inline", name="Inline", files=["inline/worker.py"],
                is_full_system=False,
            ),
            results,
        ))

        assert [item["id"] for item in parsed["entities"]["components"]] == ["COMP-1"]
        assert [item["id"] for item in parsed["entities"]["capabilities"]] == ["CAP-1"]
        assert [item["id"] for item in parsed["entities"]["behaviors"]] == ["BEH-1"]
        assert [item["id"] for item in parsed["entities"]["interfaces"]] == ["IF-1"]
        assert [item["id"] for item in parsed["entities"]["requirements"]] == ["REQ-1"]
        component = parsed["entities"]["components"][0]
        assert component["intent"] == "Process jobs reliably"
        assert component["goals"] == ["Complete each job"]
        assert component["failure_modes"] == ["Queue stalls"]
        assert component["monitored"] == ["queue_depth"]
        assert component["responsibilities"] == ["Process jobs", "Complete each job"]
        assert component["requirements"] == ["REQ-1"]
        assert component["interface_refs"] == ["IF-1"]
        assert component["interfaces"] == local.interfaces
        assert component["moes"] == ["95 percent complete"]
        assert component["value_function"] == "completed / total"
        assert component["trade_offs"] == ["Latency versus throughput"]
        assert component["extensions"]["semantic_derivation"]["capabilities"] == ["CAP-1"]
        projected_capability = parsed["entities"]["capabilities"][0]
        projected_behavior = parsed["entities"]["behaviors"][0]
        projected_interface = parsed["entities"]["interfaces"][0]
        assert projected_interface["type"] == "internal"
        assert projected_interface["provider"] == "COMP-1"
        assert projected_capability["requirements"] == ["REQ-1"]
        assert projected_capability["interface_refs"] == ["IF-1"]
        assert projected_behavior["requirements"] == ["REQ-1"]
        assert projected_behavior["interface_refs"] == ["IF-1"]
        assert projected_behavior["structured_steps"][0]["component_ref"] == "COMP-1"
        assert {tuple(rel.values()) for rel in parsed["relationships"]} >= {
            ("COMP-1", "IF-1", "exposes"),
            ("COMP-1", "REQ-1", "satisfies"),
            ("COMP-1", "CAP-1", "realizes"),
            ("COMP-1", "BEH-1", "traces-to"),
        }

    def test_component_uses_requirement_measures_when_capability_has_none(self):
        results = {
            "allocate": _stage_result(_FakeAllocOutput([
                _FakeComponent("COMP-1", "Worker", ["worker.py"]),
            ])),
            "infer": _stage_result(_FakeInferOutput(capabilities=[
                _FakeCapability("CAP-1", "Work", intent="Do work", source_files=["worker.py"]),
            ])),
            "specify": _stage_result(_FakeSpecifyOutput(requirements=[
                _FakeRequirement("REQ-1", "MIN_WORK", "worker.py"),
            ])),
            "relate": _stage_result(_FakeRelateOutput([
                _FakeRelationship("COMP-1", "CAP-1", "realizes"),
            ])),
        }

        parsed = yaml.safe_load(_build_system_model_yaml(
            SystemBoundary("COMP-inline", "Inline", files=["worker.py"]), results,
        ))

        component = parsed["entities"]["components"][0]
        assert component["moes"] == ["Observed value is >= 5"]
        assert component["value_function"] == "min(1, actual / 5)"
        assert component["rationale"] == "Source constant defines the supported minimum"
        assert component["extensions"]["semantic_derivation"]["requirements"] == ["REQ-1"]

    def test_produces_valid_yaml(self):
        boundary = SystemBoundary(system_id="SYS-core", name="Core")
        results = {
            "allocate": _stage_result(_FakeAllocOutput(components=[_FakeComponent()])),
            "infer": _stage_result(_FakeInferOutput(capabilities=[_FakeCapability()])),
            "relate": _stage_result(
                _FakeRelateOutput(relationships=[_FakeRelationship()])
            ),
        }
        yaml_str = _build_system_model_yaml(boundary, results)
        parsed = yaml.safe_load(yaml_str)

        assert parsed["meta"]["system"] == "Core"
        assert parsed["meta"]["schema_version"] == "2.0.0"
        assert len(parsed["entities"]["components"]) == 1
        assert len(parsed["entities"]["capabilities"]) == 1
        assert len(parsed["relationships"]) == 1

    def test_empty_results(self):
        boundary = SystemBoundary(system_id="SYS-x", name="Empty")
        yaml_str = _build_system_model_yaml(boundary, {})
        parsed = yaml.safe_load(yaml_str)
        assert parsed["meta"]["system"] == "Empty"
        assert parsed["relationships"] == []

    def test_capability_description_preserved(self):
        """Capability descriptions and status should survive synthesis."""
        cap = _FakeCapability(id="CAP-1", name="Test", description="A test capability")
        boundary = SystemBoundary(system_id="SYS-1", name="Sys")
        results = {
            "infer": _stage_result(_FakeInferOutput(capabilities=[cap])),
        }
        yaml_str = _build_system_model_yaml(boundary, results)
        parsed = yaml.safe_load(yaml_str)
        cap_out = parsed["entities"]["capabilities"][0]
        assert cap_out["status"] == "ACTIVE"
        assert cap_out["description"] == "A test capability"

    def test_capability_no_description_omitted(self):
        """Capabilities without description should not have the key."""
        cap = _FakeCapability(id="CAP-1", name="Test")
        boundary = SystemBoundary(system_id="SYS-1", name="Sys")
        results = {
            "infer": _stage_result(_FakeInferOutput(capabilities=[cap])),
        }
        yaml_str = _build_system_model_yaml(boundary, results)
        parsed = yaml.safe_load(yaml_str)
        cap_out = parsed["entities"]["capabilities"][0]
        assert cap_out["status"] == "ACTIVE"
        assert "description" not in cap_out

    def test_preserves_workflow_semantics_and_derives_valid_traceability(self, tmp_path):
        boundary = SystemBoundary(
            system_id="SYS-1", name="Orders", files=["a.py", "b.py"]
        )
        results = {
            "allocate": _stage_result(_FakeAllocOutput(components=[_FakeComponent()])),
            "infer": _stage_result(_FakeInferOutput(
                capabilities=[_FakeCapability(intent="Accept orders", goals=["Reliable intake"])],
                behaviors=[_FakeBehavior()],
            )),
            "relate": _stage_result(_FakeRelateOutput()),
        }

        parsed = yaml.safe_load(_build_system_model_yaml(
            boundary, results, project_name="shop"
        ))
        behavior = parsed["entities"]["behaviors"][0]

        generated_at = parsed["meta"].pop("generated_at")
        assert generated_at
        assert parsed["meta"] == {
            "project": "shop",
            "schema_version": "2.0.0",
            "system": "Orders",
            "system_id": "SYS-1",
            "parent_model": "../../.architecture-model.yaml",
            "refines_component": "SYS-1",
            "source_artifacts": ["a.py", "b.py"],
        }
        assert behavior["description"] == "Request workflow"
        assert behavior["intent"] == "Safely process a request"
        assert behavior["trigger"] == "request received"
        assert behavior["preconditions"] == ["request is valid"]
        assert behavior["postconditions"] == ["request is stored"]
        assert behavior["frequency"] == "per request"
        assert behavior["pattern"] == "sequential"
        assert behavior["steps"] == ["Validate", "Persist"]
        assert behavior["source_file"] == "a.py"
        assert behavior["structured_steps"] == [
            {"order": 1, "action": "Validate", "component_ref": "COMP-1"},
            {"order": 2, "action": "Persist", "component_ref": "COMP-1"},
        ]
        assert {tuple(r.values()) for r in parsed["relationships"]} >= {
            ("COMP-1", "CAP-1", "realizes"),
            ("COMP-1", "BEH-1", "traces-to"),
        }

        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.validator import validate_model

        validation = validate_model(_parse_raw(parsed))
        assert not [issue for issue in validation.issues if issue.severity == "error"]


class TestMergeRequirements:
    def test_preserves_richer_record_identity_and_only_fills_missing_fields(self):
        poor = {
            "id": "REQ-legacy",
            "name": "A much longer legacy display name for timeout",
            "text": "System must respect TIMEOUT = 30",
            "source_file": "config.py",
            "extensions": {"source_type": "constant:TIMEOUT=30", "legacy": True},
        }
        rich = {
            "id": "REQ-rich",
            "name": "TIMEOUT constraint",
            "status": "ACTIVE",
            "text": "System must respect TIMEOUT = 30",
            "source_file": "config.py",
            "rationale": "Architectural rationale",
            "moe": "Measure timeout",
            "moes": ["Measure timeout"],
            "value_function": "V(actual) = min(1, 30 / max(actual, 1e-9))",
            "extensions": {"source_type": "constant"},
        }

        merged = _merge_requirements([poor], [rich])

        assert len(merged) == 1
        assert merged[0]["id"] == "REQ-rich"
        assert merged[0]["name"] == "TIMEOUT constraint"
        assert merged[0]["extensions"] == {"source_type": "constant", "legacy": True}

    def test_renames_colliding_ids_deterministically(self):
        first = {
            "id": "REQ-C1",
            "name": "TIMEOUT",
            "text": "Timeout 30",
            "source_file": "a.py",
        }
        second = {
            "id": "REQ-C1",
            "name": "MIN_WORKERS",
            "text": "Workers 4",
            "source_file": "b.py",
        }

        merged = _merge_requirements([first], [second])

        assert len({req["id"] for req in merged}) == 2
        assert merged[0]["id"] == "REQ-C1"
        assert merged[1]["id"].startswith("REQ-C1-")


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
            infer=_stage_result(
                _FakeInferOutput(actors=[_FakeCapability(id="ACT-1", name="User")])
            ),
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
        assert sos_parsed["relationships"][0]["from"] == "sys-core"

    def test_no_coordinator_diagnostic(self, tmp_path):
        stage = SynthesizeStage()
        decompose = DecomposeResult(
            systems=[
                SystemBoundary(
                    system_id="S1", name="A", files=["a.py"] * 10, is_full_system=True
                )
            ]
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
    def test_scoped_runs_receive_only_boundary_corrections_and_provenance(self, tmp_path):
        coordinator = MockCoordinator()
        boundaries = [
            SystemBoundary(
                system_id="SYS-a", name="Alpha", files=["alpha/workflow.py"],
                is_full_system=True,
            ),
            SystemBoundary(
                system_id="SYS-b", name="Beta", files=["beta/workflow.py"],
                is_full_system=True,
            ),
        ]
        ctx = _make_ctx(
            tmp_path,
            decompose=_stage_result(DecomposeResult(systems=boundaries)),
            observe=_stage_result(_FakeObserveOutput()),
            infer=_stage_result(_FakeInferOutput()),
            allocate=_stage_result(_FakeAllocOutput()),
            relate=_stage_result(_FakeRelateOutput()),
        )
        ctx.run_id = "parent-run"
        ctx.prior_corrections = [
            Evidence("llm_analysis", 0.9, "alpha flow", "complex_behavior", {
                "resolution_id": "res-alpha",
            }),
            Evidence("llm_analysis", 0.9, "beta flow", "complex_behavior", {
                "resolution_id": "res-beta",
                "file_allocations": {"beta/workflow.py": "COMP-beta"},
            }),
            Evidence("user_correction", 1.0, "shared convention", "complex_behavior", {
                "resolution_id": "res-shared", "shared": True,
            }),
        ]
        ctx.llm_calls = [
            LLMCallRecord("infer", "alpha", resolution_id="res-alpha", files_sent=["alpha/workflow.py"]),
            LLMCallRecord("infer", "beta", resolution_id="res-beta", files_sent=["beta/workflow.py"]),
            LLMCallRecord("infer", "shared", resolution_id="res-shared"),
            LLMCallRecord("infer", "unrelated", resolution_id="res-other", files_sent=["other.py"]),
        ]
        ctx.config["coordinator"] = coordinator

        SynthesizeStage().run(ctx)

        scoped = {sub_ctx.scope: sub_ctx for sub_ctx in coordinator.contexts}
        assert [item.raw for item in scoped["SYS-a"].prior_corrections] == [
            "alpha flow", "shared convention",
        ]
        assert [item.raw for item in scoped["SYS-b"].prior_corrections] == [
            "beta flow", "shared convention",
        ]
        assert {call.resolution_id for call in scoped["SYS-a"].llm_calls} == {
            "res-alpha", "res-shared",
        }
        assert {call.resolution_id for call in scoped["SYS-b"].llm_calls} == {
            "res-beta", "res-shared",
        }
        assert all(sub_ctx.parent_run_id == "parent-run" for sub_ctx in scoped.values())
        assert all(sub_ctx.invocation == "synthesize" for sub_ctx in scoped.values())

    def test_scoped_runs(self, tmp_path):
        sub_results = {
            "observe": _stage_result(_FakeObserveOutput(modules=[_FakeModule()])),
            "infer": _stage_result(_FakeInferOutput(capabilities=[_FakeCapability()])),
            "allocate": _stage_result(_FakeAllocOutput(components=[_FakeComponent()])),
            "relate": _stage_result(
                _FakeRelateOutput(relationships=[_FakeRelationship()])
            ),
        }
        coordinator = MockCoordinator(results=sub_results)

        decompose = DecomposeResult(
            systems=[
                SystemBoundary(
                    system_id="SYS-a",
                    name="Alpha",
                    files=[f"f{i}.py" for i in range(10)],
                    is_full_system=True,
                ),
                SystemBoundary(
                    system_id="SYS-b",
                    name="Beta",
                    files=["x.py", "y.py"],
                    is_full_system=True,
                ),
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

        # Every full system gets validate as last stage
        beta_call = [c for c in coordinator.calls if c[1] == "SYS-b"][0]
        assert beta_call[0] == "validate"

        # System models have YAML
        for sm in synth.system_models:
            assert sm.model_yaml != ""
            assert sm.pipeline_report_md != ""

    def test_inline_components_no_scoped_run(self, tmp_path):
        coordinator = MockCoordinator()
        decompose = DecomposeResult(
            inline_components=[
                SystemBoundary(
                    system_id="SYS-utils",
                    name="Utils",
                    files=["u.py"],
                    is_full_system=False,
                ),
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
        assert result.output.system_models == []
        parsed = yaml.safe_load(result.output.sos_model_yaml)
        assert parsed["entities"]["components"][0]["name"] == "Utils"


# ---------------------------------------------------------------------------
# SoS model structure
# ---------------------------------------------------------------------------


class TestSoSModel:
    def test_inline_projections_merge_with_collision_safe_references(self):
        inline_a = SystemBoundary(
            system_id="COMP-a", name="Inline A", files=["inline_a.py"],
            is_full_system=False,
        )
        inline_b = SystemBoundary(
            system_id="COMP-b", name="Inline B", files=["inline_b.py"],
            is_full_system=False,
        )
        top_results = {
            "allocate": _stage_result(_FakeAllocOutput([
                _FakeComponent("COMP A", "Inline A worker", ["inline_a.py"]),
                _FakeComponent("COMP-A", "Inline B worker", ["inline_b.py"]),
                _FakeComponent("COMP-9", "Subsystem internal", ["system/core.py"]),
            ])),
            "infer": _stage_result(_FakeInferOutput(
                capabilities=[
                    _FakeCapability("CAP A", "Inline A cap", source_files=["inline_a.py"]),
                    _FakeCapability("CAP-A", "Inline B cap", source_files=["inline_b.py"]),
                    _FakeCapability("CAP-9", "Internal cap", source_files=["system/core.py"]),
                ],
                behaviors=[
                    _FakeBehavior("BEH A", "Inline A flow", source_file="inline_a.py", capability_id="CAP A"),
                    _FakeBehavior("BEH-A", "Inline B flow", source_file="inline_b.py", capability_id="CAP-A"),
                    _FakeBehavior("BEH-9", "Internal flow", source_file="system/core.py", capability_id="CAP-9"),
                ],
            )),
            "specify": _stage_result(_FakeSpecifyOutput(
                interfaces=[
                    _FakeInterface("IF A", "A API", "COMP A"),
                    _FakeInterface("IF-A", "B API", "COMP-A"),
                ],
                requirements=[
                    _FakeRequirement("REQ A", "A LIMIT", "inline_a.py"),
                    _FakeRequirement("REQ-A", "B LIMIT", "inline_b.py"),
                ],
            )),
            "relate": _stage_result(_FakeRelateOutput()),
        }

        parsed = yaml.safe_load(_build_sos_model(
            [SystemModel("SYS-core", "Core", "meta: {}")],
            [inline_a, inline_b],
            DecomposeResult(),
            top_results,
            project_name="demo",
        ).model_yaml)

        assert {item["name"] for item in parsed["entities"]["components"]} == {
            "Inline A worker", "Inline B worker",
        }
        assert {item["name"] for item in parsed["entities"]["capabilities"]} == {
            "Inline A cap", "Inline B cap",
        }
        assert {item["name"] for item in parsed["entities"]["behaviors"]} == {
            "Inline A flow", "Inline B flow",
        }
        all_ids = [
            entity["id"] for group in parsed["entities"].values()
            for entity in group if entity.get("id")
        ]
        assert len(all_ids) == len(set(all_ids)), {
            group: [entity.get("id") for entity in entities]
            for group, entities in parsed["entities"].items()
        }
        entity_ids = set(all_ids)
        assert all(
            relationship["from"] in entity_ids and relationship["to"] in entity_ids
            for relationship in parsed["relationships"]
        )
        assert all(
            step["component_ref"] in entity_ids
            for behavior in parsed["entities"]["behaviors"]
            for step in behavior["structured_steps"]
        )
        assert "Subsystem internal" not in str(parsed)
        assert "Internal cap" not in str(parsed)

    def test_slug_allocation_is_globally_unique_for_adversarial_generated_name(self):
        from architecture_model.pipeline.synthesize import _system_slugs
        import hashlib

        first_suffix = hashlib.sha256(b"SYS-1").hexdigest()[:8]
        systems = [
            SystemModel(system_id="SYS-1", name="A B", model_yaml="x"),
            SystemModel(system_id="SYS-2", name="A-B", model_yaml="x"),
            SystemModel(system_id="SYS-3", name=f"A-B-{first_suffix}", model_yaml="x"),
            SystemModel(system_id="SYS-4", name="A B", model_yaml="x"),
        ]

        forward = _system_slugs(systems)
        reverse = _system_slugs(list(reversed(systems)))

        assert len(set(forward.values())) == len(systems)
        assert forward == reverse
        assert set(forward) == {system.system_id for system in systems}

    def test_normalized_slug_collisions_get_distinct_stable_model_refs(self):
        systems = [
            SystemModel(system_id="SYS-1", name="A B", model_yaml="meta: {}"),
            SystemModel(system_id="SYS-2", name="A-B", model_yaml="meta: {}"),
        ]

        first = yaml.safe_load(_build_sos_model(systems, [], DecomposeResult(), {}).model_yaml)
        second = yaml.safe_load(_build_sos_model(systems, [], DecomposeResult(), {}).model_yaml)
        refs = [system["sub_model_ref"] for system in first["entities"]["systems"]]

        assert len(set(refs)) == 2
        assert refs == [system["sub_model_ref"] for system in second["entities"]["systems"]]
        assert all(ref.startswith(".architecture-models/a-b-") for ref in refs)
    def test_inter_system_edges(self):
        systems = [
            SystemModel(system_id="SYS-a", name="A", model_yaml="meta: {}"),
            SystemModel(system_id="SYS-b", name="B", model_yaml="meta: {}"),
        ]
        decompose = DecomposeResult(
            inter_system_edges=[("SYS-a", "SYS-b", "depends-on")]
        )
        sos = _build_sos_model(systems, [], decompose, {})
        assert len(sos.inter_system_interfaces) == 1
        assert sos.inter_system_interfaces[0]["from"] == "sys-a"

        parsed = yaml.safe_load(sos.model_yaml)
        assert parsed["meta"]["system_of_systems"] is True
        assert len(parsed["entities"]["systems"]) == 2

    def test_actors_from_infer(self):
        infer_out = _FakeInferOutput(actors=[_FakeCapability(id="ACT-1", name="Admin")])
        top_results = {"infer": _stage_result(infer_out)}
        sos = _build_sos_model([], [], DecomposeResult(), top_results)
        assert len(sos.actors) == 1
        assert sos.actors[0]["name"] == "Admin"

    def test_top_model_references_systems_and_keeps_inline_details_only(self):
        subsystem_yaml = yaml.safe_dump({
            "meta": {"project": "demo", "schema_version": "2.0"},
            "entities": {
                "components": [{"id": "COMP-1", "name": "Internal"}],
                "capabilities": [{"id": "CAP-1", "name": "Internal cap"}],
                "behaviors": [{"id": "BEH-1", "name": "Internal flow"}],
            },
            "relationships": [],
        })
        systems = [
            SystemModel(system_id="SYS-a", name="Alpha", model_yaml=subsystem_yaml),
            SystemModel(system_id="SYS-b", name="Beta", model_yaml=subsystem_yaml),
        ]
        inline = SystemBoundary(
            system_id="COMP-inline", name="Inline", files=["inline.py"],
            component_ids=["COMP-9"], is_full_system=False,
        )

        parsed = yaml.safe_load(_build_sos_model(
            systems, [inline], DecomposeResult(), {}, project_name="demo"
        ).model_yaml)

        assert parsed["meta"]["project"] == "demo"
        assert parsed["meta"]["source_artifacts"] == [
            ".architecture-models/alpha/.architecture-model.yaml",
            ".architecture-models/beta/.architecture-model.yaml",
            "inline.py",
        ]
        assert [system["id"] for system in parsed["entities"]["systems"]] == [
            "sys-a", "sys-b"
        ]
        assert all(system.get("sub_model_ref") for system in parsed["entities"]["systems"])
        assert parsed["entities"]["components"] == [{
            "id": "comp-inline", "name": "Inline", "status": "ACTIVE",
            "files": ["inline.py"],
        }]
        assert "capabilities" not in parsed["entities"]
        assert "behaviors" not in parsed["entities"]
        assert "layers" not in parsed["entities"]
        assert "requirements" not in parsed["entities"]


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
