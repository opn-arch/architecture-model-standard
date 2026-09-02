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


@dataclass
class _FakeCapability:
    id: str = "CAP-1"
    name: str = "TestCap"
    description: str = ""
    intent: str = ""
    goals: list[str] = field(default_factory=list)


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

    def test_top_model_references_systems_and_keeps_inline_components_only(self):
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
