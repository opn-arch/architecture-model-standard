"""Tests for parser tolerance of agent-produced YAML formats."""
import yaml
import pytest

from architecture_model.core.parser import _parse_raw


def test_parse_entities_as_dict_of_dicts():
    """Agent produces entities keyed by ID instead of as a list."""
    raw = yaml.safe_load("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    COMP-1:
      name: Core Logging
      status: ACTIVE
    COMP-2:
      name: API Layer
      status: ACTIVE
relationships: []
""")
    model = _parse_raw(raw)
    assert len(model.entities.components) == 2
    ids = {c.id for c in model.entities.components}
    assert ids == {"COMP-1", "COMP-2"}
    assert model.entities.components[0].name == "Core Logging"


def test_parse_entities_as_list_still_works():
    """Standard list format still works."""
    raw = yaml.safe_load("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Foo
      status: ACTIVE
relationships: []
""")
    model = _parse_raw(raw)
    assert len(model.entities.components) == 1
    assert model.entities.components[0].id == "COMP-1"


def test_parse_relationship_source_target_aliases():
    """Agent uses 'source'/'target' instead of 'from'/'to'."""
    raw = yaml.safe_load("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components: []
relationships:
  - type: depends_on
    source: COMP-1
    target: COMP-2
""")
    model = _parse_raw(raw)
    assert len(model.relationships) == 1
    assert model.relationships[0].from_id == "COMP-1"
    assert model.relationships[0].to_id == "COMP-2"


def test_parse_relationship_from_id_to_id_aliases():
    """Agent uses 'from_id'/'to_id' instead of 'from'/'to'."""
    raw = yaml.safe_load("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components: []
relationships:
  - type: uses
    from_id: COMP-A
    to_id: COMP-B
""")
    model = _parse_raw(raw)
    assert model.relationships[0].from_id == "COMP-A"
    assert model.relationships[0].to_id == "COMP-B"


def test_parse_mixed_entity_formats():
    """Mix of dict-keyed and list formats across entity types."""
    raw = yaml.safe_load("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    COMP-1:
      name: Foo
      status: ACTIVE
  capabilities:
    - id: CAP-1
      name: Bar
      status: ACTIVE
relationships: []
""")
    model = _parse_raw(raw)
    assert len(model.entities.components) == 1
    assert len(model.entities.capabilities) == 1
    assert model.entities.components[0].id == "COMP-1"
    assert model.entities.capabilities[0].id == "CAP-1"
