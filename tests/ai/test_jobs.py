"""Tests for architecture_model.ai.jobs — Job state machine + persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from architecture_model.ai.jobs import (
    ALLOWED_TRANSITIONS,
    InvalidTransitionError,
    Job,
    JobEvent,
    JobState,
    JobStore,
)
from architecture_model.lifecycle.journal import Journal
from architecture_model.lifecycle.versions import SchemaVersions


# --- Enum + transitions ---------------------------------------------------

def test_jobstate_has_eight_values():
    values = {s.value for s in JobState}
    assert values == {
        "draft",
        "approved",
        "queued",
        "running",
        "validating",
        "completed",
        "failed",
        "cancelled",
    }
    assert len(list(JobState)) == 8


def test_allowed_transitions_matches_spec():
    assert ALLOWED_TRANSITIONS[JobState.draft] == frozenset(
        {JobState.approved, JobState.cancelled}
    )
    assert ALLOWED_TRANSITIONS[JobState.approved] == frozenset(
        {JobState.queued, JobState.cancelled}
    )
    assert ALLOWED_TRANSITIONS[JobState.queued] == frozenset(
        {JobState.running, JobState.cancelled}
    )
    assert ALLOWED_TRANSITIONS[JobState.running] == frozenset(
        {JobState.validating, JobState.failed, JobState.cancelled}
    )
    assert ALLOWED_TRANSITIONS[JobState.validating] == frozenset(
        {JobState.completed, JobState.failed}
    )
    assert ALLOWED_TRANSITIONS[JobState.completed] == frozenset()
    assert ALLOWED_TRANSITIONS[JobState.failed] == frozenset()
    assert ALLOWED_TRANSITIONS[JobState.cancelled] == frozenset()
    assert set(ALLOWED_TRANSITIONS.keys()) == set(JobState)


def test_terminal_states_have_empty_allowed_sets():
    for terminal in (JobState.completed, JobState.failed, JobState.cancelled):
        assert ALLOWED_TRANSITIONS[terminal] == frozenset()


# --- JobStore basics ------------------------------------------------------

def test_create_produces_draft_job_and_persists(tmp_path: Path):
    store = JobStore(tmp_path)
    job = store.create("wo-123", actor="alice", job_id="job-1")
    assert job.state == JobState.draft
    assert job.work_order_id == "wo-123"
    assert job.contract_version == SchemaVersions.AI_JOB
    persisted = tmp_path / ".architecture" / "ai" / "jobs" / "job-1.yaml"
    assert persisted.exists()
    # creation event
    assert len(job.history) == 1
    assert job.history[0].from_state is None
    assert job.history[0].to_state == JobState.draft
    assert job.history[0].actor == "alice"


def test_create_auto_generates_unique_ids(tmp_path: Path):
    store = JobStore(tmp_path)
    a = store.create("wo-1")
    b = store.create("wo-2")
    assert a.id != b.id
    assert a.id and b.id


def test_get_after_create_roundtrips(tmp_path: Path):
    store = JobStore(tmp_path)
    original = store.create("wo-x", job_id="job-r")
    loaded = store.get("job-r")
    assert loaded.to_dict() == original.to_dict()


def test_get_unknown_raises_keyerror(tmp_path: Path):
    store = JobStore(tmp_path)
    with pytest.raises(KeyError):
        store.get("nope")


def test_list_ids_returns_sorted(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="job-c")
    store.create("wo-1", job_id="job-a")
    store.create("wo-1", job_id="job-b")
    assert store.list_ids() == ["job-a", "job-b", "job-c"]


# --- Transitions ----------------------------------------------------------

def test_valid_transition_draft_to_approved(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j")
    job = store.transition("j", JobState.approved, reason="ready", actor="bob")
    assert job.state == JobState.approved
    assert len(job.history) == 2
    ev = job.history[-1]
    assert ev.from_state == JobState.draft
    assert ev.to_state == JobState.approved
    assert ev.reason == "ready"
    assert ev.actor == "bob"


def test_valid_full_lifecycle_to_completed(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j")
    store.transition("j", JobState.approved)
    store.transition("j", JobState.queued)
    store.transition("j", JobState.running)
    store.transition("j", JobState.validating)
    job = store.transition("j", JobState.completed, result_ref="digest:abc")
    assert job.state == JobState.completed
    assert job.result_ref == "digest:abc"
    assert len(job.history) == 6  # create + 5 transitions


def test_invalid_transition_raises_with_attributes(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j")
    with pytest.raises(InvalidTransitionError) as exc_info:
        store.transition("j", JobState.completed, result_ref="digest:x")
    err = exc_info.value
    assert err.from_state == JobState.draft
    assert err.to_state == JobState.completed
    assert err.allowed == frozenset({JobState.approved, JobState.cancelled})


def test_transition_from_terminal_state_raises(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j")
    store.transition("j", JobState.cancelled, reason="user")
    with pytest.raises(InvalidTransitionError) as exc_info:
        store.transition("j", JobState.approved)
    assert exc_info.value.allowed == frozenset()


def test_completed_without_result_ref_raises(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j")
    store.transition("j", JobState.approved)
    store.transition("j", JobState.queued)
    store.transition("j", JobState.running)
    store.transition("j", JobState.validating)
    with pytest.raises(ValueError, match="result_ref"):
        store.transition("j", JobState.completed)


def test_failed_without_error_raises(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j")
    store.transition("j", JobState.approved)
    store.transition("j", JobState.queued)
    store.transition("j", JobState.running)
    with pytest.raises(ValueError, match="error"):
        store.transition("j", JobState.failed)


def test_every_transition_appends_one_event(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j")
    j1 = store.transition("j", JobState.approved, reason="r1", actor="a1")
    assert len(j1.history) == 2
    j2 = store.transition("j", JobState.queued, reason="r2", actor="a2")
    assert len(j2.history) == 3
    last = j2.history[-1]
    assert last.from_state == JobState.approved
    assert last.to_state == JobState.queued
    assert last.reason == "r2"
    assert last.actor == "a2"


def test_updated_at_changes_created_at_stable(tmp_path: Path):
    import time

    store = JobStore(tmp_path)
    j0 = store.create("wo-1", job_id="j")
    time.sleep(0.005)
    j1 = store.transition("j", JobState.approved)
    assert j1.created_at == j0.created_at
    assert j1.updated_at != j0.updated_at


def test_journal_receives_event_on_transition(tmp_path: Path):
    journal_path = tmp_path / "journal.jsonl"
    journal = Journal(journal_path)
    store = JobStore(tmp_path, journal=journal)
    store.create("wo-1", job_id="j")
    store.transition("j", JobState.approved, reason="go", actor="alice")
    text = journal_path.read_text(encoding="utf-8")
    assert "ai.job.transition" in text
    # parse each line
    lines = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    matches = [e for e in lines if e["event"] == "ai.job.transition"]
    assert len(matches) == 1
    payload = matches[0]["payload"]
    assert payload["job_id"] == "j"
    assert payload["from_state"] == "draft"
    assert payload["to_state"] == "approved"
    assert payload["reason"] == "go"
    assert payload["actor"] == "alice"


def test_to_dict_from_dict_roundtrip(tmp_path: Path):
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j", actor="alice")
    store.transition("j", JobState.approved, reason="r", actor="bob")
    job = store.get("j")
    data = job.to_dict()
    restored = Job.from_dict(data)
    assert restored.to_dict() == data
    assert restored.state == JobState.approved
    assert all(isinstance(e, JobEvent) for e in restored.history)


def test_equal_content_produces_equal_digest():
    ev = JobEvent(
        from_state=None,
        to_state=JobState.draft,
        at="2026-01-01T00:00:00+00:00",
        reason=None,
        actor="system",
    )
    a = Job(
        id="j",
        work_order_id="wo",
        state=JobState.draft,
        contract_version=SchemaVersions.AI_JOB,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        history=[ev],
    )
    b = Job(
        id="j",
        work_order_id="wo",
        state=JobState.draft,
        contract_version=SchemaVersions.AI_JOB,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        history=[ev],
    )
    assert a.digest() == b.digest()


def test_sequential_transitions_read_from_disk(tmp_path: Path):
    """Two transitions on same id via separate get() calls must yield 2 events."""
    store = JobStore(tmp_path)
    store.create("wo-1", job_id="j")
    # First transition
    store.transition("j", JobState.approved)
    # Simulate a fresh store instance (no in-memory cache)
    store2 = JobStore(tmp_path)
    j2 = store2.transition("j", JobState.queued)
    assert j2.state == JobState.queued
    # create + approved + queued
    assert len(j2.history) == 3
    assert j2.history[-1].to_state == JobState.queued
    assert j2.history[-1].from_state == JobState.approved
