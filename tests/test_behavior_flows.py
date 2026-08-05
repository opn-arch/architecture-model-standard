"""Tests for behavior flow filtering, grouping, scoped manifests & sub-models."""

import pytest
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel, Behavior, Component, Entities, Interface,
    InterfaceType, ModelMeta, Relationship, RelationType, Status,
)
from architecture_model.manifest.call_graph import CallGraph, FlowTrace
from architecture_model.manifest.types import (
    FunctionInfo, InterfaceEdge, Manifest, MetricsResult, ModuleInfo, ModuleStatus,
)
from architecture_model.orchestration.behavior_flows import (
    BehaviorClassification, CrudSummary,
    build_behavior_manifest, build_behavior_sub_model,
    build_file_to_comp, classify_behaviors, summarize_crud_group,
)


def _make_behavior(id, name, steps=None, trigger="", source_file=None):
    return Behavior(id=id, name=name, status=Status.ACTIVE, steps=steps or [], trigger=trigger, source_file=source_file)


def _make_component(id, name, files=None):
    return Component(id=id, name=name, status=Status.ACTIVE, files=files or [])


def _make_module(file, name, functions=None):
    return ModuleInfo(
        file=file, name=name, docstring=None,
        functions=functions or [], imports=[], line_count=10,
        status=ModuleStatus.ACTIVE, classes=[],
    )


def _make_manifest(modules=None, interfaces=None):
    return Manifest(
        modules=modules or [], interfaces=interfaces or [],
        functional_blocks={}, generated_at="", project_root=".",
        metrics=MetricsResult(values={}),
    )


def _make_model(components=None, behaviors=None, relationships=None, interfaces=None):
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(
            components=components or [],
            behaviors=behaviors or [],
            interfaces=interfaces or [],
        ),
        relationships=relationships or [],
    )


class TestClassifyBehaviors:
    def test_classify_trivial(self):
        """Behavior with 0 steps -> trivial."""
        beh = _make_behavior("BEH-1", "noop", steps=[])
        call_graph = CallGraph()
        result = classify_behaviors([beh], [], call_graph, {})
        assert beh in result.trivial
        assert len(result.cross_component) == 0
        assert len(result.crud_groups) == 0

    def test_classify_single_component(self):
        """Behavior whose flow stays in one component -> CRUD group."""
        beh = _make_behavior("BEH-1", "get_user", steps=["step1", "step2"], source_file="src/auth.py")
        # Call graph with entry that stays in one file
        call_graph = CallGraph(
            edges={"src/auth.py:get_user": ["src/auth.py:helper"]},
            functions={"src/auth.py:get_user": FunctionInfo(name="get_user", signature="()", calls=["helper"]),
                       "src/auth.py:helper": FunctionInfo(name="helper", signature="()", calls=[])},
            locations={"src/auth.py:get_user": "src/auth.py", "src/auth.py:helper": "src/auth.py"},
        )
        file_to_comp = {"src/auth.py": "COMP-1"}
        result = classify_behaviors([beh], [], call_graph, file_to_comp)
        assert len(result.cross_component) == 0
        assert "COMP-1" in result.crud_groups
        assert beh in result.crud_groups["COMP-1"]

    def test_classify_cross_component(self):
        """Behavior crossing 2 components -> cross_component."""
        beh = _make_behavior("BEH-1", "login", steps=["s1", "s2"], source_file="src/auth.py")
        call_graph = CallGraph(
            edges={"src/auth.py:login": ["src/db.py:save"]},
            functions={"src/auth.py:login": FunctionInfo(name="login", signature="()", calls=["save"]),
                       "src/db.py:save": FunctionInfo(name="save", signature="()", calls=[])},
            locations={"src/auth.py:login": "src/auth.py", "src/db.py:save": "src/db.py"},
        )
        file_to_comp = {"src/auth.py": "COMP-1", "src/db.py": "COMP-2"}
        result = classify_behaviors([beh], [], call_graph, file_to_comp)
        assert len(result.cross_component) == 1
        assert result.cross_component[0][0] == beh

    def test_classify_many_steps_single_component(self):
        """Behavior with 4+ steps but single component -> CRUD group (not cross-component)."""
        beh = _make_behavior("BEH-1", "complex", steps=["s1", "s2", "s3", "s4"], source_file="src/a.py")
        call_graph = CallGraph(
            edges={"src/a.py:complex": []},
            functions={"src/a.py:complex": FunctionInfo(name="complex", signature="()", calls=[])},
            locations={"src/a.py:complex": "src/a.py"},
        )
        file_to_comp = {"src/a.py": "COMP-1"}
        result = classify_behaviors([beh], [], call_graph, file_to_comp)
        assert len(result.cross_component) == 0
        assert "COMP-1" in result.crud_groups


class TestSummarizeCrudGroup:
    def test_summarize_crud_group(self):
        """Groups by HTTP verb from triggers."""
        behaviors = [
            _make_behavior("B1", "list_users", trigger="GET /users"),
            _make_behavior("B2", "get_user", trigger="GET /users/{id}"),
            _make_behavior("B3", "create_user", trigger="POST /users"),
        ]
        result = summarize_crud_group("COMP-1", behaviors)
        assert result.component_id == "COMP-1"
        assert result.count == 3
        assert result.verbs["GET"] == 2
        assert result.verbs["POST"] == 1
        assert "3 CRUD" in result.summary


