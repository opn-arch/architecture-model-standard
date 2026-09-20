"""Save-promise-note walk.

Realizes ``CAP-WK.save``.

Reads a promise note produced by :func:`architecture_model.walks.meta.
promise_note.note_promise` and constructs an
:class:`~architecture_model.ai.work_order.WorkOrder` targeting the
noted ``(entity_id, attribute)`` promise slot. The WorkOrder is
returned; persistence + Job creation happen in the OCA MCP tool
``architect_promise_save`` which reuses the WorkOrder store + JobStore
+ Journal primitives.

Tier: T1 (no LLM). Part 11 of CAP-DF Parts 10–15.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from architecture_model.ai.work_order import ProposalKind, SliceRef, WorkOrder
from architecture_model.comments.store import StubMissingError, load_stub
from architecture_model.lifecycle.publication import (
    GENERATION_ZERO_PAD,
    ArchitecturePackage,
    read_current_generation,
)

# Tier T2 (LLM-review) default budget — matches CAP-DF Parts 10–15 design.
_MAX_TOKENS = 8000
_MAX_WALL_SECONDS = 120

# Synthetic slice_id prefix. Part 12's author walk detects this prefix and
# materializes an entity-scoped slice on demand. See CAP-DF Part 11 plan
# (Option A: defer materialization to Part 12).
_PROMISE_SLOT_PREFIX = "promise-slot"


def _current_revision(repo_path: Path) -> str:
    """Return the current architecture package generation as a 7-digit
    zero-padded string, or ``"0000000"`` when no package has been
    published in this repo.
    """
    try:
        pkg = ArchitecturePackage(root=repo_path / ".architecture")
        n = read_current_generation(pkg)
    except Exception:
        n = None
    if n is None:
        return "0" * GENERATION_ZERO_PAD
    return f"{n:0{GENERATION_ZERO_PAD}d}"


class SavePromiseNoteError(RuntimeError):
    """Base error for save-promise-note operations."""


class NotAPromiseNoteError(SavePromiseNoteError):
    """Raised when the loaded stub has no ``target`` (not a promise note)."""


def save_promise_note(
    *,
    repo_path: Path,
    comment_id: str,
    requested_by: str,
    now: datetime | None = None,
    parameters: Mapping[str, Any] | None = None,
) -> WorkOrder:
    """Build a WorkOrder from a promise-note CommentStub.

    Parameters
    ----------
    repo_path
        Repository root; comment is loaded from
        ``.architecture/comments/<comment_id>.yaml``.
    comment_id
        Identifier of the promise note (produced by ``note_promise``).
    requested_by
        Free-form actor id recorded on the WorkOrder.
    now
        Optional injected timestamp for deterministic WorkOrder ids.
    parameters
        Optional extra parameters to merge with the auto-derived
        ``fill_promise`` payload. Reserved keys (``kind``, ``entity_id``,
        ``attribute``, ``source_comment_id``, ``note_body``) always win.

    Returns
    -------
    The constructed :class:`WorkOrder` (not yet persisted).

    Raises
    ------
    SavePromiseNoteError
        If the comment does not exist.
    NotAPromiseNoteError
        If the loaded stub has no ``target`` (freeform comment, not a
        promise note).
    """
    try:
        stub = load_stub(repo_path, comment_id)
    except StubMissingError as exc:
        raise SavePromiseNoteError(f"comment not found: {comment_id!r}") from exc

    if stub.target is None:
        raise NotAPromiseNoteError(
            f"comment {comment_id!r} has no promise target — "
            "cannot save as fill_promise WorkOrder"
        )

    ts = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    base_params: dict[str, Any] = dict(parameters or {})
    # Reserved keys — override any caller-provided value.
    base_params.update(
        {
            "kind": "fill_promise",
            "entity_id": stub.target.entity_id,
            "attribute": stub.target.attribute,
            "source_comment_id": stub.comment_id,
            "note_body": stub.body,
        }
    )

    intent = f"fill_promise:{stub.target.entity_id}:{stub.target.attribute}"

    # Option A: build a synthetic SliceRef targeting the promise slot.
    # Part 12's author walk detects the "promise-slot:" prefix and
    # materializes an entity-scoped slice on demand. WorkOrder's
    # bounded-input rule requires input_slice_refs to be non-empty.
    synthetic_slice = SliceRef(
        slice_id=f"{_PROMISE_SLOT_PREFIX}:{stub.target.entity_id}:{stub.target.attribute}",
        model_revision=_current_revision(repo_path),
    )

    return WorkOrder.build(
        intent=intent,
        slices=[synthetic_slice],
        accepts=[ProposalKind.MODEL_PATCH],
        requested_by=requested_by,
        max_tokens=_MAX_TOKENS,
        max_wall_seconds=_MAX_WALL_SECONDS,
        parameters=base_params,
        created_at=ts,
    )


__all__ = [
    "NotAPromiseNoteError",
    "SavePromiseNoteError",
    "save_promise_note",
]
