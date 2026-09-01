"""Tests for the Decision dataclass and decisions field on BaseEntity."""

from architecture_model.core.types import DecisionEntry as Decision, BaseEntity, Component, Status


def test_decision_defaults():
    d = Decision()
    assert d.date == ""
    assert d.choice == ""
    assert d.rationale == ""
    assert d.alternatives == []
    assert d.context == ""


def test_decision_with_values():
    d = Decision(
        date="2026-01-15",
        choice="Use PostgreSQL",
        rationale="Better JSON support",
        alternatives=["MySQL", "SQLite"],
        context="Database selection",
    )
    assert d.date == "2026-01-15"
    assert d.choice == "Use PostgreSQL"
    assert d.alternatives == ["MySQL", "SQLite"]


def test_base_entity_has_decisions():
    e = BaseEntity(id="E-1", name="Test", status=Status.ACTIVE)
    assert e.decisions == []


def test_base_entity_decisions_populated():
    d = Decision(choice="Go with REST")
    e = BaseEntity(id="E-1", name="Test", status=Status.ACTIVE, decisions=[d])
    assert len(e.decisions) == 1
    assert e.decisions[0].choice == "Go with REST"


def test_component_inherits_decisions():
    d = Decision(choice="Use Redis")
    c = Component(id="COMP-1", name="Cache", status=Status.ACTIVE, decisions=[d])
    assert len(c.decisions) == 1
    assert c.decisions[0].choice == "Use Redis"
