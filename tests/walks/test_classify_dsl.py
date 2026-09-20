"""Unit tests for the classify DSL atoms.

Focuses on the `promise_attribute_count:<name> {op} N` atom added in Part 9
(L22 follow-on). See classify.py::_PROMISE_ATTR_RE + _eval_atom.

Complementary to test_pilot_*.py: those exercise full WalkSpec runs, this
file pins per-atom semantics for the classify predicate engine.
"""

from __future__ import annotations

import pytest

from architecture_model.walks.stages.classify import _eval_atom, _eval_predicate


# ---------- promise_attribute_count -----------------------------------------


def _entity_with(*attrs_statuses: tuple[str, str]) -> dict:
    """Build an entity with promises of (attribute, status) pairs."""
    return {
        "id": "E",
        "promises": [
            {"id": f"P{i}", "attribute": a, "status": s}
            for i, (a, s) in enumerate(attrs_statuses)
        ],
    }


def test_promise_attribute_count_zero_when_no_promises():
    assert _eval_atom("promise_attribute_count:goals >= 1", {"id": "E"}) is False
    assert _eval_atom("promise_attribute_count:goals == 0", {"id": "E"}) is True


def test_promise_attribute_count_zero_when_promises_empty_list():
    e = {"id": "E", "promises": []}
    assert _eval_atom("promise_attribute_count:goals >= 1", e) is False
    assert _eval_atom("promise_attribute_count:goals == 0", e) is True


def test_promise_attribute_count_ge_operator():
    e = _entity_with(("goals", "verified"), ("goals", "proposed"), ("requirements", "verified"))
    assert _eval_atom("promise_attribute_count:goals >= 1", e) is True
    assert _eval_atom("promise_attribute_count:goals >= 2", e) is True
    assert _eval_atom("promise_attribute_count:goals >= 3", e) is False


def test_promise_attribute_count_gt_operator():
    e = _entity_with(("goals", "verified"), ("goals", "proposed"))
    assert _eval_atom("promise_attribute_count:goals > 1", e) is True
    assert _eval_atom("promise_attribute_count:goals > 2", e) is False


def test_promise_attribute_count_le_lt_eq_operators():
    e = _entity_with(("goals", "verified"), ("goals", "proposed"))
    assert _eval_atom("promise_attribute_count:goals <= 2", e) is True
    assert _eval_atom("promise_attribute_count:goals <= 1", e) is False
    assert _eval_atom("promise_attribute_count:goals < 3", e) is True
    assert _eval_atom("promise_attribute_count:goals == 2", e) is True
    assert _eval_atom("promise_attribute_count:goals == 3", e) is False


def test_promise_attribute_count_ignores_other_attributes():
    """Only promises whose `attribute` matches the atom name are counted."""
    e = _entity_with(
        ("goals", "verified"),
        ("requirements", "verified"),
        ("success_criteria", "proposed"),
        ("failure_modes", "open"),
    )
    assert _eval_atom("promise_attribute_count:goals >= 1", e) is True
    assert _eval_atom("promise_attribute_count:goals == 1", e) is True
    assert _eval_atom("promise_attribute_count:constraints >= 1", e) is False


def test_promise_attribute_count_counts_all_statuses():
    """The atom ignores promise status — combine with promise_status_count if needed."""
    e = _entity_with(
        ("goals", "verified"),
        ("goals", "proposed"),
        ("goals", "open"),
    )
    assert _eval_atom("promise_attribute_count:goals >= 3", e) is True
    # No status filter is baked in.
    assert _eval_atom("promise_attribute_count:goals == 3", e) is True


def test_promise_attribute_count_handles_hyphenated_names():
    """Atom regex accepts hyphens in attribute name (e.g., `open-questions`)."""
    e = _entity_with(("open-questions", "verified"))
    assert _eval_atom("promise_attribute_count:open-questions >= 1", e) is True


def test_promise_attribute_count_composes_with_and():
    """Category B strict readiness: all 5 attrs present in one predicate."""
    e = _entity_with(
        ("goals", "verified"),
        ("requirements", "verified"),
        ("success_criteria", "verified"),
        ("failure_modes", "verified"),
        ("constraints", "verified"),
    )
    predicate = (
        "promise_attribute_count:goals >= 1"
        " and promise_attribute_count:requirements >= 1"
        " and promise_attribute_count:success_criteria >= 1"
        " and promise_attribute_count:failure_modes >= 1"
        " and promise_attribute_count:constraints >= 1"
    )
    assert _eval_predicate(predicate, e) is True


def test_promise_attribute_count_and_short_circuits_on_missing():
    """Removing one Category B attr fails the strict predicate."""
    e = _entity_with(
        ("goals", "verified"),
        ("requirements", "verified"),
        ("success_criteria", "verified"),
        ("failure_modes", "verified"),
        # constraints missing
    )
    predicate = (
        "promise_attribute_count:goals >= 1"
        " and promise_attribute_count:requirements >= 1"
        " and promise_attribute_count:success_criteria >= 1"
        " and promise_attribute_count:failure_modes >= 1"
        " and promise_attribute_count:constraints >= 1"
    )
    assert _eval_predicate(predicate, e) is False


def test_promise_attribute_count_composes_with_or():
    """Partial coverage: any Category B attr present passes the OR predicate."""
    e = _entity_with(("goals", "verified"))
    predicate = (
        "promise_attribute_count:goals >= 1"
        " or promise_attribute_count:requirements >= 1"
        " or promise_attribute_count:constraints >= 1"
    )
    assert _eval_predicate(predicate, e) is True

    empty = {"id": "E", "promises": []}
    assert _eval_predicate(predicate, empty) is False


def test_promise_attribute_count_skips_non_dict_promises():
    """Malformed promise entries (bare strings, None) are silently skipped."""
    e = {
        "id": "E",
        "promises": [
            {"attribute": "goals", "status": "verified"},
            "malformed-string",
            None,
            {"attribute": "goals", "status": "proposed"},
        ],
    }
    assert _eval_atom("promise_attribute_count:goals >= 2", e) is True
    assert _eval_atom("promise_attribute_count:goals >= 3", e) is False


def test_promise_attribute_count_distinct_from_promise_status_count():
    """The two atoms have independent semantics on the same entity."""
    e = _entity_with(
        ("goals", "verified"),
        ("goals", "proposed"),
        ("requirements", "open"),
    )
    # 2 goals promises regardless of status
    assert _eval_atom("promise_attribute_count:goals == 2", e) is True
    # 1 verified promise across all attributes
    assert _eval_atom("promise_status_count:verified == 1", e) is True
    # 1 open promise (the requirements one)
    assert _eval_atom("promise_status_count:open == 1", e) is True
