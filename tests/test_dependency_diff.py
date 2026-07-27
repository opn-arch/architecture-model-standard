"""Tests for F-block dependency diff coverage check."""
from architecture_model.core.coverage import _check_dependency_accuracy
from architecture_model.core.types import (
    ArchitectureModel, Component, Entities, ModelMeta, Relationship, RelationType, Status,
)


def _model_with_deps(deps: list[tuple[str, str]], components: list[Component]):
    rels = [Relationship(from_id=f, to_id=t, type=RelationType.DEPENDS_ON) for f, t in deps]
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(components=components),
        relationships=rels,
    )


def test_perfect_match():
    comps = [
        Component(id="COMP-A", name="A", f_block="F1", status=Status.ACTIVE),
        Component(id="COMP-B", name="B", f_block="F2", status=Status.ACTIVE),
    ]
    model = _model_with_deps([("COMP-A", "COMP-B")], comps)
    import_deps = {"F1": {"F2"}}
    check = _check_dependency_accuracy(model, import_deps)
    assert check.score == 100.0


def test_missing_from_model():
    comps = [
        Component(id="COMP-A", name="A", f_block="F1", status=Status.ACTIVE),
        Component(id="COMP-B", name="B", f_block="F2", status=Status.ACTIVE),
        Component(id="COMP-C", name="C", f_block="F3", status=Status.ACTIVE),
    ]
    model = _model_with_deps([("COMP-A", "COMP-B")], comps)
    import_deps = {"F1": {"F2", "F3"}}
    check = _check_dependency_accuracy(model, import_deps)
    assert check.score < 100.0
    assert any("F3" in m for m in check.missing)


def test_extra_in_model():
    comps = [
        Component(id="COMP-A", name="A", f_block="F1", status=Status.ACTIVE),
        Component(id="COMP-B", name="B", f_block="F2", status=Status.ACTIVE),
    ]
    model = _model_with_deps([("COMP-A", "COMP-B")], comps)
    import_deps = {}
    check = _check_dependency_accuracy(model, import_deps)
    assert any("F2" in e for e in check.extra)


def test_no_deps_scores_100():
    comps = [Component(id="COMP-A", name="A", f_block="F1", status=Status.ACTIVE)]
    model = _model_with_deps([], comps)
    import_deps = {}
    check = _check_dependency_accuracy(model, import_deps)
    assert check.score == 100.0
