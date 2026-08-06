"""Tests for create_behaviors_from_manifest."""
import pytest
from architecture_model.core.types import (
    ArchitectureModel, Component, Entities, ModelMeta, Status, Behavior, Relationship,
)
from architecture_model.manifest.types import FunctionInfo, Manifest, MetricsResult, ModuleInfo, ModuleStatus
from architecture_model.orchestration.auto_enrich import create_behaviors_from_manifest


def _make_mod(file, name, functions, imports=None, line_count=50):
    return ModuleInfo(
        file=file,
        name=name,
        docstring=None,
        functions=functions,
        imports=imports or [],
        line_count=line_count,
        status=ModuleStatus.ACTIVE,
        classes=[],
    )


def _make_func(name, calls=None, raises=None):
    return FunctionInfo(name=name, signature=f"def {name}()", calls=calls or [], raises=raises or [])


def _make_manifest(modules, interfaces=None):
    from datetime import datetime
    return Manifest(
        modules=modules,
        interfaces=interfaces or [],
        functional_blocks={},
        generated_at=datetime.now().isoformat(),
        project_root="/tmp/test",
        metrics=MetricsResult(),
    )


def _make_model(components):
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.3", project="test"),
        entities=Entities(components=components),
        relationships=[],
    )


class TestCreateBehaviors:
    def test_creates_from_router_module(self):
        mods = [
            _make_mod(
                "app/routers/logs.py", "Logs router",
                [_make_func("create_log", ["log_pipeline.process"]), _make_func("list_logs")],
            ),
        ]
        model = _make_model([
            Component(id="COMP-1", name="Routers", status=Status.ACTIVE, files=["app/routers/logs.py"]),
        ])
        manifest = _make_manifest(mods)

        behaviors, rels = create_behaviors_from_manifest(model, manifest)

        assert len(behaviors) == 2
        assert behaviors[0].name == "create_log"
        assert "POST" in behaviors[0].trigger
        assert behaviors[1].name == "list_logs"
        assert "GET" in behaviors[1].trigger

    def test_creates_from_service_module(self):
        mods = [
            _make_mod(
                "app/services/log_pipeline.py", "Pipeline",
                [_make_func("process_log", ["classify", "extract_actions", "normalize", "persist", "notify"])],
                line_count=100,
            ),
        ]
        model = _make_model([
            Component(id="COMP-2", name="Pipeline", status=Status.ACTIVE, files=["app/services/log_pipeline.py"]),
        ])
        manifest = _make_manifest(mods)

        behaviors, rels = create_behaviors_from_manifest(model, manifest)

        assert len(behaviors) == 1
        assert behaviors[0].name == "process_log"
        assert behaviors[0].steps == ["classify", "extract_actions", "normalize", "persist", "notify"]

    def test_maps_cross_component_relationships(self):
        mods = [
            _make_mod("app/routers/logs.py", "Logs router", [_make_func("create_log")]),
            _make_mod("app/models/log.py", "Log model", []),
        ]
        interfaces = [type("I", (), {"source": "app/routers/logs.py", "target": "app/models/log.py", "import_path": "app.models.log"})()]
        model = _make_model([
            Component(id="COMP-1", name="Routers", status=Status.ACTIVE, files=["app/routers/logs.py"]),
            Component(id="COMP-2", name="Models", status=Status.ACTIVE, files=["app/models/log.py"]),
        ])
        manifest = _make_manifest(mods, interfaces)

        behaviors, rels = create_behaviors_from_manifest(model, manifest)

        assert len(behaviors) == 1
        rel_comps = {r.from_id for r in rels}
        assert "COMP-1" in rel_comps
        assert "COMP-2" in rel_comps

    def test_skips_init_files(self):
        mods = [
            _make_mod("app/routers/__init__.py", "init", [_make_func("setup")]),
        ]
        model = _make_model([
            Component(id="COMP-1", name="Routers", status=Status.ACTIVE, files=["app/routers/__init__.py"]),
        ])
        manifest = _make_manifest(mods)

        behaviors, rels = create_behaviors_from_manifest(model, manifest)
        assert len(behaviors) == 0

    def test_skips_private_functions(self):
        mods = [
            _make_mod("app/services/helper.py", "Helper", [
                _make_func("_internal"),
                _make_func("public_func", ["step1", "step2", "step3", "step4", "step5"]),
            ]),
        ]
        model = _make_model([
            Component(id="COMP-1", name="Services", status=Status.ACTIVE, files=["app/services/helper.py"]),
        ])
        manifest = _make_manifest(mods)

        behaviors, rels = create_behaviors_from_manifest(model, manifest)
        assert len(behaviors) == 1
        assert behaviors[0].name == "public_func"

    def test_empty_manifest(self):
        model = _make_model([
            Component(id="COMP-1", name="X", status=Status.ACTIVE, files=["src/x.py"]),
        ])
        manifest = _make_manifest([])

        behaviors, rels = create_behaviors_from_manifest(model, manifest)
        assert behaviors == []
        assert rels == []

    def test_http_trigger_inference(self):
        from architecture_model.orchestration.auto_enrich import _infer_http_trigger
        assert "POST" in _infer_http_trigger("create_log", "app/routers/logs.py")
        assert "GET" in _infer_http_trigger("list_logs", "app/routers/logs.py")
        assert "GET" in _infer_http_trigger("get_log", "app/routers/logs.py")
        assert "PATCH" in _infer_http_trigger("update_log", "app/routers/logs.py")
        assert "DELETE" in _infer_http_trigger("delete_log", "app/routers/logs.py")
        assert "POST" in _infer_http_trigger("approve_patch", "app/routers/artifact_patches.py")
