"""Tests for :mod:`architecture_model.lifecycle.diff`."""

from __future__ import annotations

import pytest

from architecture_model.core.types import (
    Actor,
    ActorType,
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    Constraint,
    ConstraintType,
    Entities,
    Interface,
    InterfaceType,
    Layer,
    ModelMeta,
    Priority,
    RelationType,
    Relationship,
    Status,
    Strength,
)
from architecture_model.lifecycle.diff import (
    ChildrenDiff,
    EntityKindDiff,
    ManifestDiff,
    RelationshipDiff,
    SemanticDiff,
    semantic_diff,
)


def _empty_model() -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.0", project="test"),
        entities=Entities(),
        relationships=[],
    )


def test_empty_vs_empty_produces_empty_diff() -> None:
    a = _empty_model()
    b = _empty_model()
    d = semantic_diff(a, b)
    assert isinstance(d, SemanticDiff)
    # entities: every kind key present with empty added/removed/changed
    for kind_diff in d.entities.values():
        assert kind_diff.added == []
        assert kind_diff.removed == []
        assert kind_diff.changed == []
    assert d.relationships.added == []
    assert d.relationships.removed == []
    assert d.relationships.changed == []
    assert d.manifest.files_added == []
    assert d.manifest.files_removed == []
    assert d.manifest.symbols_added == []
    assert d.manifest.symbols_removed == []
    assert d.manifest.symbols_signature_changed == []
    assert d.children.added == []
    assert d.children.removed == []
    assert d.children.revision_changed == []
    assert d.git == {"commit_a": None, "commit_b": None}


# --- Entity add/remove/change parametric over 7 kinds ---

def _make_entity(kind: str, id_: str, name: str = "n"):
    if kind == "actors":
        return Actor(id=id_, name=name, status=Status.ACTIVE, type=ActorType.HUMAN)
    if kind == "capabilities":
        return Capability(id=id_, name=name, status=Status.ACTIVE)
    if kind == "behaviors":
        return Behavior(id=id_, name=name, status=Status.ACTIVE)
    if kind == "interfaces":
        return Interface(id=id_, name=name, status=Status.ACTIVE, type=InterfaceType.INTERNAL)
    if kind == "constraints":
        return Constraint(id=id_, name=name, status=Status.ACTIVE, type=ConstraintType.PERFORMANCE)
    if kind == "layers":
        return Layer(id=id_, name=name, status=Status.ACTIVE)
    if kind == "components":
        return Component(id=id_, name=name, status=Status.ACTIVE)
    raise KeyError(kind)


ENTITY_KINDS = [
    "actors",
    "capabilities",
    "behaviors",
    "interfaces",
    "constraints",
    "layers",
    "components",
]


@pytest.mark.parametrize("kind", ENTITY_KINDS)
def test_entity_added(kind: str) -> None:
    a = _empty_model()
    b = _empty_model()
    getattr(b.entities, kind).append(_make_entity(kind, "X-1"))
    d = semantic_diff(a, b)
    assert d.entities[kind].added == ["X-1"]
    assert d.entities[kind].removed == []
    assert d.entities[kind].changed == []


@pytest.mark.parametrize("kind", ENTITY_KINDS)
def test_entity_removed(kind: str) -> None:
    a = _empty_model()
    b = _empty_model()
    getattr(a.entities, kind).append(_make_entity(kind, "X-1"))
    d = semantic_diff(a, b)
    assert d.entities[kind].removed == ["X-1"]
    assert d.entities[kind].added == []


@pytest.mark.parametrize("kind", ENTITY_KINDS)
def test_entity_name_changed(kind: str) -> None:
    a = _empty_model()
    b = _empty_model()
    getattr(a.entities, kind).append(_make_entity(kind, "X-1", name="old"))
    getattr(b.entities, kind).append(_make_entity(kind, "X-1", name="new"))
    d = semantic_diff(a, b)
    assert d.entities[kind].added == []
    assert d.entities[kind].removed == []
    fc = [c for c in d.entities[kind].changed if c["field"] == "name"]
    assert fc == [{"id": "X-1", "field": "name", "old": "old", "new": "new"}]


