"""Tests for representativeness metric."""

import pytest
from dataclasses import dataclass, field
from architecture_model.core.types import ArchitectureModel, Component, Entities, Relationship
from architecture_model.manifest.types import ModuleInfo, InterfaceEdge
from architecture_model.core.representativeness import compute_representativeness, RepresentativenessResult, HierarchicalRepresentativenessResult


def _model(components=None, relationships=None):
    return ArchitectureModel(
        meta={"project": "test", "schema_version": "1.3"},
        entities=Entities(components=components or []),
        relationships=relationships or [],
    )


def _module(file, line_count=50, functions=None, classes=None):
    fns = functions if functions is not None else ["f"]
    cls = classes if classes is not None else []
    return ModuleInfo(file=file, line_count=line_count, functions=fns, classes=cls, name="mod", docstring="", imports=[], status="active")


def _comp(id, name, files):
    return Component(id=id, name=name, files=files, status="ACTIVE")


def _rel(from_id, to_id, rtype="depends_on"):
    return Relationship(from_id=from_id, to_id=to_id, type=rtype)


def _edge(source, target):
    return InterfaceEdge(source=source, target=target, import_path="x")


class TestFileCoverage:
    def test_perfect_file_coverage(self):
        modules = [_module("a.py"), _module("b.py")]
        model = _model(components=[_comp("C1", "All", ["a.py", "b.py"])])
        r = compute_representativeness(model, modules, [])
        assert r.file_coverage == 100.0

    def test_partial_file_coverage(self):
        modules = [_module("a.py"), _module("b.py")]
        model = _model(components=[_comp("C1", "Half", ["a.py"])])
        r = compute_representativeness(model, modules, [])
        assert r.file_coverage == 50.0
        assert "b.py" in r.uncovered_files

    def test_trivial_files_excluded(self):
        modules = [
            _module("a.py"),
            _module("__init__.py", line_count=3, functions=[], classes=[]),
            _module("__version__.py", line_count=1, functions=[], classes=[]),
            _module("__main__.py", line_count=10, functions=["main"], classes=[]),
        ]
        model = _model(components=[_comp("C1", "A", ["a.py"])])
        r = compute_representativeness(model, modules, [])
        assert r.file_coverage == 100.0

    def test_empty_model_zero_coverage(self):
        modules = [_module("a.py")]
        model = _model(components=[])
        r = compute_representativeness(model, modules, [])
        assert r.file_coverage == 0.0


class TestRelationshipAccuracy:
    def test_all_relationships_verified(self):
        model = _model(
            components=[_comp("C1", "A", ["a.py"]), _comp("C2", "B", ["b.py"])],
            relationships=[_rel("C1", "C2")],
        )
        edges = [_edge("a.py", "b.py")]
        r = compute_representativeness(model, [], edges)
        assert r.relationship_accuracy == 100.0

    def test_unverified_relationship(self):
        model = _model(
            components=[_comp("C1", "A", ["a.py"]), _comp("C2", "B", ["b.py"])],
            relationships=[_rel("C1", "C2")],
        )
        r = compute_representativeness(model, [], [])
        assert r.relationship_accuracy == 0.0
        assert "C1 → C2" in r.unverified_relationships

    def test_no_relationships_is_100(self):
        model = _model(components=[_comp("C1", "A", ["a.py"])])
        r = compute_representativeness(model, [], [])
        assert r.relationship_accuracy == 100.0


class TestBoundaryCoherence:
    def test_perfect_coherence_single_file(self):
        model = _model(components=[_comp("C1", "A", ["a.py"]), _comp("C2", "B", ["b.py"])])
        r = compute_representativeness(model, [], [])
        assert r.boundary_coherence == 100.0

    def test_high_coherence_internal_imports(self):
        # 3-file component with 2 internal, 1 external edge; plus single-file component
        model = _model(components=[
            _comp("C1", "Big", ["a.py", "b.py", "c.py"]),
            _comp("C2", "Small", ["d.py"]),
        ])
        edges = [
            _edge("a.py", "b.py"),  # internal to C1
            _edge("b.py", "c.py"),  # internal to C1
            _edge("a.py", "d.py"),  # external from C1 perspective
        ]
        r = compute_representativeness(model, [], edges)
        # C1: 2/(2+1) = 0.667, C2: single file = 1.0 → avg = 0.833 * 100
        assert abs(r.boundary_coherence - 83.33) < 1.0

    def test_low_coherence_wrong_grouping(self):
        model = _model(components=[_comp("C1", "Bad", ["a.py", "b.py"])])
        edges = [
            _edge("a.py", "x.py"),  # external
            _edge("y.py", "b.py"),  # external
        ]
        r = compute_representativeness(model, [], edges)
        assert r.boundary_coherence == 0.0
        assert "Bad" in r.low_coherence_components


class TestOverall:
    def test_overall_is_average(self):
        # Single-file component covering one module, no relationships
        model = _model(components=[_comp("C1", "A", ["a.py"])])
        modules = [_module("a.py"), _module("b.py")]
        r = compute_representativeness(model, modules, [])
        # file=50%, rel=100%, coherence=100%, behavioral=100% (no complex funcs)
        expected = (50.0 + 100.0 + 100.0 + 100.0) / 4
        assert abs(r.overall - expected) < 0.01

    def test_perfect_model_100(self):
        modules = [_module("a.py"), _module("b.py")]
        model = _model(
            components=[_comp("C1", "A", ["a.py"]), _comp("C2", "B", ["b.py"])],
            relationships=[_rel("C1", "C2")],
        )
        edges = [_edge("a.py", "b.py")]
        r = compute_representativeness(model, modules, edges)
        assert r.overall == 100.0


class TestToDict:
    def test_representativeness_result_to_dict(self):
        r = RepresentativenessResult(
            file_coverage=80.0,
            relationship_accuracy=90.0,
            boundary_coherence=70.0,
            behavioral_coverage=100.0,
            overall=85.0,
            uncovered_files=["x.py"],
            unverified_relationships=["A → B"],
            low_coherence_components=["C1"],
            uncaptured_behaviors=["mod.func"],
        )
        d = r.to_dict()
        assert d["file_coverage"] == 80.0
        assert d["relationship_accuracy"] == 90.0
        assert d["boundary_coherence"] == 70.0
        assert d["behavioral_coverage"] == 100.0
        assert d["overall"] == 85.0
        assert d["uncovered_files"] == ["x.py"]
        assert d["unverified_relationships"] == ["A → B"]
        assert d["low_coherence_components"] == ["C1"]
        assert d["uncaptured_behaviors"] == ["mod.func"]

    def test_hierarchical_result_to_dict(self):
        block_result = RepresentativenessResult(file_coverage=75.0, overall=75.0)
        root_result = RepresentativenessResult(file_coverage=90.0, overall=90.0)
        h = HierarchicalRepresentativenessResult(
            root=root_result,
            blocks={"F1": block_result},
            overall=82.5,
        )
        d = h.to_dict()
        assert d["overall"] == 82.5
        assert d["root"]["file_coverage"] == 90.0
        assert d["blocks"]["F1"]["file_coverage"] == 75.0
        assert d["blocks"]["F1"]["overall"] == 75.0
