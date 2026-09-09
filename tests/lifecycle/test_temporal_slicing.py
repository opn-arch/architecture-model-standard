"""Tests for temporal slicing fields (Phase 2 Task 11).

Covers ``RevisionRange``, ``TimeWindow`` types and their integration on
``ModelSlice`` — validation, serialization aliasing (``from`` not
``from_``), digest back-compat when unset, and digest sensitivity when
set.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from architecture_model.lifecycle.model_slice import (
    Curation,
    ModelSlice,
    RevisionRange,
    Selectors,
    TimeWindow,
    compute_slice_digest,
)


def _slice(**overrides) -> ModelSlice:
    kwargs = dict(
        id="s1",
        architecture_id="pkg-root",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_kinds=["component"]),
        curation=Curation(),
    )
    kwargs.update(overrides)
    return ModelSlice(**kwargs)


# ---------------------------------------------------------------------------
# RevisionRange
# ---------------------------------------------------------------------------

def test_revision_range_construction():
    rr = RevisionRange(from_="0000001", to="0000005")
    assert rr.from_ == "0000001"
    assert rr.to == "0000005"


def test_revision_range_accepts_alias_from_construction():
    """Callers wiring pydantic from dict must be able to use ``from``."""
    rr = RevisionRange.model_validate({"from": "0000002", "to": "0000004"})
    assert rr.from_ == "0000002"
    assert rr.to == "0000004"


def test_revision_range_serializes_with_alias():
    rr = RevisionRange(from_="0000001", to="0000005")
    dumped = rr.model_dump(by_alias=True)
    assert dumped == {"from": "0000001", "to": "0000005"}
    assert "from_" not in dumped


def test_revision_range_rejects_non_7digit():
    with pytest.raises(ValidationError):
        RevisionRange(from_="1", to="0000005")
    with pytest.raises(ValidationError):
        RevisionRange(from_="0000001", to="abcdefg")


def test_revision_range_rejects_descending():
    with pytest.raises(ValidationError):
        RevisionRange(from_="0000005", to="0000001")


def test_revision_range_allows_equal_endpoints():
    rr = RevisionRange(from_="0000003", to="0000003")
    assert rr.from_ == rr.to


def test_revision_range_is_frozen():
    rr = RevisionRange(from_="0000001", to="0000002")
    with pytest.raises(ValidationError):
        rr.to = "0000003"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TimeWindow
# ---------------------------------------------------------------------------

def test_time_window_construction():
    tw = TimeWindow(from_="2026-08-01T00:00:00Z", to="2026-08-08T00:00:00Z")
    assert tw.from_ == "2026-08-01T00:00:00Z"


def test_time_window_accepts_alias():
    tw = TimeWindow.model_validate(
        {"from": "2026-08-01T00:00:00Z", "to": "2026-08-02T00:00:00Z"}
    )
    assert tw.from_ == "2026-08-01T00:00:00Z"


def test_time_window_serializes_with_alias():
    tw = TimeWindow(from_="2026-08-01T00:00:00Z", to="2026-08-02T00:00:00Z")
    assert tw.model_dump(by_alias=True) == {
        "from": "2026-08-01T00:00:00Z",
        "to": "2026-08-02T00:00:00Z",
    }


def test_time_window_rejects_non_iso():
    with pytest.raises(ValidationError):
        TimeWindow(from_="2026-08-01", to="2026-08-02T00:00:00Z")
    with pytest.raises(ValidationError):
        TimeWindow(from_="not-a-time", to="2026-08-02T00:00:00Z")


def test_time_window_rejects_non_ascending():
    with pytest.raises(ValidationError):
        TimeWindow(from_="2026-08-02T00:00:00Z", to="2026-08-01T00:00:00Z")
    # equal endpoints rejected (strict ascending, half-open interval)
    with pytest.raises(ValidationError):
        TimeWindow(from_="2026-08-01T00:00:00Z", to="2026-08-01T00:00:00Z")


def test_time_window_accepts_fractional_seconds():
    tw = TimeWindow(
        from_="2026-08-01T00:00:00.123Z", to="2026-08-01T00:00:01Z"
    )
    assert tw.from_.endswith(".123Z")


# ---------------------------------------------------------------------------
# ModelSlice integration
# ---------------------------------------------------------------------------

def test_slice_defaults_temporal_fields_to_none():
    s = _slice()
    assert s.revision_range is None
    assert s.time_window is None


def test_slice_accepts_revision_range():
    rr = RevisionRange(from_="0000001", to="0000005")
    s = _slice(revision_range=rr)
    assert s.revision_range == rr


def test_slice_accepts_time_window():
    tw = TimeWindow(from_="2026-08-01T00:00:00Z", to="2026-08-08T00:00:00Z")
    s = _slice(time_window=tw)
    assert s.time_window == tw


def test_slice_round_trip_preserves_temporal_fields():
    rr = RevisionRange(from_="0000001", to="0000003")
    tw = TimeWindow(from_="2026-08-01T00:00:00Z", to="2026-08-02T00:00:00Z")
    s = _slice(revision_range=rr, time_window=tw)
    dumped = s.model_dump(mode="json", by_alias=True)
    # Aliasing must project through the full slice envelope.
    assert dumped["revision_range"] == {"from": "0000001", "to": "0000003"}
    assert dumped["time_window"] == {
        "from": "2026-08-01T00:00:00Z",
        "to": "2026-08-02T00:00:00Z",
    }
    restored = ModelSlice.model_validate(dumped)
    assert restored.revision_range == rr
    assert restored.time_window == tw


# ---------------------------------------------------------------------------
# Digest back-compat + sensitivity
# ---------------------------------------------------------------------------

def test_unset_temporal_fields_do_not_change_digest():
    """Adding temporal fields with default None must not perturb pre-Phase-2 digests."""
    a = compute_slice_digest(_slice())
    # Explicit None passes should also match the default digest.
    b = compute_slice_digest(_slice(revision_range=None, time_window=None))
    assert a == b


def test_setting_revision_range_changes_digest():
    baseline = compute_slice_digest(_slice())
    with_rr = compute_slice_digest(
        _slice(revision_range=RevisionRange(from_="0000001", to="0000002"))
    )
    assert baseline != with_rr


def test_setting_time_window_changes_digest():
    baseline = compute_slice_digest(_slice())
    with_tw = compute_slice_digest(
        _slice(
            time_window=TimeWindow(
                from_="2026-08-01T00:00:00Z", to="2026-08-02T00:00:00Z"
            )
        )
    )
    assert baseline != with_tw


def test_different_temporal_windows_produce_different_digests():
    a = compute_slice_digest(
        _slice(revision_range=RevisionRange(from_="0000001", to="0000002"))
    )
    b = compute_slice_digest(
        _slice(revision_range=RevisionRange(from_="0000001", to="0000003"))
    )
    assert a != b
