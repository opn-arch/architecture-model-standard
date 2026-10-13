"""Tests for author_promise_note meta-walk. Realizes ``CAP-WK.author``."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pytest
import yaml

from architecture_model.ai.jobs import JobState, JobStore
from architecture_model.ai.proposals import ModelPatch
from architecture_model.lifecycle.atomic_store import write_atomic
from architecture_model.walks.meta._prompt_assembly import assemble_promise_prompt
from architecture_model.walks.meta.author_promise_note import (
    AuthorPromiseError,
    CommentMissingError,
    EntityNotFoundError,
    JobNotQueuedError,
    NotAPromiseNoteError,
    ProviderResponseError,
    WorkOrderMissingError,
    author_promise_note,
)
from architecture_model.walks.meta.promise_note import note_promise
from architecture_model.walks.meta.save_promise_note import save_promise_note


# ---- fixtures --------------------------------------------------------


def _v3_model() -> dict:
    """Two-cap model with a single promise slot on CAP-C."""
    return {
        "meta": {"schema_version": "3.0"},
        "entities": {
            "capabilities": [
                {
                    "id": "CAP-P",
                    "name": "Parent",
                    "description": "parent cap",
                    "promises": [],
                },
                {
                    "id": "CAP-C",
                    "name": "Child",
                    "description": "child cap",
                    "promises": [
                        {
                            "id": "PR-CAP-C-goals",
                            "attribute": "goals",
                            "content": [],
                            "owner_entity": "CAP-C",
                            "delivered_from": None,
                            "verified_by": [],
                            "status": "proposed",
                            "gap_type": "retrofit-pending",
                            "provenance": "test",
                        }
                    ],
                },
            ],
            "components": [],
            "behaviors": [],
            "interfaces": [],
            "actors": [],
            "constraints": [],
            "layers": [],
        },
        "relationships": [
            {"from": "CAP-P", "to": "CAP-C", "type": "contains"},
        ],
    }


def _write_model_fragment(repo: Path) -> None:
    frag_dir = repo / ".architecture" / "model"
    frag_dir.mkdir(parents=True, exist_ok=True)
    (frag_dir / "capabilities.v3.yaml").write_text(yaml.safe_dump(_v3_model()))


class _StubProvider:
    """Simple LLMProvider stub returning a fixed content string."""

    name = "stub"

    def __init__(self, content: str = "Author-drafted goal content."):
        self._content = content
        self.calls: list[str] = []

    def complete(self, prompt, *, model=None, max_tokens=4096, temperature=0.0):
        raise NotImplementedError

    def stream(self, prompt, *, model=None, max_tokens=4096, temperature=0.0):
        raise NotImplementedError

    def structured(self, prompt: str, schema: dict, *, model=None) -> dict:
        self.calls.append(prompt)
        return {"content": self._content}

    def tokenize(self, text: str) -> int:
        return len(text.split())


class _BadProvider(_StubProvider):
    def structured(self, prompt: str, schema: dict, *, model=None) -> dict:
        return {"wrong_key": "no content field"}


def _seed_note_save_and_queue(repo: Path) -> str:
    """note → save (which auto-queues in the walk-level? no — walk-level
    returns a WorkOrder only). This helper mimics the full OCA tool flow:
    note → save-walk → persist WO + create Job → advance to queued.
    Returns the job_id."""
    _write_model_fragment(repo)

    stub = note_promise(
        repo_path=repo,
        model=_v3_model(),
        entity_id="CAP-C",
        attribute="goals",
        text="must be measurable and observable in a single e2e test",
        author="tester",
        now=datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc),
    )
    wo = save_promise_note(
        repo_path=repo,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc),
    )
    # Persist WorkOrder atomically (mirror the MCP tool's persistence).
    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(
        wo_dir / f"{wo.id}.yaml",
        yaml.safe_dump(wo.to_dict(), sort_keys=True).encode("utf-8"),
    )
    store = JobStore(root=repo)
    job = store.create(work_order_id=wo.id, actor="tester")
    store.transition(job.id, JobState.approved, actor="test")
    store.transition(job.id, JobState.queued, actor="test")
    return job.id


# ---- tests -----------------------------------------------------------


def test_happy_path_returns_model_patch(tmp_path: Path):
    job_id = _seed_note_save_and_queue(tmp_path)
    provider = _StubProvider(content="Measurable and observable in one test.")

    proposal = author_promise_note(
        repo_path=tmp_path, job_id=job_id, provider=provider
    )

    assert isinstance(proposal, ModelPatch)
    assert len(proposal.operations) == 1
    op = proposal.operations[0]
    assert op["op"] == "add"
    assert op["path"] == "entities.capabilities[id=CAP-C].goals"
    assert op["value"] == "Measurable and observable in one test."
    assert proposal.provenance.model_version.startswith("stub:")
    # provider called exactly once
    assert len(provider.calls) == 1


def test_prompt_digest_matches_sha256(tmp_path: Path):
    job_id = _seed_note_save_and_queue(tmp_path)
    provider = _StubProvider()
    proposal = author_promise_note(
        repo_path=tmp_path, job_id=job_id, provider=provider
    )
    # Recompute prompt independently and compare digests.
    assembled = assemble_promise_prompt(
        _v3_model(),
        "CAP-C",
        "goals",
        "must be measurable and observable in a single e2e test",
    )
    expected = hashlib.sha256(assembled.encode("utf-8")).hexdigest()
    assert proposal.provenance.prompt_digest == expected


def test_deterministic_prompt_across_calls(tmp_path: Path):
    """Same inputs → same prompt → identical provider invocation."""
    job_id = _seed_note_save_and_queue(tmp_path)
    p1 = _StubProvider()
    p2 = _StubProvider()
    author_promise_note(repo_path=tmp_path, job_id=job_id, provider=p1)
    author_promise_note(repo_path=tmp_path, job_id=job_id, provider=p2)
    assert p1.calls == p2.calls


def test_unknown_job_id_raises_key_error(tmp_path: Path):
    _write_model_fragment(tmp_path)
    with pytest.raises(KeyError):
        author_promise_note(
            repo_path=tmp_path, job_id="job-does-not-exist", provider=_StubProvider()
        )


def test_job_not_queued_raises(tmp_path: Path):
    """A Job left in draft state must be rejected."""
    _write_model_fragment(tmp_path)
    stub = note_promise(
        repo_path=tmp_path,
        model=_v3_model(),
        entity_id="CAP-C",
        attribute="goals",
        text="text",
        author="t",
        now=datetime(2026, 9, 18, tzinfo=timezone.utc),
    )
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="t",
        now=datetime(2026, 9, 18, tzinfo=timezone.utc),
    )
    wo_dir = tmp_path / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(
        wo_dir / f"{wo.id}.yaml",
        yaml.safe_dump(wo.to_dict(), sort_keys=True).encode("utf-8"),
    )
    store = JobStore(root=tmp_path)
    job = store.create(work_order_id=wo.id, actor="t")
    # Leave in draft.
    with pytest.raises(JobNotQueuedError):
        author_promise_note(
            repo_path=tmp_path, job_id=job.id, provider=_StubProvider()
        )


def test_workorder_missing_raises(tmp_path: Path):
    _write_model_fragment(tmp_path)
    # Create a Job pointing at a non-existent WorkOrder id.
    store = JobStore(root=tmp_path)
    job = store.create(work_order_id="wo-does-not-exist", actor="t")
    store.transition(job.id, JobState.approved, actor="t")
    store.transition(job.id, JobState.queued, actor="t")
    with pytest.raises(WorkOrderMissingError):
        author_promise_note(
            repo_path=tmp_path, job_id=job.id, provider=_StubProvider()
        )


def test_comment_missing_raises(tmp_path: Path):
    job_id = _seed_note_save_and_queue(tmp_path)
    # Delete the source comment file to simulate loss.
    comments_dir = tmp_path / ".architecture" / "comments"
    for c in comments_dir.glob("*.yaml"):
        c.unlink()
    with pytest.raises(CommentMissingError):
        author_promise_note(
            repo_path=tmp_path, job_id=job_id, provider=_StubProvider()
        )


def test_entity_not_in_model_raises(tmp_path: Path):
    """When the v3 model no longer contains the target entity."""
    job_id = _seed_note_save_and_queue(tmp_path)
    # Overwrite the model fragment with a model that lacks CAP-C.
    stripped = _v3_model()
    stripped["entities"]["capabilities"] = [
        e for e in stripped["entities"]["capabilities"] if e["id"] != "CAP-C"
    ]
    (tmp_path / ".architecture" / "model" / "capabilities.v3.yaml").write_text(
        yaml.safe_dump(stripped)
    )
    with pytest.raises(EntityNotFoundError):
        author_promise_note(
            repo_path=tmp_path, job_id=job_id, provider=_StubProvider()
        )


def test_provider_returning_bad_shape_raises(tmp_path: Path):
    job_id = _seed_note_save_and_queue(tmp_path)
    with pytest.raises(ProviderResponseError):
        author_promise_note(
            repo_path=tmp_path, job_id=job_id, provider=_BadProvider()
        )


def test_v3_model_can_be_injected(tmp_path: Path):
    """Passing v3_model explicitly bypasses on-disk fragment loading."""
    job_id = _seed_note_save_and_queue(tmp_path)
    # Even if we blow away the on-disk fragment, injection lets it proceed.
    (tmp_path / ".architecture" / "model" / "capabilities.v3.yaml").unlink()
    proposal = author_promise_note(
        repo_path=tmp_path,
        job_id=job_id,
        provider=_StubProvider(),
        v3_model=_v3_model(),
    )
    assert isinstance(proposal, ModelPatch)
