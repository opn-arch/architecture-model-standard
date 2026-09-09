"""Tests for ViewCuration.overlays (Phase 2 Task 13).

Overlays are ordered, non-empty string slots on ViewCuration. Projectors
that understand an overlay name fold it into the rendered output; unknown
names are silently ignored (see architecture_model.lifecycle.overlays).

Digest back-compat: an empty ``overlays`` tuple MUST be stripped from the
view digest payload so pre-Phase-2 view digests remain byte-stable.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.view_spec import (
    SliceRef,
    ViewCuration,
    ViewSpec,
    compute_view_spec_digest,
)


def _minimum_view(**overrides):
    kwargs = dict(
        id="view-conops-1",
        slice_ref=SliceRef(slice_id="slice-1", model_revision="sha256-v1:abc"),
        projector="se.conops",
        output_content_kind="diagram",
    )
    kwargs.update(overrides)
    return ViewSpec(**kwargs)


def test_overlays_default_empty_tuple():
    v = _minimum_view()
    assert v.curation.overlays == ()


def test_overlays_roundtrip_preserves_order():
    curation = ViewCuration(overlays=("sil", "drift", "gates"))
    v = _minimum_view(curation=curation)
    dumped = v.model_dump()
    restored = ViewSpec.model_validate(dumped)
    # tuples become lists via model_dump; the field coerces back to tuple
    assert restored.curation.overlays == ("sil", "drift", "gates")


def test_overlays_order_preserved_in_dump():
    curation = ViewCuration(overlays=("drift", "sil"))
    v = _minimum_view(curation=curation)
    dumped = v.model_dump()
    assert list(dumped["curation"]["overlays"]) == ["drift", "sil"]


def test_empty_overlays_do_not_change_digest():
    """Back-compat: default empty overlays must yield the pre-Phase-2 digest."""
    v_default = _minimum_view()
    v_explicit_empty = _minimum_view(curation=ViewCuration(overlays=()))
    assert compute_view_spec_digest(v_default) == compute_view_spec_digest(
        v_explicit_empty
    )


def test_nonempty_overlays_change_digest():
    v_no = _minimum_view()
    v_yes = _minimum_view(curation=ViewCuration(overlays=("sil",)))
    assert compute_view_spec_digest(v_no) != compute_view_spec_digest(v_yes)


def test_overlays_order_affects_digest():
    v_a = _minimum_view(curation=ViewCuration(overlays=("sil", "drift")))
    v_b = _minimum_view(curation=ViewCuration(overlays=("drift", "sil")))
    assert compute_view_spec_digest(v_a) != compute_view_spec_digest(v_b)


def test_reject_empty_string_overlay():
    with pytest.raises(ValidationError):
        ViewCuration(overlays=("",))


def test_reject_non_string_overlay():
    with pytest.raises(ValidationError):
        ViewCuration(overlays=(123,))  # type: ignore[arg-type]


def test_curation_is_frozen():
    curation = ViewCuration(overlays=("sil",))
    with pytest.raises(ValidationError):
        curation.overlays = ("drift",)  # type: ignore[misc]


def test_duplicate_overlay_names_allowed_but_order_preserved():
    """Deduplication is the projector's concern; the spec preserves declared order."""
    curation = ViewCuration(overlays=("sil", "sil", "drift"))
    assert curation.overlays == ("sil", "sil", "drift")
