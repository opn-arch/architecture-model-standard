"""Behavior gains 6 optional semantic fields (Phase 2 Task 3 / schema 2.1)."""

from __future__ import annotations

from architecture_model.core.parser import _parse_behavior
from architecture_model.core.semantic_types import FailureMode, VerificationRef
from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    Maturity,
    ModelMeta,
)


def _make(**overrides):
    d = {"id": "BEH-1", "name": "X", "status": "ACTIVE"}
    d.update(overrides)
    return _parse_behavior(d)


def test_behavior_defaults():
    b = _make()
    assert b.stakeholders == []
    assert b.success_criteria == []
    assert b.assumptions == []
    assert b.open_questions == []
    assert b.verification == []
    assert b.maturity is None


def test_behavior_typed_failure_modes_via_promotion():
    b = _make(
        failure_modes=[
            {
                "id": "FM-B1",
                "cause": "timeout",
                "effect": "abort",
                "likelihood": "likely",
                "severity": "major",
                "detection": "retry",
                "mitigation": "circuit-break",
            }
        ]
    )
    assert isinstance(b.failure_modes[0], FailureMode)


def test_behavior_new_fields_parse():
    b = _make(
        stakeholders=["ops"],
        success_criteria=["p99<200ms"],
        assumptions=["network available"],
        open_questions=["retry cap?"],
        verification=[{"id": "VER-B1", "method": "load-test"}],
        maturity="active",
    )
    assert b.stakeholders == ["ops"]
    assert b.success_criteria == ["p99<200ms"]
    assert b.assumptions == ["network available"]
    assert b.open_questions == ["retry cap?"]
    assert isinstance(b.verification[0], VerificationRef)
    assert b.maturity == Maturity.ACTIVE


def test_behavior_dump_omits_empty():
    b = _make()
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(behaviors=[b]),
    )
    beh_d = model.to_dict()["entities"]["behaviors"][0]
    for k in (
        "stakeholders",
        "success_criteria",
        "assumptions",
        "open_questions",
        "verification",
        "maturity",
    ):
        assert k not in beh_d


def test_behavior_dump_serializes_typed():
    b = _make(
        failure_modes=[
            {
                "id": "FM-B1",
                "cause": "c",
                "effect": "e",
                "likelihood": "rare",
                "severity": "minor",
                "detection": "d",
                "mitigation": "m",
            }
        ],
        verification=[{"id": "VER-B1", "method": "unit"}],
        maturity="draft",
    )
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(behaviors=[b]),
    )
    beh_d = model.to_dict()["entities"]["behaviors"][0]
    assert beh_d["failure_modes"][0]["id"] == "FM-B1"
    assert beh_d["verification"][0]["method"] == "unit"
    assert beh_d["maturity"] == "draft"
