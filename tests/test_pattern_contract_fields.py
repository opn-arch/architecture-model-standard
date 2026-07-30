"""Test pattern and contract fields on Component."""
from architecture_model.core.types import Component, Status


def test_component_has_pattern_field():
    c = Component(id="COMP-1", name="Test", status=Status.ACTIVE)
    assert c.pattern == ""
    c2 = Component(id="COMP-2", name="Test2", status=Status.ACTIVE, pattern="entity-platform")
    assert c2.pattern == "entity-platform"


def test_component_has_contract_field():
    c = Component(id="COMP-1", name="Test", status=Status.ACTIVE)
    assert c.contract == ""
    c2 = Component(id="COMP-2", name="Test2", status=Status.ACTIVE, contract="Translates MQTT messages to HA entity state updates")
    assert c2.contract == "Translates MQTT messages to HA entity state updates"


def test_pattern_contract_roundtrip_yaml():
    """Pattern and contract survive YAML serialization."""
    from architecture_model.core.parser import load_model
    import tempfile
    from pathlib import Path

    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: MQTTFan
      status: ACTIVE
      pattern: entity-platform
      contract: Exposes MQTT fan devices as HA fan entities
relationships: []
"""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(model_yaml)
        f.flush()
        model = load_model(Path(f.name))
    assert model.entities.components[0].pattern == "entity-platform"
    assert model.entities.components[0].contract == "Exposes MQTT fan devices as HA fan entities"
