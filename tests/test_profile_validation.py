import yaml
from architecture_model.core.parser import _parse_raw
from architecture_model.core.validator import validate_model


def test_profile_validation_catches_missing_required_field():
    raw = yaml.safe_load("""
    meta:
      project: factory
      schema_version: '1.4'
      domain_profile: controls
    entities:
      components:
        - id: COMP-1
          name: Temp Sensor
          status: ACTIVE
          kind: sensor
          layer: field-layer
          source_block: S1
    relationships: []
    """)
    model = _parse_raw(raw)
    result = validate_model(model)
    profile_issues = [i for i in result.issues if "signal_type" in i.message]
    assert len(profile_issues) > 0


def test_profile_validation_passes_with_required_field():
    raw = yaml.safe_load("""
    meta:
      project: factory
      schema_version: '1.4'
      domain_profile: controls
    entities:
      components:
        - id: COMP-1
          name: Temp Sensor
          status: ACTIVE
          kind: sensor
          layer: field-layer
          source_block: S1
          extensions:
            signal_type: analog
    relationships: []
    """)
    model = _parse_raw(raw)
    result = validate_model(model)
    profile_issues = [i for i in result.issues if "signal_type" in i.message]
    assert len(profile_issues) == 0
