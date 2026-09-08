"""M2 → M1 propagation rules."""

from architecture_model.lifecycle.invalidation import propagates_to_m1


def _diff(**kw):
    return {
        "entities": kw.get("entities", {"added": [], "removed": [], "changed": []}),
        "relationships": kw.get("relationships", {"added": [], "removed": [], "changed": []}),
    }


def test_public_interface_add_propagates():
    diff = _diff(relationships={
        "added": [{"type": "exposes", "from": "COMP-1", "to": "IF-1"}],
        "removed": [], "changed": [],
    })
    assert propagates_to_m1(diff) is True


def test_cross_subsystem_depends_on_propagates():
    diff = _diff(relationships={
        "added": [{"type": "depends-on", "from": "COMP-1", "to": "COMP-2", "cross_subsystem": True}],
        "removed": [], "changed": [],
    })
    assert propagates_to_m1(diff) is True


def test_internal_only_change_does_not_propagate():
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "component", "id": "COMP-1", "fields": ["name"]}],
    })
    assert propagates_to_m1(diff) is False


def test_semantic_field_on_top_level_entity_propagates_surgically():
    """A semantic-field change on a component that appears in M1 → M1 semantic-only invalidation."""
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "component", "id": "COMP-1", "fields": ["intent"],
                     "appears_in_m1": True}],
    })
    assert propagates_to_m1(diff) is True