class TestBuildBehaviorManifest:
    def test_build_behavior_manifest(self):
        """Scoped manifest has only touched modules."""
        mod1 = _make_module("src/auth.py", "auth", [FunctionInfo(name="login", signature="()", calls=[])])
        mod2 = _make_module("src/db.py", "db", [FunctionInfo(name="save", signature="()", calls=[])])
        mod3 = _make_module("src/unrelated.py", "unrelated")
        manifest = _make_manifest(modules=[mod1, mod2, mod3])

        flow = FlowTrace(entry="src/auth.py:login", steps=[("src/auth.py", "login"), ("src/db.py", "save")],
                         components_crossed=["COMP-1", "COMP-2"], depth=1, truncated=False)
        beh = _make_behavior("BEH-1", "login")

        result = build_behavior_manifest(beh, flow, manifest)
        assert len(result.modules) == 2
        assert {m.file for m in result.modules} == {"src/auth.py", "src/db.py"}

    def test_build_behavior_manifest_preserves_functions(self):
        """Full function detail preserved in scoped manifest."""
        func = FunctionInfo(name="login", signature="(user, pw)", calls=["validate", "save"])
        mod = _make_module("src/auth.py", "auth", [func])
        manifest = _make_manifest(modules=[mod])
        flow = FlowTrace(entry="src/auth.py:login", steps=[("src/auth.py", "login")],
                         components_crossed=["COMP-1"], depth=0, truncated=False)
        beh = _make_behavior("BEH-1", "login")

        result = build_behavior_manifest(beh, flow, manifest)
        assert result.modules[0].functions[0].calls == ["validate", "save"]


class TestBuildBehaviorSubModel:
    def test_build_behavior_sub_model_components(self):
        """Only touched components included."""
        comp1 = _make_component("COMP-1", "Auth", files=["src/auth.py"])
        comp2 = _make_component("COMP-2", "DB", files=["src/db.py"])
        comp3 = _make_component("COMP-3", "Unrelated", files=["src/other.py"])
        beh = _make_behavior("BEH-1", "login")
        model = _make_model(components=[comp1, comp2, comp3], behaviors=[beh])

        flow = FlowTrace(entry="src/auth.py:login", steps=[("src/auth.py", "login"), ("src/db.py", "save")],
                         components_crossed=["COMP-1", "COMP-2"], depth=1, truncated=False)
        file_to_comp = {"src/auth.py": "COMP-1", "src/db.py": "COMP-2"}

        result = build_behavior_sub_model(beh, flow, model, file_to_comp)
        comp_ids = {c.id for c in result.entities.components}
        assert comp_ids == {"COMP-1", "COMP-2"}

    def test_build_behavior_sub_model_relationships(self):
        """Only relevant relationships included."""
        comp1 = _make_component("COMP-1", "Auth")
        comp2 = _make_component("COMP-2", "DB")
        beh = _make_behavior("BEH-1", "login")
        rels = [
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON),
            Relationship(from_id="COMP-1", to_id="COMP-3", type=RelationType.DEPENDS_ON),  # unrelated
        ]
        model = _make_model(components=[comp1, comp2], behaviors=[beh], relationships=rels)

        flow = FlowTrace(entry="src/auth.py:login", steps=[("src/auth.py", "login"), ("src/db.py", "save")],
                         components_crossed=["COMP-1", "COMP-2"], depth=1, truncated=False)
        file_to_comp = {"src/auth.py": "COMP-1", "src/db.py": "COMP-2"}

        result = build_behavior_sub_model(beh, flow, model, file_to_comp)
        # Should have the COMP-1->COMP-2 rel + a realizes rel for the behavior
        assert any(r.from_id == "COMP-1" and r.to_id == "COMP-2" for r in result.relationships)
        assert not any(r.to_id == "COMP-3" for r in result.relationships)

    def test_build_behavior_sub_model_meta(self):
        """meta.refines_behavior set correctly."""
        beh = _make_behavior("BEH-1", "login")
        model = _make_model(components=[_make_component("COMP-1", "Auth")], behaviors=[beh])
        flow = FlowTrace(entry="src/auth.py:login", steps=[("src/auth.py", "login")],
                         components_crossed=["COMP-1"], depth=0, truncated=False)

        result = build_behavior_sub_model(beh, flow, model, {"src/auth.py": "COMP-1"})
        assert result.meta.refines_behavior == "BEH-1"


class TestBuildFileToComp:
    def test_build_file_to_comp(self):
        """Basic file to component mapping from component.files."""
        comp1 = _make_component("COMP-1", "Auth", files=["src/auth.py", "src/auth_utils.py"])
        comp2 = _make_component("COMP-2", "DB", files=["src/db.py"])
        model = _make_model(components=[comp1, comp2])
        manifest = _make_manifest(modules=[
            _make_module("src/auth.py", "auth"),
            _make_module("src/auth_utils.py", "auth_utils"),
            _make_module("src/db.py", "db"),
        ])

        result = build_file_to_comp(model, manifest)
        assert result["src/auth.py"] == "COMP-1"
        assert result["src/auth_utils.py"] == "COMP-1"
        assert result["src/db.py"] == "COMP-2"
