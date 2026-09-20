"""Pydantic schemas for comment stubs. See
docs/plans/2026-09-05-comment-view-shared-interfaces-design.md §2."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_REVISION_RE = r"^\d{7}$"
_MAX_BODY_BYTES = 8192


class IssueRef(BaseModel):
    """Reference to an external issue-tracker record backing this comment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    system: Literal["logs-db"] = "logs-db"
    issue_id: int | str | None = None
    synced_at: Optional[datetime] = None


class PromiseTarget(BaseModel):
    """Pointer to a specific promise slot on a v3 entity.

    Used by CAP-WK.note (Part 10) to attach comments to (entity_id,
    attribute) tuples rather than freeform bodies. Additive: existing
    stubs without a `target` field continue to parse unchanged.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_id: str = Field(..., min_length=1)
    attribute: str = Field(..., min_length=1)


class CommentStub(BaseModel):
    """Local, authoritative record of a user comment on a lifecycle-rendered view."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    comment_id: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    view_id: str = Field(..., min_length=1)
    slice_id: str = Field(..., min_length=1)
    package_id: str = Field(..., min_length=1)
    revision: str = Field(..., pattern=_REVISION_RE)
    target_entity_id: Optional[str] = None
    body: str
    author: str
    created_at: datetime
    issue_ref: Optional[IssueRef] = None
    target: Optional[PromiseTarget] = None

    @field_validator("body")
    @classmethod
    def _body_size(cls, v: str) -> str:
        if len(v.encode("utf-8")) > _MAX_BODY_BYTES:
            raise ValueError(f"body exceeds {_MAX_BODY_BYTES} bytes")
        return v
