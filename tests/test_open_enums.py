"""Tests for open enum parsing — unknown values accepted as plain strings."""
from architecture_model.core.types import (
    ComponentKind, InterfaceType, BehaviorPattern,
    ConstraintType, ActorType, RelationType,
)


def test_component_kind_accepts_unknown():
    result = ComponentKind.parse("sensor")
    assert result == "sensor"


def test_component_kind_known_returns_enum():
    result = ComponentKind.parse("service")
    assert result == ComponentKind.SERVICE


def test_interface_type_accepts_unknown():
    result = InterfaceType.parse("fieldbus")
    assert result == "fieldbus"


def test_interface_type_known_returns_enum():
    result = InterfaceType.parse("REST")
    assert result == InterfaceType.REST


def test_behavior_pattern_accepts_unknown():
    result = BehaviorPattern.parse("feedback-loop")
    assert result == "feedback-loop"


def test_behavior_pattern_known_returns_enum():
    result = BehaviorPattern.parse("sequential")
    assert result == BehaviorPattern.SEQUENTIAL


def test_constraint_type_accepts_unknown():
    result = ConstraintType.parse("compliance")
    assert result == "compliance"


def test_actor_type_accepts_unknown():
    result = ActorType.parse("bot")
    assert result == "bot"


def test_relation_type_accepts_unknown():
    result = RelationType.parse("orchestrates")
    assert result == "orchestrates"


def test_parser_accepts_unknown_kind():
    import yaml
    from architecture_model.core.parser import _parse_raw
    raw = yaml.safe_load("""
    meta:
      project: test
      schema_version: '1.4'
    entities:
      components:
        - id: COMP-1
          name: Temperature Sensor
          status: ACTIVE
          kind: sensor
          layer: field-layer
          f_block: F1
    relationships: []
    """)
    model = _parse_raw(raw)
    assert model.entities.components[0].kind == "sensor"


def test_parser_accepts_unknown_interface_type():
    import yaml
    from architecture_model.core.parser import _parse_raw
    raw = yaml.safe_load("""
    meta:
      project: test
      schema_version: '1.4'
    entities:
      interfaces:
        - id: IF-1
          name: Fieldbus Interface
          status: ACTIVE
          type: fieldbus
    relationships: []
    """)
    model = _parse_raw(raw)
    assert model.entities.interfaces[0].type == "fieldbus"


def test_parser_accepts_unknown_relation_type():
    import yaml
    from architecture_model.core.parser import _parse_raw
    raw = yaml.safe_load("""
    meta:
      project: test
      schema_version: '1.4'
    entities: {}
    relationships:
      - type: orchestrates
        from: A
        to: B
    """)
    model = _parse_raw(raw)
    assert model.relationships[0].type == "orchestrates"


def test_roundtrip_unknown_kind():
    """Unknown enum values survive to_dict() serialization."""
    import yaml
    from architecture_model.core.parser import _parse_raw
    raw = yaml.safe_load("""
    meta:
      project: test
      schema_version: '1.4'
    entities:
      components:
        - id: COMP-1
          name: Sensor
          status: ACTIVE
          kind: sensor
    relationships: []
    """)
    model = _parse_raw(raw)
    d = model.to_dict()
    comp = d["entities"]["components"][0]
    assert comp["kind"] == "sensor"
