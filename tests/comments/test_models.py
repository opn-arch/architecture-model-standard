from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from architecture_model.comments.models import CommentStub, IssueRef

def _base_kwargs():
    return dict(
        comment_id="c-0001",
        artifact_id="art-1",
        view_id="view-1",
        slice_id="slice-1",
        package_id="pkg-1",
        revision="0000042",
        body="something is off",
        author="user@example.com",
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

def test_stub_minimal_valid():
    stub = CommentStub(**_base_kwargs())
    assert stub.issue_ref is None
    assert stub.target_entity_id is None

def test_stub_revision_must_be_seven_digits():
    with pytest.raises(ValidationError):
        CommentStub(**{**_base_kwargs(), "revision": "42"})

def test_stub_body_size_cap():
    with pytest.raises(ValidationError):
        CommentStub(**{**_base_kwargs(), "body": "x" * 8193})

def test_issue_ref_backfill():
    ref = IssueRef(system="logs-db", issue_id=123, synced_at=datetime.now(timezone.utc))
    stub = CommentStub(**_base_kwargs(), issue_ref=ref)
    assert stub.issue_ref.issue_id == 123
