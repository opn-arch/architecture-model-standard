"""Tests for SupplementaryRef + ModelSlice.supplementary_refs (Phase 2 Task 8)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.model_slice import (
    Curation,
    ModelSlice,
    Selectors,
    SupplementaryRef,
    compute_slice_digest,
)


def _minimum_slice(**overrides):
    kwargs = dict(
        id="slice-sup-1",
        architecture_id="pkg-root",
        model_revision="sha256-v1:abc",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_kinds=["component"]),
        curation=Curation(),
    )
    kwargs.update(overrides)
    return ModelSlice(**kwargs)


# ---------------------------------------------------------------------------
# SupplementaryRef construction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "kind",
    ["manifest", "sil", "gates", "drift", "test_results", "learning"],
)
def test_supplementary_ref_accepts_all_kinds(kind):
    ref = SupplementaryRef(kind=kind)
    assert ref.kind == kind
    assert ref.path is None
    assert ref.filter is None


def test_supplementary_ref_rejects_invalid_kind():
    with pytest.raises(ValidationError):
        SupplementaryRef(kind="not-a-kind")


def test_supplementary_ref_accepts_path_and_filter():
    ref = SupplementaryRef(
        kind="sil",
        path=".architecture/sil.sqlite",
        filter={"component_id": "COMP-3"},
    )
    assert ref.path == ".architecture/sil.sqlite"
    assert ref.filter == {"component_id": "COMP-3"}


def test_supplementary_ref_is_frozen():
    ref = SupplementaryRef(kind="manifest")
    with pytest.raises(ValidationError):
        ref.kind = "sil"  # type: ignore[misc]


def test_supplementary_ref_rejects_extras():
    with pytest.raises(ValidationError):
        SupplementaryRef(kind="manifest", unexpected="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ModelSlice integration
# ---------------------------------------------------------------------------

def test_default_supplementary_refs_is_empty_tuple():
    s = _minimum_slice()
    assert s.supplementary_refs == ()


def test_slice_accepts_supplementary_refs():
    refs = (
        SupplementaryRef(kind="manifest"),
        SupplementaryRef(kind="sil", filter={"component_id": "COMP-1"}),
    )
    s = _minimum_slice(supplementary_refs=refs)
    assert len(s.supplementary_refs) == 2
    assert s.supplementary_refs[0].kind == "manifest"
    assert s.supplementary_refs[1].filter == {"component_id": "COMP-1"}


def test_slice_round_trip_preserves_supplementary_refs():
    refs = (SupplementaryRef(kind="gates"), SupplementaryRef(kind="drift"))
    s = _minimum_slice(supplementary_refs=refs)
    dumped = s.model_dump(mode="json")
    restored = ModelSlice.model_validate(dumped)
    assert restored.supplementary_refs == refs


# ---------------------------------------------------------------------------
# Digest back-compat
# ---------------------------------------------------------------------------

def test_empty_supplementary_refs_does_not_change_digest():
    """Adding the field with the empty default must not perturb pre-Phase-2 digests."""
    s_default = _minimum_slice()
    s_explicit_empty = _minimum_slice(supplementary_refs=())
    assert compute_slice_digest(s_default) == compute_slice_digest(s_explicit_empty)


def test_nonempty_supplementary_refs_changes_digest():
    baseline = compute_slice_digest(_minimum_slice())
    with_ref = compute_slice_digest(
        _minimum_slice(supplementary_refs=(SupplementaryRef(kind="manifest"),))
    )
    assert baseline != with_ref


def test_different_refs_produce_different_digests():
    a = compute_slice_digest(
        _minimum_slice(supplementary_refs=(SupplementaryRef(kind="manifest"),))
    )
    b = compute_slice_digest(
        _minimum_slice(supplementary_refs=(SupplementaryRef(kind="sil"),))
    )
    assert a != b


def test_ref_filter_participates_in_digest():
    a = compute_slice_digest(
        _minimum_slice(
            supplementary_refs=(SupplementaryRef(kind="sil", filter={"c": "1"}),)
        )
    )
    b = compute_slice_digest(
        _minimum_slice(
            supplementary_refs=(SupplementaryRef(kind="sil", filter={"c": "2"}),)
        )
    )
    assert a != b
