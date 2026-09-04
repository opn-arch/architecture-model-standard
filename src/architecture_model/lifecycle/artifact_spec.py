"""ArtifactSpec contract: renderable artifact bound to a view or bundle.

Purpose
-------
An ``ArtifactSpec`` names a *renderable output* — SVG, markdown, HTML, an
AI context bundle, or a zip package aggregating other artifacts. Each
non-zip artifact binds to exactly one :class:`ViewRef` (a view + a pinned
model revision), which in turn identifies the immutable slice/model input.
Zip artifacts instead aggregate a list of sibling artifact ids.

An ArtifactSpec is a **contract** (not a rendered payload) that is
content-addressable via :func:`compute_artifact_spec_digest`.

Migration note
--------------
This module owns ``ArtifactSpec``. The prior owner
``opencode_arch.artifacts.selector`` will become a compatibility import
shim in a follow-up (opencode-arch Phase 2). Downstream imports should
be updated to ``architecture_model.lifecycle.artifact_spec``.

Invariants
----------
* Frozen (``model_config = ConfigDict(frozen=True, extra="forbid")``);
  ArtifactSpec/ViewRef/SignatureSlot are immutable value objects safe to
  share across threads.
* ``contract_version`` is pinned to :data:`SchemaVersions.ARTIFACT_SPEC`;
  mismatch raises :class:`ValueError` (wrapped by pydantic).
* ``id`` and ``view_ref.view_id`` are slugs ``[A-Za-z0-9._-]+``. Each
  entry of ``bundle_refs`` is also a slug.
* ``renderer == "zip"`` iff ``bundle_refs`` is a non-empty list of slugs
  AND ``view_ref is None``.
* ``renderer != "zip"`` iff ``view_ref`` is present AND ``bundle_refs``
  is either None or an empty list.
* ``view_ref.model_revision`` is REQUIRED and non-empty when a
  ``view_ref`` is present: a rendered artifact is bound to an *immutable
  revision* of its view input; otherwise reproducibility is lost.

Digest
------
:func:`compute_artifact_spec_digest` excludes:

* ``generated_at`` — envelope metadata (not content).
* ``signature_slots[*].signature`` — signature values are populated after
  the digest is computed; the slot's ``algorithm``/``key_id`` remain part
  of the identity (they declare which key is *expected* to sign).

Implementation strategy: pre-strip ``signature`` fields in the payload
copy before delegating to
``architecture_model.lifecycle.serialization.digest`` (which only
supports exclusion by exact key path, not glob-through-list). This is
explicit and directly unit-testable.

Thread safety
-------------
Instances are frozen pydantic models. All functions in this module are
pure. Safe for concurrent read access.

Error taxonomy
--------------
Construction failures raise :class:`pydantic.ValidationError` wrapping
the underlying :class:`ValueError`. This module does not define custom
exception types.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from architecture_model.lifecycle.serialization import digest as _digest
from architecture_model.lifecycle.versions import SchemaVersions

_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

Renderer = Literal["svg", "markdown", "html", "ai-context", "zip"]


class SignatureSlot(BaseModel):
    """Reserved slot for detached signatures (crypto is Phase 2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: str
    key_id: str
    signature: str | None = None

    @field_validator("algorithm")
    @classmethod
    def _check_algorithm(cls, v: str) -> str:
        if not v:
            raise ValueError("signature slot algorithm must be non-empty")
        return v

    @field_validator("key_id")
    @classmethod
    def _check_key_id(cls, v: str) -> str:
        if not v:
            raise ValueError("signature slot key_id must be non-empty")
        return v


class ViewRef(BaseModel):
    """Immutable reference to a ViewSpec at a specific model revision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    view_id: str
    model_revision: str

    @field_validator("view_id")
    @classmethod
    def _check_view_id(cls, v: str) -> str:
        if not v or not _ID_RE.match(v):
            raise ValueError(
                f"invalid view_id {v!r}: must match [A-Za-z0-9._-]+ and be non-empty"
            )
        return v

    @field_validator("model_revision")
    @classmethod
    def _check_model_revision(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "view_ref.model_revision must be a non-empty string; "
                "ArtifactSpec is bound to an immutable view revision"
            )
        return v


class ArtifactSpec(BaseModel):
    """Renderable-artifact contract bound to a view or an aggregation of siblings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    contract_version: str = SchemaVersions.ARTIFACT_SPEC
    renderer: Renderer
    view_ref: ViewRef | None = None
    bundle_refs: list[str] | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    signature_slots: list[SignatureSlot] = Field(default_factory=list)
    generated_at: str | None = None

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not v or not _ID_RE.match(v):
            raise ValueError(
                f"invalid artifact id {v!r}: must match [A-Za-z0-9._-]+ and be non-empty"
            )
        return v

    @field_validator("contract_version")
    @classmethod
    def _check_version(cls, v: str) -> str:
        if v != SchemaVersions.ARTIFACT_SPEC:
            raise ValueError(
                f"contract_version {v!r} does not match frozen "
                f"SchemaVersions.ARTIFACT_SPEC ({SchemaVersions.ARTIFACT_SPEC!r})"
            )
        return v

    @field_validator("bundle_refs")
    @classmethod
    def _check_bundle_ref_slugs(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        for i, ref in enumerate(v):
            if not isinstance(ref, str) or not ref or not _ID_RE.match(ref):
                raise ValueError(
                    f"bundle_refs[{i}] {ref!r} must match [A-Za-z0-9._-]+ and be non-empty"
                )
        return v

    @model_validator(mode="after")
    def _check_renderer_shape(self) -> "ArtifactSpec":
        if self.renderer == "zip":
            if self.view_ref is not None:
                raise ValueError(
                    "renderer='zip' artifacts must not carry a view_ref; "
                    "zip artifacts aggregate sibling artifact ids via bundle_refs"
                )
            if not self.bundle_refs:
                raise ValueError(
                    "renderer='zip' artifacts require a non-empty bundle_refs list"
                )
        else:
            if self.view_ref is None:
                raise ValueError(
                    f"renderer={self.renderer!r} artifacts require a view_ref"
                )
            if self.bundle_refs:
                raise ValueError(
                    f"renderer={self.renderer!r} artifacts must not carry bundle_refs "
                    "(only renderer='zip' aggregates siblings)"
                )
        return self


def compute_artifact_spec_digest(artifact: ArtifactSpec) -> str:
    """Return the content digest of ``artifact``.

    Excludes ``generated_at`` (envelope metadata) and every
    ``signature_slots[*].signature`` (populated *after* digest by the
    signer). The slot's ``algorithm``/``key_id`` remain part of the
    identity.
    """
    payload = artifact.model_dump(mode="json")
    slots = payload.get("signature_slots")
    if isinstance(slots, list):
        stripped_slots = []
        for slot in slots:
            if isinstance(slot, dict):
                stripped = {k: v for k, v in slot.items() if k != "signature"}
                stripped["signature"] = None
                stripped_slots.append(stripped)
            else:
                stripped_slots.append(slot)
        payload["signature_slots"] = stripped_slots
    return _digest(payload, exclude_paths=(("generated_at",),))


__all__ = [
    "ArtifactSpec",
    "SignatureSlot",
    "ViewRef",
    "Renderer",
    "compute_artifact_spec_digest",
]
