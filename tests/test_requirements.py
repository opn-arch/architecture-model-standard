"""Tests for Requirement entity type and satisfies relationship (Task C1)."""
import tempfile
from pathlib import Path

import yaml

from architecture_model.core.parser import load_model, save_model, _parse_raw
from architecture_model.core.types import Requirement, RelationType


REQUIREMENT_MODEL = """
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Auth
      status: ACTIVE
  requirements:
    - id: REQ-001
      name: User Authentication
      text: System shall authenticate users via OAuth2
      source_doc: requirements.md
      source_anchor: "L42"
      content_hash: abc123
      status: ACTIVE
relationships:
  - from: COMP-1
    to: REQ-001
    type: satisfies
"""

NO_REQUIREMENTS_MODEL = """
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Auth
      status: ACTIVE
relationships: []
"""


class TestRequirementEntity:
    def test_parse_requirements(self):
        raw = yaml.safe_load(REQUIREMENT_MODEL)
        model = _parse_raw(raw)
        assert len(model.entities.requirements) == 1
        assert model.entities.requirements[0].id == "REQ-001"

    def test_requirement_fields(self):
        raw = yaml.safe_load(REQUIREMENT_MODEL)
        model = _parse_raw(raw)
        req = model.entities.requirements[0]
        assert req.name == "User Authentication"
        assert req.text == "System shall authenticate users via OAuth2"
        assert req.source_doc == "requirements.md"
        assert req.source_anchor == "L42"
        assert req.content_hash == "abc123"

    def test_satisfies_relationship(self):
        raw = yaml.safe_load(REQUIREMENT_MODEL)
        model = _parse_raw(raw)
        rel = model.relationships[0]
        assert rel.type == RelationType.SATISFIES
        assert rel.from_id == "COMP-1"
        assert rel.to_id == "REQ-001"

    def test_round_trip(self):
        raw = yaml.safe_load(REQUIREMENT_MODEL)
        model = _parse_raw(raw)
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            save_model(model, f.name)
            reloaded = load_model(f.name)
        assert len(reloaded.entities.requirements) == 1
        req = reloaded.entities.requirements[0]
        assert req.id == "REQ-001"
        assert req.text == "System shall authenticate users via OAuth2"

    def test_no_requirements_backward_compat(self):
        raw = yaml.safe_load(NO_REQUIREMENTS_MODEL)
        model = _parse_raw(raw)
        assert model.entities.requirements == []
