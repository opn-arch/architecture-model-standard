"""Author-promise-note walk.

Realizes ``CAP-WK.author``.

Given a queued Job (produced by ``architect_promise_save``) and an
:class:`~architecture_model.llm.provider.LLMProvider`, load the linked
WorkOrder + CommentStub, assemble a hand-rolled v3-native prompt via
:func:`_prompt_assembly.assemble_promise_prompt`, invoke
``provider.structured(...)``, and return a
:class:`~architecture_model.ai.proposals.ModelPatch` proposal.

The walk itself is **pure** — it does not transition Job state, does not
persist the Proposal, and does not touch the model. Job lifecycle +
Proposal persistence live in the OCA MCP tool ``architect_promise_author``.

Tier: T2 (LLM-review). Part 12 of CAP-DF Parts 10–15.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from architecture_model.ai.jobs import JobState, JobStore
from architecture_model.ai.proposals import ModelPatch, Provenance
from architecture_model.ai.work_order import WorkOrder
from architecture_model.comments.store import StubMissingError, load_stub
from architecture_model.core.v3_loader import load_v3_model
from architecture_model.llm.provider import LLMProvider
from architecture_model.walks.meta._prompt_assembly import (
    assemble_promise_prompt,
    default_template_body,
)

_FILL_PROMISE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"content": {"type": "string"}},
    "required": ["content"],
}


class AuthorPromiseError(RuntimeError):
    """Base error for the author-promise-note walk."""


class JobNotQueuedError(AuthorPromiseError):
    """Raised when the Job is not in ``queued`` state."""


class WorkOrderMissingError(AuthorPromiseError):
    """Raised when the Job's linked WorkOrder file is absent."""


class CommentMissingError(AuthorPromiseError):
    """Raised when the WorkOrder's ``source_comment_id`` cannot be loaded."""


class NotAPromiseNoteError(AuthorPromiseError):
    """Raised when the CommentStub has no ``target`` (not a promise note)."""


class EntityNotFoundError(AuthorPromiseError):
    """Raised when the target entity is not present in the v3 model."""


class ProviderResponseError(AuthorPromiseError):
    """Raised when the provider response does not conform to the schema."""


def _load_workorder(repo_path: Path, work_order_id: str) -> WorkOrder:
    import yaml

    wo_path = (
        repo_path / ".architecture" / "ai" / "workorders" / f"{work_order_id}.yaml"
    )
    if not wo_path.exists():
        raise WorkOrderMissingError(
            f"WorkOrder not found: {work_order_id!r} at {wo_path}"
        )
    data = yaml.safe_load(wo_path.read_text(encoding="utf-8"))
    return WorkOrder.from_dict(data)


