"""Part 16a: `sequence:` field on Relationship (flow substrate).

Guards the additive `sequence` field: roundtrip, absence-preservation,
type/value validation via parser warnings, and non-triggers soft warning.
Schema-level presence/validity guarded separately in
``tests/spec/test_schema_2_1_defs.py``.
"""

from __future__ import annotations

import warnings

import pytest

from architecture_model.core.parser import _parse_raw, _parse_relationship
from architecture_model.core.types import (
    ArchitectureModel,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)


def _minimal_model_with_rel(rel: Relationship) -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.2", project="test"),
        entities=Entities(),
        relationships=[rel],
    )


def test_sequence_roundtrips_through_parse_and_serialize() -> None:
    rel = Relationship(
        type=RelationType.TRIGGERS,
        from_id="BEH-a",
        to_id="BEH-b",
        sequence=3,
    )
    model = _minimal_model_with_rel(rel)
    dumped = model.to_dict()
    assert dumped["relationships"][0]["sequence"] == 3

    reparsed = _parse_raw(dumped)
    assert reparsed.relationships[0].sequence == 3
    assert reparsed.relationships[0].type == RelationType.TRIGGERS


def test_missing_sequence_stays_absent_in_serialization() -> None:
    """Digest-stability: fixtures without sequence must not gain the key."""
    rel = Relationship(
        type=RelationType.TRIGGERS,
        from_id="BEH-a",
        to_id="BEH-b",
    )
    model = _minimal_model_with_rel(rel)
    dumped = model.to_dict()
    assert "sequence" not in dumped["relationships"][0]

    reparsed = _parse_raw(dumped)
    assert reparsed.relationships[0].sequence is None


def test_negative_sequence_rejected_with_warning() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rel = _parse_relationship({
            "type": "triggers", "from": "BEH-a", "to": "BEH-b", "sequence": -1,
        })
    assert rel.sequence is None
    assert any("positive int" in str(x.message) for x in w)


def test_zero_sequence_rejected_with_warning() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rel = _parse_relationship({
            "type": "triggers", "from": "BEH-a", "to": "BEH-b", "sequence": 0,
        })
    assert rel.sequence is None
    assert any("positive int" in str(x.message) for x in w)


def test_string_sequence_rejected_with_warning() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rel = _parse_relationship({
            "type": "triggers", "from": "BEH-a", "to": "BEH-b", "sequence": "3",
        })
    assert rel.sequence is None
    assert any("positive int" in str(x.message) for x in w)


def test_bool_sequence_rejected_with_warning() -> None:
    """``True`` is-a int in Python; explicitly guard against it."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rel = _parse_relationship({
            "type": "triggers", "from": "BEH-a", "to": "BEH-b", "sequence": True,
        })
    assert rel.sequence is None
    assert any("positive int" in str(x.message) for x in w)


def test_sequence_on_non_triggers_edge_emits_soft_warning() -> None:
    """Parses succeed, but a UserWarning surfaces the semantics gap."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rel = _parse_relationship({
            "type": "contains", "from": "CAP-a", "to": "BEH-b", "sequence": 2,
        })
    assert rel.sequence == 2  # value preserved
    assert any("non-'triggers'" in str(x.message) for x in w)


def test_existing_fixture_shape_unchanged() -> None:
    """Roundtrip a triggers edge with no sequence; assert byte-shape parity."""
    raw = {
        "meta": {"schema_version": "2.2", "project": "test"},
        "entities": {},
        "relationships": [
            {"type": "triggers", "from": "BEH-a", "to": "BEH-b"},
        ],
    }
    model = _parse_raw(raw)
    dumped = model.to_dict()
    assert dumped["relationships"][0] == {
        "type": "triggers", "from": "BEH-a", "to": "BEH-b",
    }
