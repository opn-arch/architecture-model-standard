"""Tests for ViewSpec.depth + expand_kinds (Phase 3 Task 5).

Adds two optional fields to :class:`ViewSpec` for entity-scoped recursion
controls:

- ``depth: int = 1`` — how many ``contains`` levels to descend.
  ``depth == 0`` renders only the scope root; ``depth < 0`` is rejected.
- ``expand_kinds: tuple[str, ...] = ()`` — which entity kinds recurse
  (empty tuple means "all kinds recurse", matching the pre-Phase-3
  default).

Backwards compatibility: both fields default to their zero values and
must be stripped from the view digest when unset so pre-Phase-3 view
digests stay byte-stable.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.view_spec import (
    SliceRef,
    ViewSpec,
    compute_view_spec_digest,
)


def _spec(**overrides) -> ViewSpec:
    kwargs = dict(
        id="v1",
        slice_ref=SliceRef(slice_id="s1", model_revision="rev-1"),
        projector="family1.entity_page",
        output_content_kind="prose",
    )
    kwargs.update(overrides)
    return ViewSpec(**kwargs)


def test_view_spec_defaults_depth_and_expand_kinds():
    v = _spec()
    assert v.depth == 1
    assert v.expand_kinds == ()


def test_view_spec_depth_zero_is_valid():
    v = _spec(depth=0)
    assert v.depth == 0


def test_view_spec_depth_positive_is_valid():
    v = _spec(depth=3)
    assert v.depth == 3


def test_view_spec_negative_depth_rejected():
    with pytest.raises(ValidationError):
        _spec(depth=-1)


def test_view_spec_expand_kinds_populated():
    v = _spec(expand_kinds=("component", "capability"))
    assert v.expand_kinds == ("component", "capability")


def test_view_spec_expand_kinds_empty_string_rejected():
    with pytest.raises(ValidationError):
        _spec(expand_kinds=("component", ""))


def test_view_spec_digest_stable_when_defaults():
    """Digest of a spec with only default depth/expand_kinds must equal
    the digest computed without those fields present (back-compat)."""
    v = _spec()
    d = compute_view_spec_digest(v)
    assert isinstance(d, str) and len(d) > 0
    # Recomputing yields identical result.
    assert compute_view_spec_digest(_spec()) == d


def test_view_spec_digest_differs_on_depth():
    d1 = compute_view_spec_digest(_spec(depth=1))
    d2 = compute_view_spec_digest(_spec(depth=2))
    assert d1 != d2


def test_view_spec_digest_differs_on_expand_kinds():
    d_empty = compute_view_spec_digest(_spec())
    d_kind = compute_view_spec_digest(_spec(expand_kinds=("component",)))
    assert d_empty != d_kind


def test_view_spec_round_trip_preserves_new_fields():
    v = _spec(depth=2, expand_kinds=("capability",))
    payload = v.model_dump(mode="json")
    assert payload["depth"] == 2
    assert payload["expand_kinds"] == ["capability"]
    v2 = ViewSpec.model_validate(payload)
    assert v2 == v