def author_promise_note(
    *,
    repo_path: Path,
    job_id: str,
    provider: LLMProvider,
    v3_model: Mapping[str, Any] | None = None,
    template_body: str | None = None,
    now: datetime | None = None,
) -> ModelPatch:
    """Author the target promise's attribute content via an LLM provider.

    Parameters
    ----------
    repo_path
        Repository root; JobStore + WorkOrder store + comment store live under
        ``.architecture/`` here.
    job_id
        Identifier of a Job in state ``queued`` whose linked WorkOrder was
        produced by ``architect_promise_save`` (intent ``fill_promise:...``).
    provider
        Any :class:`LLMProvider` — the walk only calls ``.structured()``
        and reads ``.name``.
    v3_model
        Optional pre-loaded v3 model dict. When ``None``, the walk calls
        :func:`load_v3_model` scoped to ``repo_path``.
    template_body
        Optional prompt template body. When ``None``, the walk resolves
        the default via :func:`default_template_body`.
    now
        Unused; kept for API symmetry with earlier walks.

    Returns
    -------
    A :class:`ModelPatch` with a single ``add`` operation targeting
    ``entities.<kind>[id=<entity_id>].<attribute>``. Not persisted.

    Raises
    ------
    JobNotQueuedError, WorkOrderMissingError, CommentMissingError,
    NotAPromiseNoteError, EntityNotFoundError, ProviderResponseError
        See individual class docstrings.
    KeyError
        Propagated from ``JobStore.get`` when ``job_id`` is unknown.
    """
    del now  # unused

    repo_path = Path(repo_path)
    store = JobStore(root=repo_path)
    job = store.get(job_id)
    if job.state != JobState.queued:
        raise JobNotQueuedError(
            f"job {job_id!r} in state {job.state.value!r}; expected 'queued'"
        )

    wo = _load_workorder(repo_path, job.work_order_id)

    params = wo.parameters or {}
    entity_id = params.get("entity_id")
    attribute = params.get("attribute")
    source_comment_id = params.get("source_comment_id")
    if not entity_id or not attribute or not source_comment_id:
        raise AuthorPromiseError(
            f"WorkOrder {wo.id!r} missing required fill_promise parameters"
        )

    try:
        stub = load_stub(repo_path, source_comment_id)
    except StubMissingError as exc:
        raise CommentMissingError(
            f"source comment not found: {source_comment_id!r}"
        ) from exc

    if stub.target is None:
        raise NotAPromiseNoteError(
            f"comment {source_comment_id!r} has no promise target"
        )

    note_body = stub.body

    if v3_model is None:
        # load_v3_model uses cwd-based defaults; scope to repo_path.
        model_path = repo_path / ".architecture-model.v3.yaml"
        if not model_path.exists():
            model_path = repo_path / ".architecture-model.yaml"
            if not model_path.exists():
                # Fall back to the capabilities.v3.yaml fragment authored
                # under .architecture/model — this is what the notes/save
                # walks read too.
                model_path = (
                    repo_path
                    / ".architecture"
                    / "model"
                    / "capabilities.v3.yaml"
                )
        fragment_dir = repo_path / ".architecture" / "model"
        v3_model = load_v3_model(
            model_path=model_path if model_path.exists() else None,
            fragment_dir=fragment_dir if fragment_dir.exists() else None,
        )

    # Verify entity is present up-front so we raise a precise error before
    # burning a provider call.
    try:
        prompt = assemble_promise_prompt(
            v3_model,
            entity_id,
            attribute,
            note_body,
            template_body=template_body or default_template_body(repo_path),
        )
    except KeyError as exc:
        raise EntityNotFoundError(
            f"entity {entity_id!r} not found in v3 model"
        ) from exc

    response = provider.structured(prompt, _FILL_PROMISE_SCHEMA)
    content = response.get("content") if isinstance(response, Mapping) else None
    if not isinstance(content, str) or not content:
        raise ProviderResponseError(
            f"provider {provider.name!r} returned invalid response: "
            f"expected object with non-empty 'content' string, got {response!r}"
        )

    # Locate the entity's kind for the JSON-patch path.
    kind: str | None = None
    for k, ents in (v3_model.get("entities") or {}).items():
        if any(
            isinstance(e, Mapping) and e.get("id") == entity_id
            for e in ents or []
        ):
            kind = k
            break
    if kind is None:  # pragma: no cover — assemble_promise_prompt already checked
        raise EntityNotFoundError(f"entity {entity_id!r} not found in v3 model")

    operation = {
        "op": "add",
        "path": f"entities.{kind}[id={entity_id}].{attribute}",
        "value": content,
    }

    prompt_digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    model_revision = (
        wo.input_slice_refs[0].model_revision if wo.input_slice_refs else "0000000"
    )
    provenance = Provenance(
        work_order_id=wo.id,
        model_version=f"{provider.name}:{model_revision}",
        prompt_digest=prompt_digest,
    )
    return ModelPatch(provenance=provenance, operations=[operation])


__all__ = [
    "AuthorPromiseError",
    "CommentMissingError",
    "EntityNotFoundError",
    "JobNotQueuedError",
    "NotAPromiseNoteError",
    "ProviderResponseError",
    "WorkOrderMissingError",
    "author_promise_note",
]
