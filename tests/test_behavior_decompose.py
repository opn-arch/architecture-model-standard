"""Tests for structured behavior decomposition."""
import pytest
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Component, Step
)
from architecture_model.orchestration.behavior_decompose import (
    decompose_behavior, decompose_all_behaviors
)
from architecture_model.manifest.types import Manifest, ModuleInfo, FunctionInfo, MetricsResult
from datetime import datetime


def _make_manifest(modules):
    infos = []
    for m in modules:
        infos.append(ModuleInfo(
            file=m["file"], name=m["file"],
            docstring="",
            functions=[FunctionInfo(name=f, signature=f"def {f}()") for f in m.get("functions", [])],
            imports=[], line_count=50, status="active", classes=[]
        ))
    return Manifest(
        modules=infos, interfaces=[],
        functional_blocks={}, generated_at=datetime.now().isoformat(),
        project_root="/tmp/test", metrics=MetricsResult(values={})
    )


class TestDecomposeBehavior:
    def test_maps_steps_to_components(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(components=[
                Component(id="COMP-1", name="API", status="ACTIVE", files=["api/routes.py"]),
                Component(id="COMP-2", name="DB", status="ACTIVE", files=["db/queries.py"]),
            ]),
            relationships=[]
        )
        manifest = _make_manifest([
            {"file": "api/routes.py", "functions": ["validate_input", "format_response"]},
            {"file": "db/queries.py", "functions": ["create_record", "fetch_record"]},
        ])
        beh = Behavior(
            id="BEH-1", name="Create item", status="ACTIVE",
            steps=["validate_input", "create_record", "format_response"]
        )
        result = decompose_behavior(beh, model, manifest)
        assert len(result.structured_steps) == 3
        assert result.structured_steps[0].component_ref == "COMP-1"
        assert result.structured_steps[1].component_ref == "COMP-2"
        assert result.structured_steps[2].component_ref == "COMP-1"

    def test_step_action_is_humanized(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(components=[]),
            relationships=[]
        )
        beh = Behavior(
            id="BEH-1", name="Test", status="ACTIVE",
            steps=["validate_input", "create_record"]
        )
        result = decompose_behavior(beh, model)
        assert result.structured_steps[0].action == "Validate Input"
        assert result.structured_steps[1].action == "Create Record"

    def test_empty_steps_returns_unchanged(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(), relationships=[]
        )
        beh = Behavior(id="BEH-1", name="Test", status="ACTIVE", steps=[])
        result = decompose_behavior(beh, model)
        assert result.structured_steps == []

    def test_decompose_all_behaviors(self):
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(
                components=[Component(id="COMP-1", name="API", status="ACTIVE", files=["api.py"])],
                behaviors=[
                    Behavior(id="BEH-1", name="A", status="ACTIVE", steps=["do_thing"]),
                    Behavior(id="BEH-2", name="B", status="ACTIVE", steps=["other_thing"]),
                ]
            ),
            relationships=[]
        )
        manifest = _make_manifest([{"file": "api.py", "functions": ["do_thing", "other_thing"]}])
        result = decompose_all_behaviors(model, manifest)
        assert all(len(b.structured_steps) > 0 for b in result.entities.behaviors)


class TestStepDataclass:
    def test_step_creation(self):
        step = Step(order=1, action="Validate input", component_ref="COMP-1", actor="system")
        assert step.order == 1
        assert step.action == "Validate input"

    def test_step_defaults(self):
        step = Step()
        assert step.order == 0
        assert step.action == ""
        assert step.component_ref == ""


class TestParserRoundtrip:
    def test_structured_steps_serialize_deserialize(self, tmp_path):
        from architecture_model.core.parser import save_model, load_model
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Test", status="ACTIVE",
                         structured_steps=[
                             Step(order=1, action="Do thing", component_ref="COMP-1"),
                             Step(order=2, action="Other thing", actor="user"),
                         ])
            ]),
            relationships=[]
        )
        path = tmp_path / "model.yaml"
        save_model(model, path)
        loaded = load_model(path)
        assert len(loaded.entities.behaviors[0].structured_steps) == 2
        assert loaded.entities.behaviors[0].structured_steps[0].action == "Do thing"
        assert loaded.entities.behaviors[0].structured_steps[0].component_ref == "COMP-1"
        assert loaded.entities.behaviors[0].structured_steps[1].actor == "user"

    def test_plain_steps_still_work(self, tmp_path):
        from architecture_model.core.parser import save_model, load_model
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Test", status="ACTIVE",
                         steps=["step1", "step2"])
            ]),
            relationships=[]
        )
        path = tmp_path / "model.yaml"
        save_model(model, path)
        loaded = load_model(path)
        assert loaded.entities.behaviors[0].steps == ["step1", "step2"]
        assert loaded.entities.behaviors[0].structured_steps == []
