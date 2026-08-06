import yaml
import pytest
from architecture_model.core.parser import _parse_raw
from architecture_model.core.validator import validate_model
from architecture_model.core.slicer import slice_by_source_block

CONTROLS_MODEL = """
meta:
  project: factory-line-3
  schema_version: '1.4'
  domain_profile: controls
entities:
  actors:
    - id: ACT-1
      name: Plant Operator
      status: ACTIVE
      type: human
  capabilities:
    - id: CAP-S1
      name: Temperature Monitoring
      status: ACTIVE
      source_block: S1
      priority: high
  layers:
    - id: field-layer
      name: Field Layer
      status: ACTIVE
      order: 1
    - id: control-layer
      name: Control Layer
      status: ACTIVE
      order: 2
  components:
    - id: COMP-1
      name: Temperature Sensor
      status: ACTIVE
      kind: sensor
      layer: field-layer
      source_block: S1
      extensions:
        signal_type: analog
        sampling_rate_hz: 1000
    - id: COMP-2
      name: PID Controller
      status: ACTIVE
      kind: controller
      layer: control-layer
      source_block: S1
relationships:
  - type: realizes
    from: COMP-1
    to: CAP-S1
  - type: depends_on
    from: COMP-2
    to: COMP-1
"""

def test_controls_model_parses():
    raw = yaml.safe_load(CONTROLS_MODEL)
    model = _parse_raw(raw)
    assert model.meta.domain_profile == "controls"
    assert model.entities.components[0].kind == "sensor"

def test_controls_model_validates():
    raw = yaml.safe_load(CONTROLS_MODEL)
    model = _parse_raw(raw)
    result = validate_model(model)
    assert result.is_valid
    assert result.score >= 90

def test_controls_model_slices():
    raw = yaml.safe_load(CONTROLS_MODEL)
    model = _parse_raw(raw)
    sliced = slice_by_source_block(model, "S1")
    assert len(sliced.entities.components) == 2

MECHANICAL_MODEL = """
meta:
  project: robotic-arm
  schema_version: '1.4'
  domain_profile: mechanical
entities:
  capabilities:
    - id: CAP-S1
      name: 6-DOF Motion
      status: ACTIVE
      source_block: S1
      priority: high
  layers:
    - id: structure-layer
      name: Structural Frame
      status: ACTIVE
      order: 1
  components:
    - id: COMP-1
      name: Base Housing
      status: ACTIVE
      kind: housing
      layer: structure-layer
      source_block: S1
      extensions:
        material: aluminum-6061
        mass_kg: 12.5
    - id: COMP-2
      name: Shoulder Joint
      status: ACTIVE
      kind: assembly
      layer: structure-layer
      source_block: S1
      extensions:
        material: steel-4140
        mass_kg: 8.3
relationships:
  - type: realizes
    from: COMP-1
    to: CAP-S1
  - type: contains
    from: COMP-1
    to: COMP-2
"""

def test_mechanical_model_parses():
    raw = yaml.safe_load(MECHANICAL_MODEL)
    model = _parse_raw(raw)
    assert model.meta.domain_profile == "mechanical"
    assert model.entities.components[0].extensions["material"] == "aluminum-6061"

def test_mechanical_model_validates():
    raw = yaml.safe_load(MECHANICAL_MODEL)
    model = _parse_raw(raw)
    result = validate_model(model)
    assert result.is_valid
