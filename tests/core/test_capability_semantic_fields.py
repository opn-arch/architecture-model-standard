"""Capability gains 7 optional semantic fields (Phase 2 Task 3 / schema 2.1).

Plan reference: docs/plans/2026-09-08-phase-2-schema-and-semantic-content.md
Task 3 matrix. Same deviation from spec as Task 2 applies: legacy BaseEntity
list[str] fields preserved; parser widens dict entries to typed objects.
"""

from __future__ import annotations

from architecture_model.core.parser import _parse_capability
from architecture_model.core.semantic_types import (
    FailureMode,  # noqa: F401 (kept for future extensions)
    RequirementRef,
    TradeOff,
    VerificationRef,
)
from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    Maturity,
    ModelMeta,
)


def _make(**overrides):
    d = {"id": "CAP-1", "name": "X", "status": "ACTIVE"}
    d.update(overrides)
    return _parse_capability(d)


def test_capability_defaults():
    c = _make()
    assert c.stakeholders == []
    assert c.success_criteria == []
    assert c.assumptions == []
    assert c.open_questions == []
    assert c.verification == []
    assert c.owner is None
    assert c.maturity is None


def test_capability_accepts_typed_and_untyped_entries():
    c = _make(
        requirements=[{"id": "REQ-1"}, "REQ-legacy"],
        trade_offs=[
            {
                "id": "TO-1",
                "decision": "d",
                "alternatives": ["a"],
                "rationale": "r",
                "consequences": ["c"],
                "revisit_when": "when",
                "status": "active",
            }
        ],
        verification=[{"id": "VER-1", "method": "review"}, "VER-2"],
    )
    assert isinstance(c.requirements[0], RequirementRef)
    assert c.requirements[1] == "REQ-legacy"
    assert isinstance(c.trade_offs[0], TradeOff)
    assert all(isinstance(v, VerificationRef) for v in c.verification)


def test_capability_new_fields_parse():
    c = _make(
        stakeholders=["team"],
        success_criteria=["latency<10ms"],
        assumptions=["single-tenant"],
        open_questions=["horizontal scale?"],
        owner="cap-owner",
        maturity="draft",
    )
    assert c.stakeholders == ["team"]
    assert c.success_criteria == ["latency<10ms"]
    assert c.assumptions == ["single-tenant"]
    assert c.open_questions == ["horizontal scale?"]
    assert c.owner == "cap-owner"
    assert c.maturity == Maturity.DRAFT


def test_capability_dump_omits_empty_semantic_fields():
    c = _make()
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(capabilities=[c]),
    )
    cap_d = model.to_dict()["entities"]["capabilities"][0]
    for k in (
        "stakeholders",
        "success_criteria",
        "assumptions",
        "open_questions",
        "verification",
        "owner",
        "maturity",
    ):
        assert k not in cap_d


def test_capability_dump_serializes_typed_entries():
    c = _make(
        trade_offs=[
            {
                "id": "TO-1",
                "decision": "d",
                "alternatives": ["a"],
                "rationale": "r",
                "consequences": ["c"],
                "revisit_when": "w",
            }
        ],
        verification=[{"id": "VER-1", "method": "review"}],
        owner="team",
        maturity="stable",
    )
    model = ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(capabilities=[c]),
    )
    cap_d = model.to_dict()["entities"]["capabilities"][0]
    assert cap_d["trade_offs"][0]["id"] == "TO-1"
    assert cap_d["verification"][0]["method"] == "review"
    assert cap_d["owner"] == "team"
    assert cap_d["maturity"] == "stable"
