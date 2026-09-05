from datetime import datetime, timezone
from pathlib import Path
import pytest
from architecture_model.comments.models import CommentStub, IssueRef
from architecture_model.comments.store import (
    write_stub, load_stub, list_stubs, StubExistsError,
)

def _stub(cid="c-0001", rev="0000042"):
    return CommentStub(
        comment_id=cid, artifact_id="art-1", view_id="v-1",
        slice_id="s-1", package_id="p-1", revision=rev,
        body="x", author="a", created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

def test_write_and_load(tmp_path):
    write_stub(tmp_path, _stub())
    loaded = load_stub(tmp_path, "c-0001")
    assert loaded.comment_id == "c-0001"

def test_duplicate_id_rejected(tmp_path):
    write_stub(tmp_path, _stub())
    with pytest.raises(StubExistsError):
        write_stub(tmp_path, _stub())

def test_list_stubs_all_and_by_revision(tmp_path):
    write_stub(tmp_path, _stub("c-1", "0000001"))
    write_stub(tmp_path, _stub("c-2", "0000002"))
    write_stub(tmp_path, _stub("c-3", "0000002"))
    assert {s.comment_id for s in list_stubs(tmp_path)} == {"c-1", "c-2", "c-3"}
    assert {s.comment_id for s in list_stubs(tmp_path, revision="0000002")} == {"c-2", "c-3"}

def test_backfill_issue_ref(tmp_path):
    write_stub(tmp_path, _stub())
    ref = IssueRef(issue_id=42, synced_at=datetime.now(timezone.utc))
    from architecture_model.comments.store import set_issue_ref
    set_issue_ref(tmp_path, "c-0001", ref)
    assert load_stub(tmp_path, "c-0001").issue_ref.issue_id == 42
