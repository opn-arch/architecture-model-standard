"""WP-16: Round-trip tests ensuring new SE fields survive parse->serialize->parse."""
import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import Status


def _make_model_dict():
    return {
        "meta": {
            "schema_version": "2.1",
            "project": "test",
            "generated_at": "2026-01-01",
        },
        "entities": {
            "components": [{
                "id": "COMP-1",
                "name": "Core",
                "status": "ACTIVE",
                "intent": "Provide validation",
                "goals": ["High accuracy"],
                "moes": ["99% detection"],
                "trade_offs": ["Speed vs depth"],
                "failure_modes": ["OOM on large models"],
            }],
            "capabilities": [{
                "id": "CAP-1",
                "name": "Validate",
                "status": "ACTIVE",
                "intent": "Ensure correctness",
                "moes": ["Catch all structural errors"],
            }],
            "requirements": [{
                "id": "REQ-1",
                "name": "Must validate",
                "status": "ACTIVE",
                "intent": "Correctness assurance",
                "rationale": "Models used for code gen",
                "priority": "must",
                "moe": "Zero false negatives",
            }],
            "interfaces": [{
                "id": "IF-1",
                "name": "Validate API",
                "status": "ACTIVE",
                "intent": "Entry point for validation",
                "contract": "ArchitectureModel -> ValidationResult",
            }],
            "behaviors": [{
                "id": "BEH-1",
                "name": "Run Validation",
                "status": "ACTIVE",
                "intent": "User triggers validation of a model file",
            }],
            "constraints": [{
                "id": "CON-1",
                "name": "Performance",
                "status": "ACTIVE",
                "intent": "Keep validation fast",
                "rationale": "Used in CI pipelines",
            }],
        },
        "relationships": [],
    }


class TestRoundTrip:
    def test_component_se_fields_survive_parse(self):
        model = _parse_raw(_make_model_dict())
        c = model.entities.components[0]
        assert c.intent == "Provide validation"
        assert c.goals == ["High accuracy"]
        assert c.moes == ["99% detection"]
        assert c.trade_offs == ["Speed vs depth"]
        assert c.failure_modes == ["OOM on large models"]

    def test_capability_se_fields_survive_parse(self):
        model = _parse_raw(_make_model_dict())
        cap = model.entities.capabilities[0]
        assert cap.intent == "Ensure correctness"
        assert cap.moes == ["Catch all structural errors"]

    def test_requirement_se_fields_survive_parse(self):
        model = _parse_raw(_make_model_dict())
        r = model.entities.requirements[0]
        assert r.rationale == "Models used for code gen"
        assert r.priority == "must"
        assert r.moe == "Zero false negatives"

    def test_interface_contract_survives_parse(self):
        model = _parse_raw(_make_model_dict())
        i = model.entities.interfaces[0]
        assert i.contract == "ArchitectureModel -> ValidationResult"

    def test_to_dict_preserves_se_fields(self):
        model = _parse_raw(_make_model_dict())
        d = model.to_dict()
        comp = d["entities"]["components"][0]
        assert comp["intent"] == "Provide validation"
        assert comp["goals"] == ["High accuracy"]
        assert comp["moes"] == ["99% detection"]

    def test_yaml_roundtrip(self):
        model = _parse_raw(_make_model_dict())
        yaml_str = model.to_yaml()
        reparsed = yaml.safe_load(yaml_str)
        comp = reparsed["entities"]["components"][0]
        assert comp["intent"] == "Provide validation"
        assert comp["goals"] == ["High accuracy"]
