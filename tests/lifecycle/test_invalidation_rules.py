"""Invalidation rules: diff kinds → stale view families."""

import pytest
from architecture_model.lifecycle.invalidation import stale_families, RULES


def _diff(**kw):
    """Minimal diff dict for tests."""
    return {
        "entities": kw.get("entities", {"added": [], "removed": [], "changed": []}),
        "relationships": kw.get("relationships", {"added": [], "removed": [], "changed": []}),
    }


def test_component_added_invalidates_f3_f2_f8():
    diff = _diff(entities={
        "added": [{"kind": "component", "id": "COMP-99"}],
        "removed": [], "changed": [],
    })
    families = stale_families(diff)
    assert "family3" in families
    assert "family2" in families
    assert "family8" in families


def test_capability_change_invalidates_f1_f2_f7():
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "capability", "id": "CAP-1", "fields": ["intent"]}],
    })
    families = stale_families(diff)
    assert "family1" in families
    assert "family2" in families
    assert "family7" in families


def test_constraint_added_invalidates_f7_f1():
    diff = _diff(entities={
        "added": [{"kind": "constraint", "id": "CON-9"}],
        "removed": [], "changed": [],
    })
    families = stale_families(diff)
    assert "family7" in families
    assert "family1" in families


def test_interface_change_invalidates_f6_f3():
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "interface", "id": "IF-1", "fields": ["name"]}],
    })
    families = stale_families(diff)
    assert "family6" in families
    assert "family3" in families


def test_semantic_field_only_change_invalidates_only_touched_families():
    """A change to failure_modes on a Behavior touches F7, not F3."""
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "behavior", "id": "BEH-1", "fields": ["failure_modes"]}],
    })
    families = stale_families(diff)
    assert "family7" in families
    assert "family3" not in families


def test_empty_diff_stales_nothing():
    assert stale_families(_diff()) == set()


def test_rules_are_data_not_code():
    """RULES must be a data table, iterable, and reference-stable."""
    assert isinstance(RULES, list)
    assert all(hasattr(r, "trigger") and hasattr(r, "invalidates") for r in RULES)
