"""Test confidence field on entities."""
from architecture_model.core.types import Component, Behavior, Capability, Interface, Status


def test_component_has_confidence_default_zero():
    c = Component(id="C1", name="Test", status=Status.ACTIVE)
    assert c.confidence == 0.0


def test_behavior_has_confidence():
    b = Behavior(id="B1", name="Test", status=Status.ACTIVE)
    assert b.confidence == 0.0


def test_capability_has_confidence():
    cap = Capability(id="CAP-1", name="Test", status=Status.ACTIVE)
    assert cap.confidence == 0.0


def test_interface_has_confidence():
    i = Interface(id="IF-1", name="Test", status=Status.ACTIVE)
    assert i.confidence == 0.0


def test_confidence_set_explicitly():
    c = Component(id="C1", name="Test", status=Status.ACTIVE, confidence=0.85)
    assert c.confidence == 0.85


def test_confidence_roundtrip_yaml():
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
      name: Test
      status: ACTIVE
      confidence: 0.92
relationships: []
"""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(model_yaml)
        f.flush()
        model = load_model(Path(f.name))
    assert model.entities.components[0].confidence == 0.92
