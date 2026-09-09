"""Tests for entity-scoped slice scope: ``scope='entity(<id>)'``.

Plan reference: ``docs/plans/2026-09-08-phase-3-recursion-and-entity-views.md``
Task 2. Extends the existing ``Scope`` literal (``local`` / ``descendants`` /
``descendants:each`` / ``federated``) with an entity-scoped form
``entity(<entity_id>)`` and adds a parser helper.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.model_slice import (
    ModelSlice,
    Selectors,
    compute_slice_digest,
    parse_entity_scope,
)


def _slice(**overrides) -> ModelSlice:
    kwargs = dict(
        id="s1",
        architecture_id="pkg-root",
        model_revision="sha256-v1:abc",
        scope="entity(COMP-3)",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-3"]),
    )
    kwargs.update(overrides)
    return ModelSlice(**kwargs)


def test_slice_entity_scope_round_trip():
    s = _slice()
    d = s.model_dump(mode="json", by_alias=True)
    assert d["scope"] == "entity(COMP-3)"
    s2 = ModelSlice.model_validate(d)
    assert s2 == s


def test_parse_entity_scope_valid_ids():
    assert parse_entity_scope("entity(COMP-3)") == "COMP-3"
    assert parse_entity_scope("entity(CAP-F1.2)") == "CAP-F1.2"
    assert parse_entity_scope("entity(COMP-1.1.1)") == "COMP-1.1.1"


def test_parse_entity_scope_non_entity_returns_none():
    assert parse_entity_scope("local") is None
    assert parse_entity_scope("descendants") is None
    assert parse_entity_scope("federated") is None


def test_parse_entity_scope_malformed_returns_none():
    assert parse_entity_scope("entity()") is None
    assert parse_entity_scope("entity(bad id)") is None  # space
    assert parse_entity_scope("entity(lowercase)") is None  # must start [A-Z]
    assert parse_entity_scope("entity(COMP-3") is None  # missing paren
    assert parse_entity_scope("") is None


def test_entity_scope_digest_stable():
    s1 = _slice()
    s2 = _slice()
    assert compute_slice_digest(s1) == compute_slice_digest(s2)


def test_entity_scope_digest_differs_by_id():
    s_comp3 = _slice(scope="entity(COMP-3)")
    s_comp4 = _slice(scope="entity(COMP-4)", selectors=Selectors(entity_ids=["COMP-4"]))
    assert compute_slice_digest(s_comp3) != compute_slice_digest(s_comp4)


def test_entity_scope_preserves_legacy_scope_values():
    # Sanity: extending the type must not break the existing Literal values.
    for scope in ("local", "descendants", "descendants:each"):
        s = _slice(scope=scope)
        assert s.scope == scope


def test_entity_scope_invalid_string_rejected():
    with pytest.raises(ValidationError):
        _slice(scope="not-a-real-scope")
    with pytest.raises(ValidationError):
        _slice(scope="entity()")  # empty id
    with pytest.raises(ValidationError):
        _slice(scope="entity(bad id)")  # space in id
