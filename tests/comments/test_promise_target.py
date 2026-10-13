"""Tests for PromiseTarget on CommentStub. Realizes CAP-WK.note (Part 10 Task 1)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from architecture_model.comments.models import CommentStub, PromiseTarget


def _base_stub_kwargs() -> dict:
    return dict(
        comment_id="c-001",
        artifact_id="a-001",
        view_id="v-001",
        slice_id="s-001",
        package_id="p-001",
        revision="0000001",
        body="hello",
        author="tester",
        created_at=datetime(2026, 9, 18, tzinfo=timezone.utc),
    )


def test_promise_target_construction():
    t = PromiseTarget(entity_id="CAP-DF.3", attribute="goals")
    assert t.entity_id == "CAP-DF.3"
    assert t.attribute == "goals"


def test_promise_target_forbids_extra_fields():
    with pytest.raises(ValidationError):
        PromiseTarget(entity_id="CAP-DF.3", attribute="goals", extra="nope")


def test_promise_target_requires_entity_id():
    with pytest.raises(ValidationError):
        PromiseTarget(attribute="goals")


def test_promise_target_requires_attribute():
    with pytest.raises(ValidationError):
        PromiseTarget(entity_id="CAP-DF.3")


def test_promise_target_rejects_empty_strings():
    with pytest.raises(ValidationError):
        PromiseTarget(entity_id="", attribute="goals")
    with pytest.raises(ValidationError):
        PromiseTarget(entity_id="CAP-DF.3", attribute="")


def test_comment_stub_target_defaults_none():
    stub = CommentStub(**_base_stub_kwargs())
    assert stub.target is None


def test_comment_stub_accepts_target():
    stub = CommentStub(
        **_base_stub_kwargs(),
        target=PromiseTarget(entity_id="CAP-DF.3", attribute="goals"),
    )
    assert stub.target is not None
    assert stub.target.entity_id == "CAP-DF.3"
    assert stub.target.attribute == "goals"


def test_comment_stub_serializes_with_target():
    stub = CommentStub(
        **_base_stub_kwargs(),
        target=PromiseTarget(entity_id="CAP-DF.3", attribute="goals"),
    )
    dumped = stub.model_dump(mode="json")
    assert dumped["target"] == {"entity_id": "CAP-DF.3", "attribute": "goals"}


def test_comment_stub_backward_compat_no_target():
    # Existing stubs without a `target` field parse unchanged.
    payload = _base_stub_kwargs()
    payload["created_at"] = payload["created_at"].isoformat()
    stub = CommentStub.model_validate(payload)
    assert stub.target is None
