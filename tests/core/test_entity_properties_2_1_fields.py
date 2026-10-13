"""Tests for schema 2.1 semantic field serialization (Track 4 Pass 2 Task 3)."""

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import build_entity_properties


def _model_with_populated_capability():
    # Note: uses a Component because Capability's dataclass omits
    # `slos` and `dependencies_rationale` (Component carries all 9
    # schema-2.1 semantic fields; see types.py:580-591).
    return _parse_raw({
        "meta": {"project": "sem-fields", "schema_version": "2.1"},
        "entities": {
            "components": [{
                "id": "CAP-1",
                "name": "RichCap",
                "status": "ACTIVE",
                "intent": "why-it-exists",
                "goals": ["goal-a"],
                "stakeholders": ["ops"],
                "success_criteria": ["metric-x-met"],
                "assumptions": ["network-available"],
                "open_questions": ["q1?"],
                "requirements": ["REQ-1"],
                "verification": ["test-suite-z"],
                "slos": [{"metric": "latency", "target": "<100ms", "window": "5m"}],
                "owner": "alice",
                "maturity": "stable",
                "dependencies_rationale": {"COMP-X": "because-y"},
            }],
        },
    })


def test_all_nine_new_semantic_fields_serialize():
    """The 9 schema-2.1 fields missing from _base must now appear in properties."""
    model = _model_with_populated_capability()
    props = build_entity_properties(model)
    universal = props["CAP-1"]["properties"]
    expected_labels = {
        "Stakeholders", "Success Criteria", "Assumptions", "Open Questions",
        "Verification", "SLOs", "Owner", "Maturity", "Dependencies Rationale",
    }
    for label in expected_labels:
        assert label in universal, f"missing label {label!r} in {list(universal)}"


def test_existing_fields_still_serialize():
    """Regression: existing 2.0 fields still appear."""
    model = _model_with_populated_capability()
    props = build_entity_properties(model)
    universal = props["CAP-1"]["properties"]
    assert "Intent" in universal
    assert "Goals" in universal
    assert "Requirements" in universal


def test_empty_semantic_fields_are_stripped():
    """None/empty values must not produce spurious keys."""
    raw = {
        "meta": {"project": "sparse", "schema_version": "2.1"},
        "entities": {"components": [{
            "id": "CAP-2", "name": "SparseCap", "status": "ACTIVE",
            "intent": "populated",  # only one field
        }]},
    }
    model = _parse_raw(raw)
    props = build_entity_properties(model)
    universal = props["CAP-2"]["properties"]
    assert "Intent" in universal
    assert "Stakeholders" not in universal
    assert "SLOs" not in universal
