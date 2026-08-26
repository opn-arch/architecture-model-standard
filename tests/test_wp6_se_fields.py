"""Tests for WP-6 SE fields on entity dataclasses."""
from architecture_model.core.types import (
    Actor, Behavior, Capability, Component, Constraint,
    Interface, Requirement, Status,
)


class TestBaseEntitySEFields:
    def test_intent_default_empty(self):
        """All entities should have intent field defaulting to empty string."""
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.intent == ""

    def test_intent_settable(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      intent="Provide validation for architecture models")
        assert c.intent == "Provide validation for architecture models"


class TestComponentSEFields:
    def test_goals_default_empty(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.goals == []

    def test_moes_default_empty(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.moes == []

    def test_trade_offs_default_empty(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.trade_offs == []

    def test_failure_modes_default_empty(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.failure_modes == []

    def test_all_se_fields_populated(self):
        c = Component(
            id="C-1", name="Test", status=Status.ACTIVE,
            intent="Enable structural validation",
            goals=["Catch 95% of model errors", "Sub-second validation"],
            moes=["error detection rate", "p99 latency"],
            trade_offs=["Strictness vs usability"],
            failure_modes=["Silent pass on malformed YAML"],
        )
        assert len(c.goals) == 2
        assert len(c.moes) == 2
        assert c.trade_offs[0] == "Strictness vs usability"


class TestCapabilitySEFields:
    def test_moes_default_empty(self):
        c = Capability(id="CAP-1", name="Test", status=Status.ACTIVE)
        assert c.moes == []

    def test_intent_default_empty(self):
        c = Capability(id="CAP-1", name="Test", status=Status.ACTIVE)
        assert c.intent == ""


class TestRequirementSEFields:
    def test_rationale_default_empty(self):
        r = Requirement(id="REQ-1", name="Test", status=Status.ACTIVE)
        assert r.rationale == ""

    def test_priority_default_empty(self):
        r = Requirement(id="REQ-1", name="Test", status=Status.ACTIVE)
        assert r.priority == ""

    def test_moe_default_empty(self):
        r = Requirement(id="REQ-1", name="Test", status=Status.ACTIVE)
        assert r.moe == ""


class TestBehaviorSEFields:
    def test_intent_default_empty(self):
        b = Behavior(id="BEH-1", name="Test", status=Status.ACTIVE)
        assert b.intent == ""


class TestInterfaceSEFields:
    def test_contract_default_empty(self):
        i = Interface(id="IF-1", name="Test", status=Status.ACTIVE)
        assert i.contract == ""


class TestConstraintSEFields:
    def test_rationale_already_exists(self):
        """Constraint already has rationale — verify it still works."""
        c = Constraint(id="CON-1", name="Test", status=Status.ACTIVE,
                       rationale="Required by ISO 25010")
        assert c.rationale == "Required by ISO 25010"

    def test_intent_default_empty(self):
        c = Constraint(id="CON-1", name="Test", status=Status.ACTIVE)
        assert c.intent == ""