def test_entity_status_change_shows_enum_value() -> None:
    a = _empty_model()
    b = _empty_model()
    a.entities.components.append(Component(id="C-1", name="c", status=Status.ACTIVE))
    b.entities.components.append(Component(id="C-1", name="c", status=Status.DEPRECATED))
    d = semantic_diff(a, b)
    changes = d.entities["components"].changed
    assert {"id": "C-1", "field": "status", "old": "ACTIVE", "new": "DEPRECATED"} in changes


def test_entity_deterministic_ordering_of_added() -> None:
    a = _empty_model()
    b = _empty_model()
    for cid in ["C-3", "C-1", "C-2"]:
        b.entities.components.append(Component(id=cid, name="n", status=Status.ACTIVE))
    d = semantic_diff(a, b)
    assert d.entities["components"].added == ["C-1", "C-2", "C-3"]


# --- Relationships ---

REL_TYPES = [
    RelationType.REALIZES,
    RelationType.CONTAINS,
    RelationType.DEPENDS_ON,
    RelationType.EXPOSES,
    RelationType.CONSUMES,
    RelationType.TRIGGERS,
]


@pytest.mark.parametrize("rt", REL_TYPES)
def test_relationship_added(rt: RelationType) -> None:
    a = _empty_model()
    b = _empty_model()
    b.relationships.append(Relationship(type=rt, from_id="A", to_id="B"))
    d = semantic_diff(a, b)
    assert d.relationships.added == [{"from": "A", "to": "B", "type": rt.value}]
    assert d.relationships.removed == []


@pytest.mark.parametrize("rt", REL_TYPES)
def test_relationship_removed(rt: RelationType) -> None:
    a = _empty_model()
    b = _empty_model()
    a.relationships.append(Relationship(type=rt, from_id="A", to_id="B"))
    d = semantic_diff(a, b)
    assert d.relationships.removed == [{"from": "A", "to": "B", "type": rt.value}]


def test_relationship_attr_change_is_changed_not_add_remove() -> None:
    a = _empty_model()
    b = _empty_model()
    a.relationships.append(
        Relationship(type=RelationType.REALIZES, from_id="A", to_id="B", description="old")
    )
    b.relationships.append(
        Relationship(type=RelationType.REALIZES, from_id="A", to_id="B", description="new")
    )
    d = semantic_diff(a, b)
    assert d.relationships.added == []
    assert d.relationships.removed == []
    assert d.relationships.changed == [
        {"from": "A", "to": "B", "type": "realizes", "field": "description", "old": "old", "new": "new"}
    ]


def test_relationship_strength_change_detected() -> None:
    a = _empty_model()
    b = _empty_model()
    a.relationships.append(
        Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="B", strength=Strength.WEAK)
    )
    b.relationships.append(
        Relationship(type=RelationType.DEPENDS_ON, from_id="A", to_id="B", strength=Strength.STRONG)
    )
    d = semantic_diff(a, b)
    fields = {c["field"] for c in d.relationships.changed}
    assert "strength" in fields


def test_relationship_deterministic_ordering() -> None:
    a = _empty_model()
    b = _empty_model()
    for f, t in [("Z", "A"), ("A", "B"), ("A", "A")]:
        b.relationships.append(Relationship(type=RelationType.REALIZES, from_id=f, to_id=t))
    d = semantic_diff(a, b)
    assert [(r["from"], r["to"]) for r in d.relationships.added] == [
        ("A", "A"),
        ("A", "B"),
        ("Z", "A"),
    ]


# --- Manifest ---

def test_manifest_files_added_removed() -> None:
    a = _empty_model()
    b = _empty_model()
    m_a = {"files": ["x.py", "y.py"], "symbols": []}
    m_b = {"files": ["y.py", "z.py"], "symbols": []}
    d = semantic_diff(a, b, manifest_a=m_a, manifest_b=m_b)
    assert d.manifest.files_added == ["z.py"]
    assert d.manifest.files_removed == ["x.py"]


