"""Interface gains 7 optional semantic fields (Phase 2 Task 3 / schema 2.1)."""

from __future__ import annotations

from architecture_model.core.parser import _parse_interface
from architecture_model.core.semantic_types import SLO, VerificationRef
from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    Maturity,
    ModelMeta,
)


def _make(**overrides):
    d = {"id": "IF-1", "name": "X", "status": "ACTIVE"}
    d.update(overrides)
    return _parse_interface(d)


def test_interface_defaults():
    i = _make()
    assert i.stakeholders == []
    assert i.success_criteria == []
    assert i.assumptions == []
    assert i.open_questions == []
    assert i.verification == []
    assert i.slos == []
    assert i.maturity is None


def test_interface_new_fields_parse():
    i = _make(
        stakeholders=["consumer-team"],
        success_criteria=["schema stable"],
        assumptions=["tls terminated upstream"],
        open_questions=["auth v2?"],
        verification=[{"id": "VER-I1", "method": "contract-test"}],
        slos=[{"metric": "p99", "target": "100ms", "window": "1m"}],
        maturity="stable",
    )
    assert i.stakeholders == ["consumer-team"]
    assert isinstance(i.verification[0], VerificationRef)
    assert isinstance(i.slos[0], SLO)
    assert i.slos[0].target == "100ms"
    assert i.maturity == Maturity.STABLE


def test_interface_dump_omits_empty():
    i = _make()
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(interfaces=[i]),
    )
    d = model.to_dict()["entities"]["interfaces"][0]
    for k in (
        "stakeholders",
        "success_criteria",
        "assumptions",
        "open_questions",
        "verification",
        "slos",
        "maturity",
    ):
        assert k not in d


def test_interface_dump_serializes_typed():
    i = _make(
        verification=[{"id": "VER-I1", "method": "contract"}],
        slos=[{"metric": "lat", "target": "50ms", "window": "p99"}],
        maturity="active",
    )
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(interfaces=[i]),
    )
    d = model.to_dict()["entities"]["interfaces"][0]
    assert d["verification"][0]["id"] == "VER-I1"
    assert d["slos"][0]["metric"] == "lat"
    assert d["maturity"] == "active"
