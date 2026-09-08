"""Actor, Constraint, Layer gain per-matrix semantic fields (Phase 2 Task 3 / 2.1).

Combined test file (one per commit would be excessive for the small deltas
on these three entity kinds).
"""

from __future__ import annotations

from architecture_model.core.parser import (
    _parse_actor,
    _parse_constraint,
    _parse_layer,
)
from architecture_model.core.semantic_types import VerificationRef
from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    Maturity,
    ModelMeta,
)


# ------------------------------------------------------------------ Actor -----

def _actor(**overrides):
    d = {"id": "ACT-1", "name": "User", "status": "ACTIVE"}
    d.update(overrides)
    return _parse_actor(d)


def test_actor_defaults():
    a = _actor()
    assert a.assumptions == []
    assert a.open_questions == []


def test_actor_new_fields_parse_and_dump():
    a = _actor(assumptions=["logged in"], open_questions=["mfa required?"])
    assert a.assumptions == ["logged in"]
    assert a.open_questions == ["mfa required?"]
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(actors=[a]),
    )
    d = model.to_dict()["entities"]["actors"][0]
    assert d["assumptions"] == ["logged in"]
    assert d["open_questions"] == ["mfa required?"]


def test_actor_dump_omits_empty():
    a = _actor()
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(actors=[a]),
    )
    d = model.to_dict()["entities"]["actors"][0]
    assert "assumptions" not in d
    assert "open_questions" not in d


# ------------------------------------------------------------- Constraint -----

def _con(**overrides):
    d = {"id": "CON-1", "name": "P99", "status": "ACTIVE"}
    d.update(overrides)
    return _parse_constraint(d)


def test_constraint_defaults():
    c = _con()
    assert c.success_criteria == []
    assert c.assumptions == []
    assert c.open_questions == []
    assert c.verification == []
    assert c.maturity is None


def test_constraint_new_fields_parse_and_dump():
    c = _con(
        success_criteria=["<200ms"],
        assumptions=["single region"],
        open_questions=["multi-region?"],
        verification=[{"id": "VER-C1", "method": "load-test"}],
        maturity="active",
    )
    assert isinstance(c.verification[0], VerificationRef)
    assert c.maturity == Maturity.ACTIVE
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(constraints=[c]),
    )
    d = model.to_dict()["entities"]["constraints"][0]
    assert d["success_criteria"] == ["<200ms"]
    assert d["verification"][0]["method"] == "load-test"
    assert d["maturity"] == "active"


def test_constraint_dump_omits_empty():
    c = _con()
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(constraints=[c]),
    )
    d = model.to_dict()["entities"]["constraints"][0]
    for k in ("success_criteria", "assumptions", "open_questions", "verification", "maturity"):
        assert k not in d


# ------------------------------------------------------------------ Layer -----

def _layer(**overrides):
    d = {"id": "LAY-1", "name": "web", "status": "ACTIVE"}
    d.update(overrides)
    return _parse_layer(d)


def test_layer_defaults():
    l = _layer()
    assert l.owner is None
    assert l.maturity is None


def test_layer_new_fields_parse_and_dump():
    l = _layer(owner="frontend-team", maturity="stable")
    assert l.owner == "frontend-team"
    assert l.maturity == Maturity.STABLE
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(layers=[l]),
    )
    d = model.to_dict()["entities"]["layers"][0]
    assert d["owner"] == "frontend-team"
    assert d["maturity"] == "stable"


def test_layer_dump_omits_empty():
    l = _layer()
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(layers=[l]),
    )
    d = model.to_dict()["entities"]["layers"][0]
    assert "owner" not in d
    assert "maturity" not in d