def test_manifest_symbols_add_remove_signature_change() -> None:
    a = _empty_model()
    b = _empty_model()
    m_a = {
        "files": [],
        "symbols": [
            {"name": "pkg.foo", "signature": "(x)->int"},
            {"name": "pkg.bar", "signature": "()->None"},
        ],
    }
    m_b = {
        "files": [],
        "symbols": [
            {"name": "pkg.foo", "signature": "(x, y)->int"},
            {"name": "pkg.baz", "signature": "()->str"},
        ],
    }
    d = semantic_diff(a, b, manifest_a=m_a, manifest_b=m_b)
    assert d.manifest.symbols_added == ["pkg.baz"]
    assert d.manifest.symbols_removed == ["pkg.bar"]
    assert d.manifest.symbols_signature_changed == ["pkg.foo"]


def test_manifest_none_yields_empty_manifest_diff() -> None:
    a = _empty_model()
    b = _empty_model()
    m = {"files": ["only_in_a.py"], "symbols": [{"name": "s", "signature": "()"}]}
    d = semantic_diff(a, b, manifest_a=m, manifest_b=None)
    assert d.manifest.files_added == []
    assert d.manifest.files_removed == []
    assert d.manifest.symbols_added == []
    assert d.manifest.symbols_removed == []
    assert d.manifest.symbols_signature_changed == []


# --- Children ---

def test_children_add_remove_revision_change() -> None:
    a = _empty_model()
    b = _empty_model()
    ra = {"arch-1": "rev-a1", "arch-2": "rev-a2"}
    rb = {"arch-2": "rev-b2", "arch-3": "rev-b3"}
    d = semantic_diff(a, b, child_revisions_a=ra, child_revisions_b=rb)
    assert d.children.added == ["arch-3"]
    assert d.children.removed == ["arch-1"]
    assert d.children.revision_changed == [
        {"architecture_id": "arch-2", "from": "rev-a2", "to": "rev-b2"}
    ]


def test_children_none_yields_empty() -> None:
    a = _empty_model()
    b = _empty_model()
    d = semantic_diff(a, b, child_revisions_a={"x": "y"}, child_revisions_b=None)
    assert d.children.added == []
    assert d.children.removed == []
    assert d.children.revision_changed == []


# --- Git provenance ---

def test_git_commit_propagated_when_both_present() -> None:
    a = _empty_model()
    b = _empty_model()
    a.meta.provenance = {"git_commit": "aaaa"}  # type: ignore[attr-defined]
    b.meta.provenance = {"git_commit": "bbbb"}  # type: ignore[attr-defined]
    d = semantic_diff(a, b)
    assert d.git == {"commit_a": "aaaa", "commit_b": "bbbb"}


def test_git_commit_none_when_only_one_present() -> None:
    a = _empty_model()
    b = _empty_model()
    a.meta.provenance = {"git_commit": "aaaa"}  # type: ignore[attr-defined]
    d = semantic_diff(a, b)
    assert d.git == {"commit_a": None, "commit_b": None}


# --- Determinism repeated ---

def test_repeated_diff_is_byte_identical() -> None:
    a = _empty_model()
    b = _empty_model()
    a.entities.components.append(Component(id="C-2", name="a", status=Status.ACTIVE))
    a.entities.components.append(Component(id="C-1", name="a", status=Status.ACTIVE))
    b.entities.components.append(Component(id="C-3", name="a", status=Status.ACTIVE))
    b.entities.components.append(Component(id="C-1", name="a-renamed", status=Status.ACTIVE))
    b.relationships.append(Relationship(type=RelationType.REALIZES, from_id="B", to_id="A"))
    b.relationships.append(Relationship(type=RelationType.REALIZES, from_id="A", to_id="A"))
    d1 = semantic_diff(a, b)
    d2 = semantic_diff(a, b)
    # pydantic v2 model_dump gives deterministic dicts if input is deterministic
    assert d1.model_dump() == d2.model_dump()


def test_semantic_diff_forbids_extra_fields() -> None:
    with pytest.raises(Exception):
        SemanticDiff(entities={}, relationships=RelationshipDiff(), manifest=ManifestDiff(),
                     children=ChildrenDiff(), git={"commit_a": None, "commit_b": None},
                     unexpected="x")  # type: ignore[call-arg]


def test_entity_kind_diff_forbids_extra_fields() -> None:
    with pytest.raises(Exception):
        EntityKindDiff(added=[], removed=[], changed=[], boom=1)  # type: ignore[call-arg]
