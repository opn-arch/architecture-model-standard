"""ViewSpec contract: curated view over a ModelSlice, bound to a projector.

Purpose
-------
A ``ViewSpec`` names a *reproducible rendering intent* over an immutable
``ModelSlice`` revision. It answers "which projector + configuration should
render which slice, in what kind of output?" A ViewSpec is a **contract**,
not a rendered artifact — the actual ``DiagramSpec`` / prose / table is
produced by the projector at runtime (T16).

Invariants
----------
* Frozen (``model_config = ConfigDict(frozen=True, extra="forbid")``);
  view specs are immutable value objects safe to share across threads.
* ``contract_version`` is pinned to :data:`SchemaVersions.VIEW_SPEC`.
  Rejecting a mismatch is intentional: bumping the version REQUIRES a
  migration that overrides the validator.
* ``id`` is a slug (``[A-Za-z0-9._-]+``) — spaces and empty strings are
  rejected so view ids can be embedded in filenames and URLs.
* ``slice_ref.model_revision`` is REQUIRED and non-empty. A ViewSpec is
  bound to an *immutable slice revision*: without a revision the view has
  no reproducible input and thus no reproducible output. This is a
  critical spec property; do not relax it.
* ``projector`` is a non-empty string. Registry membership is enforced at
  runtime by the projector registry (T16), not by the schema.
* ``output_content_kind`` is one of ``diagram``/``prose``/``table``.
* The **digest** (see :func:`compute_view_spec_digest`) excludes
  ``generated_at`` and ``signatures``: they are envelope metadata, not
  content, and would otherwise defeat content-addressing.

Thread safety
-------------
Instances are frozen pydantic models. All functions in this module are
pure. Safe for concurrent read access.

Error taxonomy
--------------
Construction failures raise :class:`pydantic.ValidationError` wrapping the
underlying :class:`ValueError`. This module does not define custom
exception types.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from architecture_model.lifecycle.serialization import digest as _digest
from architecture_model.lifecycle.versions import SchemaVersions

_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

OutputContentKind = Literal["diagram", "prose", "table"]


class SliceRef(BaseModel):
    """Immutable reference to a specific ModelSlice revision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slice_id: str
    model_revision: str

    @field_validator("slice_id")
    @classmethod
    def _check_slice_id(cls, v: str) -> str:
        if not v or not _ID_RE.match(v):
            raise ValueError(
                f"invalid slice_id {v!r}: must match [A-Za-z0-9._-]+ and be non-empty"
            )
        return v

    @field_validator("model_revision")
    @classmethod
    def _check_model_revision(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "slice_ref.model_revision must be a non-empty string; "
                "a ViewSpec is bound to an immutable slice revision"
            )
        return v


class ViewCuration(BaseModel):
    """Post-projection include/exclude/redact/drill-down hints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    include: list[str] | None = None
    exclude: list[str] | None = None
    redactions: list[str] | None = None
    drill_downs: list[str] | None = None


class ViewSpec(BaseModel):
    """Reproducible rendering intent over an immutable ModelSlice revision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    contract_version: str = SchemaVersions.VIEW_SPEC
    slice_ref: SliceRef
    projector: str
    projector_config: dict[str, Any] = Field(default_factory=dict)
    curation: ViewCuration = Field(default_factory=ViewCuration)
    parameters: dict[str, Any] = Field(default_factory=dict)
    output_content_kind: OutputContentKind
    generated_at: str | None = None
    signatures: list[dict] | None = None

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not v or not _ID_RE.match(v):
            raise ValueError(
                f"invalid view id {v!r}: must match [A-Za-z0-9._-]+ and be non-empty"
            )
        return v

    @field_validator("contract_version")
    @classmethod
    def _check_version(cls, v: str) -> str:
        if v != SchemaVersions.VIEW_SPEC:
            raise ValueError(
                f"contract_version {v!r} does not match frozen "
                f"SchemaVersions.VIEW_SPEC ({SchemaVersions.VIEW_SPEC!r})"
            )
        return v

    @field_validator("projector")
    @classmethod
    def _check_projector(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "projector must be a non-empty string (registry lookup at runtime)"
            )
        return v


def compute_view_spec_digest(view: ViewSpec) -> str:
    """Return the content digest of ``view``.

    Excludes ``generated_at`` and ``signatures`` from the hashed payload
    so envelope metadata does not perturb identity.
    """
    payload = view.model_dump(mode="json")
    return _digest(
        payload,
        exclude_paths=(("generated_at",), ("signatures",)),
    )


__all__ = [
    "ViewSpec",
    "SliceRef",
    "ViewCuration",
    "compute_view_spec_digest",
    "OutputContentKind",
]
