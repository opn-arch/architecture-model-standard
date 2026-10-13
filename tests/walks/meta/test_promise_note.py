"""Tests for promise_note meta-walk. Realizes ``CAP-WK.note``."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import list_stubs
from architecture_model.walks.meta.promise_note import (
    PromiseNoteError,
    UnknownAttributeError,
    UnknownEntityError,
    note_promise,
)


def _model_with_entity(entity_id: str, attribute: str) -> dict:
    """Minimal v3-shape model dict carrying one entity with one promise slot."""
    return {
        "meta": {"schema_version": "3.0"},
        "entities": {
            "capabilities": [
                {
                    "id": entity_id,
                    "name": "test-cap",
                    "promises": [
                        {
                            "id": f"PR-{entity_id}-{attribute}",
                            "attribute": attribute,
                            "content": [],
                            "owner_entity": entity_id,
                            "delivered_from": None,
                            "verified_by": [],
                            "status": "proposed",
                            "gap_type": "retrofit-pending",
                            "provenance": "test",
                        }
                    ],
                }
            ]
        },
    }


def _fixed_now() -> datetime:
    return datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)


def test_note_promise_appends_stub(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    stub = note_promise(
        repo_path=tmp_path,
        model=model,
        entity_id="CAP-DF.3",
        attribute="goals",
        text="Goal missing — must specify measurable outcome.",
        author="tester",
        now=_fixed_now(),
    )
    assert isinstance(stub, CommentStub)
    assert stub.target is not None
    assert stub.target.entity_id == "CAP-DF.3"
    assert stub.target.attribute == "goals"
    assert stub.body == "Goal missing — must specify measurable outcome."
    # Persisted on disk under .architecture/comments/
    saved = list(list_stubs(tmp_path))
    assert len(saved) == 1
    assert saved[0].comment_id == stub.comment_id


def test_note_promise_unknown_entity(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    with pytest.raises(UnknownEntityError):
        note_promise(
            repo_path=tmp_path,
            model=model,
            entity_id="CAP-DOES-NOT-EXIST",
            attribute="goals",
            text="body",
            author="t",
            now=_fixed_now(),
        )


def test_note_promise_unknown_attribute(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    with pytest.raises(UnknownAttributeError):
        note_promise(
            repo_path=tmp_path,
            model=model,
            entity_id="CAP-DF.3",
            attribute="does-not-exist",
            text="body",
            author="t",
            now=_fixed_now(),
        )


def test_note_promise_multiple_notes_per_promise(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    s1 = note_promise(
        repo_path=tmp_path,
        model=model,
        entity_id="CAP-DF.3",
        attribute="goals",
        text="first",
        author="a",
        now=_fixed_now(),
    )
    s2 = note_promise(
        repo_path=tmp_path,
        model=model,
        entity_id="CAP-DF.3",
        attribute="goals",
        text="second",
        author="b",
        now=_fixed_now(),
    )
    assert s1.comment_id != s2.comment_id
    saved = list(list_stubs(tmp_path))
    assert {s1.comment_id, s2.comment_id} == {s.comment_id for s in saved}


def test_note_promise_deterministic_comment_id(tmp_path: Path):
    """Same (entity, attribute, body, author, timestamp) → same comment_id."""
    from architecture_model.walks.meta.promise_note import _derive_comment_id

    cid_a = _derive_comment_id("CAP-DF.3", "goals", "body", "a", _fixed_now())
    cid_b = _derive_comment_id("CAP-DF.3", "goals", "body", "a", _fixed_now())
    assert cid_a == cid_b
    cid_c = _derive_comment_id("CAP-DF.3", "goals", "body", "b", _fixed_now())
    assert cid_a != cid_c


def test_note_promise_empty_body_rejected(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    with pytest.raises(PromiseNoteError):
        note_promise(
            repo_path=tmp_path,
            model=model,
            entity_id="CAP-DF.3",
            attribute="goals",
            text="",
            author="t",
            now=_fixed_now(),
        )


def test_note_promise_target_roundtrips_on_disk(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    stub = note_promise(
        repo_path=tmp_path,
        model=model,
        entity_id="CAP-DF.3",
        attribute="goals",
        text="roundtrip",
        author="t",
        now=_fixed_now(),
    )
    (loaded,) = list(list_stubs(tmp_path))
    assert loaded.target is not None
    assert loaded.target.entity_id == "CAP-DF.3"
    assert loaded.target.attribute == "goals"
    assert loaded.body == "roundtrip"


def test_note_promise_docstring_declares_cap_wk_note():
    """Meta-coverage discovery (Part 9 audit) requires this marker."""
    import architecture_model.walks.meta.promise_note as m

    assert m.__doc__ is not None
    assert "``CAP-WK.note``" in m.__doc__
