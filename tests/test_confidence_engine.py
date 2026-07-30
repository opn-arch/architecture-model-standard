"""Test confidence computation engine."""
from architecture_model.core.confidence import (
    compute_component_confidence,
    compute_behavior_confidence,
    compute_capability_confidence,
    compute_interface_confidence,
    compute_model_confidence,
)
from architecture_model.core.types import (
    Component, Behavior, Capability, Interface, Status, Priority,
    FunctionSignature, Symbol, TestContract, ArchitectureModel, ModelMeta, Entities,
    Relationship, RelationType,
)


def test_empty_component_zero_confidence():
    c = Component(id="C1", name="Empty", status=Status.ACTIVE)
    score = compute_component_confidence(c)
    assert score == 0.0


def test_full_component_high_confidence():
    c = Component(
        id="C1", name="Full", status=Status.ACTIVE,
        contract="Handles MQTT fan entities",
        pattern="entity-platform",
        signatures=[FunctionSignature(name="setup", params=["hass"], returns="None")],
        symbols=[Symbol(name="MqttFan", members=["turn_on", "turn_off"])],
        test_contracts=[TestContract(test_file="test_fan.py", test_method="test_on", assertion="state=on")],
        responsibilities=["Handle fan commands"],
        files=["mqtt/fan.py"],
    )
    score = compute_component_confidence(c)
    assert score >= 0.9


def test_partial_component_medium_confidence():
    c = Component(
        id="C1", name="Partial", status=Status.ACTIVE,
        contract="Handles something",
        files=["a.py"],
    )
    score = compute_component_confidence(c)
    assert 0.2 < score < 0.6


def test_empty_behavior_zero():
    b = Behavior(id="B1", name="Empty", status=Status.ACTIVE)
    score = compute_behavior_confidence(b)
    assert score == 0.0


def test_full_behavior_high():
    b = Behavior(
        id="B1", name="Full", status=Status.ACTIVE,
        trigger="MQTT message received",
        actor="MQTTClient",
        steps=["Parse payload", "Update entity state", "Fire event"],
        preconditions=["Connected to broker"],
        postconditions=["Entity state updated"],
    )
    score = compute_behavior_confidence(b)
    assert score >= 0.85


def test_capability_with_requirements():
    cap = Capability(id="CAP-1", name="Cap", status=Status.ACTIVE,
                     description="Handles MQTT", requirements=["Must support QoS 1"])
    score = compute_capability_confidence(cap)
    assert score >= 0.6


def test_capability_realized_boosts_score():
    cap = Capability(id="CAP-1", name="Cap", status=Status.ACTIVE,
                     description="Handles MQTT", requirements=["QoS 1"])
    base_score = compute_capability_confidence(cap)
    boosted = compute_capability_confidence(cap, realized=True)
    assert boosted > base_score


def test_interface_full():
    i = Interface(id="IF-1", name="MQTT API", status=Status.ACTIVE,
                  protocol="MQTT", data_format="JSON",
                  provider="COMP-1", consumer="COMP-2",
                  endpoints=[{"topic": "home/fan"}], schema="mqtt_schema.json")
    score = compute_interface_confidence(i)
    assert score >= 0.9


def test_compute_model_confidence_fills_all():
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(
            components=[
                Component(id="C1", name="A", status=Status.ACTIVE, contract="Does X", files=["a.py"]),
                Component(id="C2", name="B", status=Status.ACTIVE),
            ],
            behaviors=[Behavior(id="B1", name="Flow", status=Status.ACTIVE, steps=["a", "b"])],
        ),
        relationships=[Relationship(from_id="C1", to_id="CAP-1", type=RelationType.REALIZES)],
    )
    updated = compute_model_confidence(model)
    assert updated.entities.components[0].confidence > 0
    assert updated.entities.components[1].confidence == 0.0
    assert updated.entities.behaviors[0].confidence > 0
