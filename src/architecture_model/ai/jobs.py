"""AI Job state machine and persistence.

A :class:`Job` tracks the lifecycle of an AI :class:`WorkOrder` through
approval, queueing, execution, validation, and terminal outcomes. State
transitions are governed by :data:`ALLOWED_TRANSITIONS`; every transition
appends an immutable :class:`JobEvent` to :attr:`Job.history` and emits
an ``ai.job.transition`` event on the lifecycle
:class:`~architecture_model.lifecycle.journal.Journal`.

Persistence is per-job YAML at
``<root>/.architecture/ai/jobs/<job_id>.yaml`` written atomically via
:func:`architecture_model.lifecycle.atomic_store.write_atomic`.

This module implements state + persistence only. Execution (dequeue,
worker, dispatch) is intentionally out of scope.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from architecture_model.lifecycle.atomic_store import write_atomic
from architecture_model.lifecycle.journal import Journal
from architecture_model.lifecycle.serialization import (
    canonical_yaml_load,
    digest as _digest,
)
from architecture_model.lifecycle.versions import SchemaVersions


class JobState(str, Enum):
    draft = "draft"
    approved = "approved"
    queued = "queued"
    running = "running"
    validating = "validating"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.draft: frozenset({JobState.approved, JobState.cancelled}),
    JobState.approved: frozenset({JobState.queued, JobState.cancelled}),
    JobState.queued: frozenset({JobState.running, JobState.cancelled}),
    JobState.running: frozenset(
        {JobState.validating, JobState.failed, JobState.cancelled}
    ),
    JobState.validating: frozenset({JobState.completed, JobState.failed}),
    JobState.completed: frozenset(),
    JobState.failed: frozenset(),
    JobState.cancelled: frozenset(),
}


class InvalidTransitionError(Exception):
    """Raised when a requested state transition is not allowed."""

    def __init__(
        self,
        from_state: JobState,
        to_state: JobState,
        allowed: frozenset[JobState],
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed
        allowed_names = sorted(s.value for s in allowed)
        super().__init__(
            f"invalid transition {from_state.value} -> {to_state.value}; "
            f"allowed: {allowed_names}"
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobEvent:
    from_state: JobState | None
    to_state: JobState
    at: str
    reason: str | None = None
    actor: str = "system"

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state.value if self.from_state is not None else None,
            "to_state": self.to_state.value,
            "at": self.at,
            "reason": self.reason,
            "actor": self.actor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobEvent":
        fs = data.get("from_state")
        return cls(
            from_state=JobState(fs) if fs is not None else None,
            to_state=JobState(data["to_state"]),
            at=data["at"],
            reason=data.get("reason"),
            actor=data.get("actor", "system"),
        )


@dataclass
class Job:
    id: str
    work_order_id: str
    created_at: str
    updated_at: str
    state: JobState = JobState.draft
    contract_version: str = SchemaVersions.AI_JOB
    history: list[JobEvent] = field(default_factory=list)
    result_ref: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "contract_version": self.contract_version,
            "work_order_id": self.work_order_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "history": [e.to_dict() for e in self.history],
            "result_ref": self.result_ref,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        return cls(
            id=data["id"],
            contract_version=data.get("contract_version", SchemaVersions.AI_JOB),
            work_order_id=data["work_order_id"],
            state=JobState(data.get("state", JobState.draft.value)),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            history=[JobEvent.from_dict(e) for e in data.get("history", [])],
            result_ref=data.get("result_ref"),
            error=data.get("error"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


class JobStore:
    """Filesystem-backed job store.

    Jobs are persisted per-file under
    ``<root>/.architecture/ai/jobs/<job_id>.yaml``. All writes go through
    :func:`write_atomic`. Transitions are journalled via the optional
    :class:`Journal` (defaults to
    ``<root>/.architecture/ai/jobs.journal.jsonl``).
    """

    def __init__(self, root: Path, *, journal: Journal | None = None) -> None:
        self.root = Path(root)
        self._dir = self.root / ".architecture" / "ai" / "jobs"
        if journal is None:
            journal = Journal(self.root / ".architecture" / "ai" / "jobs.journal.jsonl")
        self._journal = journal

    # -- paths -----------------------------------------------------------

    def _path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.yaml"

    # -- CRUD ------------------------------------------------------------

    def create(
        self,
        work_order_id: str,
        *,
        actor: str = "system",
        job_id: str | None = None,
    ) -> Job:
        if job_id is None:
            job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        creation_event = JobEvent(
            from_state=None,
            to_state=JobState.draft,
            at=now,
            reason=None,
            actor=actor,
        )
        job = Job(
            id=job_id,
            work_order_id=work_order_id,
            state=JobState.draft,
            contract_version=SchemaVersions.AI_JOB,
            created_at=now,
            updated_at=now,
            history=[creation_event],
        )
        self._write(job)
        return job

    def get(self, job_id: str) -> Job:
        path = self._path(job_id)
        if not path.exists():
            raise KeyError(job_id)
        data = canonical_yaml_load(path.read_text(encoding="utf-8"))
        return Job.from_dict(data)

    def list_ids(self) -> list[str]:
        if not self._dir.exists():
            return []
        return sorted(p.stem for p in self._dir.glob("*.yaml"))

    def transition(
        self,
        job_id: str,
        new_state: JobState,
        *,
        reason: str | None = None,
        actor: str = "system",
        result_ref: str | None = None,
        error: str | None = None,
    ) -> Job:
        job = self.get(job_id)
        allowed = ALLOWED_TRANSITIONS[job.state]
        if new_state not in allowed:
            raise InvalidTransitionError(job.state, new_state, allowed)
        if new_state == JobState.completed and not result_ref:
            raise ValueError(
                "result_ref is required when transitioning to 'completed'"
            )
        if new_state == JobState.failed and not error:
            raise ValueError(
                "error is required when transitioning to 'failed'"
            )
        from_state = job.state
        now = _now_iso()
        event = JobEvent(
            from_state=from_state,
            to_state=new_state,
            at=now,
            reason=reason,
            actor=actor,
        )
        job.state = new_state
        job.updated_at = now
        job.history.append(event)
        if result_ref is not None:
            job.result_ref = result_ref
        if error is not None:
            job.error = error
        self._write(job)
        self._journal.record(
            "ai.job.transition",
            {
                "job_id": job_id,
                "from_state": from_state.value,
                "to_state": new_state.value,
                "reason": reason,
                "actor": actor,
            },
        )
        return job

    # -- internals -------------------------------------------------------

    def _write(self, job: Job) -> None:
        text = yaml.safe_dump(
            job.to_dict(),
            sort_keys=True,
            default_flow_style=False,
            allow_unicode=True,
        )
        write_atomic(self._path(job.id), text.encode("utf-8"))
