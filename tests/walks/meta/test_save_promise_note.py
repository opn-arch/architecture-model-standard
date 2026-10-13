"""Tests for save_promise_note meta-walk. Realizes ``CAP-WK.save``."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from architecture_model.ai.work_order import ProposalKind, WorkOrder
from architecture_model.comments.models import CommentStub, PromiseTarget
from architecture_model.comments.store import write_stub
from architecture_model.walks.meta.promise_note import note_promise
from architecture_model.walks.meta.save_promise_note import (
    NotAPromiseNoteError,
    SavePromiseNoteError,
    save_promise_note,
)


def _model_with_entity(entity_id: str, attribute: str) -> dict:
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


def _seed_note(tmp_path: Path) -> CommentStub:
    return note_promise(
        repo_path=tmp_path,
        model=_model_with_entity("CAP-DF.3", "goals"),
        entity_id="CAP-DF.3",
        attribute="goals",
        text="need measurable outcome",
        author="tester",
        now=_fixed_now(),
    )


def test_save_returns_workorder(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert isinstance(wo, WorkOrder)
    assert wo.intent == "fill_promise:CAP-DF.3:goals"
    assert wo.requested_by == "tester"


def test_save_workorder_carries_promise_parameters(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    params = dict(wo.parameters)
    assert params["kind"] == "fill_promise"
    assert params["entity_id"] == "CAP-DF.3"
    assert params["attribute"] == "goals"
    assert params["source_comment_id"] == stub.comment_id
    assert params["note_body"] == "need measurable outcome"


def test_save_workorder_accepts_model_patch(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert list(wo.expected_proposal_kinds) == [ProposalKind.MODEL_PATCH]


def test_save_workorder_t2_budget(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert wo.budget.max_tokens == 8000
    assert wo.budget.max_wall_seconds == 120


def test_save_workorder_synthetic_slice(tmp_path: Path):
    """Option A: walk builds a synthetic SliceRef with promise-slot:
    prefix. Part 12's author walk detects this prefix and materializes
    on demand. WorkOrder's bounded-input rule requires non-empty
    input_slice_refs.
    """
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert len(wo.input_slice_refs) == 1
    ref = wo.input_slice_refs[0]
    assert ref.slice_id == "promise-slot:CAP-DF.3:goals"
    assert isinstance(ref.model_revision, str)
    assert len(ref.model_revision) == 7
    assert ref.model_revision.isdigit()


def test_save_workorder_deterministic_id(tmp_path: Path):
    """Same (comment_id, requested_by, now) → same WorkOrder id."""
    stub = _seed_note(tmp_path)
    wo_a = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    wo_b = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert wo_a.id == wo_b.id


def test_save_rejects_non_promise_note(tmp_path: Path):
    """CommentStub without a `target` cannot be saved."""
    stub = CommentStub(
        comment_id="freeform-001",
        artifact_id="a-1",
        view_id="v-1",
        slice_id="s-1",
        package_id="p-1",
        revision="0000001",
        target_entity_id="COMP-X",
        body="freeform comment (no promise target)",
        author="tester",
        created_at=_fixed_now(),
    )
    write_stub(tmp_path, stub)
    with pytest.raises(NotAPromiseNoteError):
        save_promise_note(
            repo_path=tmp_path,
            comment_id="freeform-001",
            requested_by="tester",
            now=_fixed_now(),
        )


def test_save_missing_comment(tmp_path: Path):
    with pytest.raises(SavePromiseNoteError):
        save_promise_note(
            repo_path=tmp_path,
            comment_id="does-not-exist",
            requested_by="tester",
            now=_fixed_now(),
        )


def test_save_docstring_declares_cap_wk_save():
    """Meta-coverage discovery (Part 9 audit) requires this marker."""
    import architecture_model.walks.meta.save_promise_note as m

    assert m.__doc__ is not None
    assert "``CAP-WK.save``" in m.__doc__
