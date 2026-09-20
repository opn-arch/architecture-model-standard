"""Promise-scoped note walk.

Realizes ``CAP-WK.note``.

Attaches a comment to a specific ``(entity_id, attribute)`` promise slot
on a v3 architecture model. Validates the target against the model's
entity graph, constructs a :class:`~architecture_model.comments.models.CommentStub`
with a :class:`~architecture_model.comments.models.PromiseTarget`, and
persists it via :func:`architecture_model.comments.store.write_stub`.

Tier: T1 (no LLM). Part 10 of CAP-DF Parts 10–15.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from architecture_model.comments.models import CommentStub, PromiseTarget
from architecture_model.comments.store import write_stub

# Sentinel values for view-scope fields when a note originates outside a
# rendered artifact (e.g., from a CLI or MCP call rather than a viewer).
# The comment-store schema requires all view-scope fields; promise-scoped
# notes MAY carry real artifact context later, but Part 10 only enforces
# a non-empty placeholder to keep pydantic happy.
_SENTINEL_VIEW_ID = "promise-note"
_SENTINEL_SLICE_ID = "promise-note"
_SENTINEL_PACKAGE_ID = "promise-note"
_SENTINEL_REVISION = "0000000"


class PromiseNoteError(RuntimeError):
    """Base error for promise-scoped note operations."""


class UnknownEntityError(PromiseNoteError):
    """Raised when ``entity_id`` is not present in the model."""


class UnknownAttributeError(PromiseNoteError):
    """Raised when the target entity carries no promise for ``attribute``."""


def _iter_entities(model: Mapping[str, Any]):
    """Yield every entity dict across all v3 entity kinds."""
    entities = model.get("entities") or {}
    for kind_list in entities.values():
        if not isinstance(kind_list, list):
            continue
        for ent in kind_list:
            if isinstance(ent, Mapping):
                yield ent


def _find_entity(model: Mapping[str, Any], entity_id: str) -> Mapping[str, Any] | None:
    for ent in _iter_entities(model):
        if ent.get("id") == entity_id:
            return ent
    return None


def _entity_has_attribute(entity: Mapping[str, Any], attribute: str) -> bool:
    promises = entity.get("promises") or []
    for p in promises:
        if isinstance(p, Mapping) and p.get("attribute") == attribute:
            return True
    return False


def _derive_comment_id(
    entity_id: str, attribute: str, body: str, author: str, now: datetime
) -> str:
    """Deterministic comment id: sha1 over (entity, attr, body, author, iso-time)[:12]."""
    payload = "|".join(
        [entity_id, attribute, body, author, now.astimezone(timezone.utc).isoformat()]
    ).encode("utf-8")
    return "pn-" + hashlib.sha1(payload).hexdigest()[:12]


def note_promise(
    *,
    repo_path: Path,
    model: Mapping[str, Any],
    entity_id: str,
    attribute: str,
    text: str,
    author: str,
    now: datetime | None = None,
) -> CommentStub:
    """Attach a note to ``(entity_id, attribute)`` and persist it.

    Parameters
    ----------
    repo_path
        Repository root; comments are written under
        ``.architecture/comments/<comment_id>.yaml``.
    model
        v3-shape model dict (as loaded from ``capabilities.v3.yaml``).
    entity_id
        Target entity id (must exist in ``model.entities.*``).
    attribute
        Promise attribute to target (must exist on ``entity_id``'s
        ``promises`` list).
    text
        Note body (non-empty, max 8 KiB per ``CommentStub`` constraint).
    author
        Free-form author string.
    now
        Optional injected timestamp for deterministic tests. Defaults to
        ``datetime.now(timezone.utc)``.

    Returns
    -------
    The written :class:`CommentStub`.

    Raises
    ------
    UnknownEntityError
        If ``entity_id`` is not present in ``model``.
    UnknownAttributeError
        If the entity carries no promise for ``attribute``.
    PromiseNoteError
        If ``text`` is empty or whitespace-only.
    """
    if not text or not text.strip():
        raise PromiseNoteError("note text must be non-empty")

    entity = _find_entity(model, entity_id)
    if entity is None:
        raise UnknownEntityError(f"entity_id not in model: {entity_id!r}")
    if not _entity_has_attribute(entity, attribute):
        raise UnknownAttributeError(
            f"entity {entity_id!r} has no promise for attribute {attribute!r}"
        )

    ts = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    comment_id = _derive_comment_id(entity_id, attribute, text, author, ts)

    stub = CommentStub(
        comment_id=comment_id,
        artifact_id=f"promise-note:{entity_id}:{attribute}",
        view_id=_SENTINEL_VIEW_ID,
        slice_id=_SENTINEL_SLICE_ID,
        package_id=_SENTINEL_PACKAGE_ID,
        revision=_SENTINEL_REVISION,
        target_entity_id=entity_id,
        body=text,
        author=author,
        created_at=ts,
        target=PromiseTarget(entity_id=entity_id, attribute=attribute),
    )
    write_stub(repo_path, stub)
    return stub


__all__ = [
    "PromiseNoteError",
    "UnknownEntityError",
    "UnknownAttributeError",
    "note_promise",
]
