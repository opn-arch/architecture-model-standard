"""Tests for WP-1 schema evolution — new SE fields in JSON Schema."""
import json
from pathlib import Path

import jsonschema


SCHEMA_PATH = Path(__file__).parent.parent / "src" / "architecture_model" / "spec" / "schema.json"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text())


class TestSchemaNewFields:
    def test_base_entity_has_intent(self):
        schema = _load_schema()
        base = schema["$defs"]["base_entity"]["properties"]
        assert "intent" in base

    def test_component_has_goals(self):
        schema = _load_schema()
        comp = schema["$defs"]["component"]["properties"]
        assert "goals" in comp

    def test_component_has_moes(self):
        schema = _load_schema()
        comp = schema["$defs"]["component"]["properties"]
        assert "moes" in comp

    def test_component_has_trade_offs(self):
        schema = _load_schema()
        comp = schema["$defs"]["component"]["properties"]
        assert "trade_offs" in comp

    def test_component_has_failure_modes(self):
        schema = _load_schema()
        comp = schema["$defs"]["component"]["properties"]
        assert "failure_modes" in comp

    def test_capability_has_moes(self):
        schema = _load_schema()
        cap = schema["$defs"]["capability"]["properties"]
        assert "moes" in cap

    def test_requirement_has_rationale(self):
        schema = _load_schema()
        req = schema["$defs"]["requirement"]["properties"]
        assert "rationale" in req

    def test_requirement_has_priority(self):
        schema = _load_schema()
        req = schema["$defs"]["requirement"]["properties"]
        assert "priority" in req

    def test_interface_has_contract(self):
        schema = _load_schema()
        iface = schema["$defs"]["interface"]["properties"]
        assert "contract" in iface

    def test_schema_version_bumped(self):
        schema = _load_schema()
        assert "2.1" in schema["$id"], f"Schema $id should reference v2.1: {schema['$id']}"


class TestSchemaValidation:
    """Ensure a model with new fields validates against updated schema."""

    def test_model_with_se_fields_validates(self):
        schema = _load_schema()
        model = {
            "meta": {
                "schema_version": "2.1.0",
                "project": "test",
                "generated_at": "2026-01-01T00:00:00Z",
            },
            "entities": {
                "components": [{
                    "id": "COMP-1",
                    "name": "Test",
                    "status": "ACTIVE",
                    "intent": "Provide core functionality",
                    "goals": ["High reliability"],
                    "moes": ["99.9% uptime"],
                    "trade_offs": ["Speed vs accuracy"],
                    "failure_modes": ["Timeout on large models"],
                }],
                "capabilities": [{
                    "id": "CAP-1",
                    "name": "Validation",
                    "status": "ACTIVE",
                    "moes": ["Catch 95% of errors"],
                }],
                "requirements": [{
                    "id": "REQ-1",
                    "name": "Must validate",
                    "status": "ACTIVE",
                    "rationale": "Ensures model correctness",
                    "priority": "must",
                    "moe": "Zero false negatives on structural checks",
                }],
                "interfaces": [{
                    "id": "IF-1",
                    "name": "Validate API",
                    "status": "ACTIVE",
                    "contract": "Input: ArchitectureModel, Output: ValidationResult",
                }],
            },
            "relationships": [],
        }
        jsonschema.validate(model, schema)  # Should not raise
