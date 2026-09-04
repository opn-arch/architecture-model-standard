"""ModelSlice contract: curated view spec over an architecture model.

Purpose
-------
A ``ModelSlice`` names a *reproducible curated subset* of an architecture
model. Slice specs are the input to view synthesis and artifact
generation: they answer "which subset of the model, closed under which
rules, is being rendered?" A slice is a **contract**, not a rendering —
it stores selectors + closure policy, not resolved entities.

Invariants
----------
* Frozen (``model_config = ConfigDict(frozen=True, extra="forbid")``);
  slices are immutable value objects safe to share across threads.
* ``contract_version`` is pinned to :data:`SchemaVersions.MODEL_SLICE`.
  Rejecting a mismatch is intentional: bumping the version REQUIRES a
  migration that overrides the validator.
* ``id`` is a slug (``[a-zA-Z0-9._-]+``) — spaces and empty strings are
  rejected so slice ids can be embedded in filenames and URLs.
* ``selectors`` must nominate at least one dimension; an empty slice has
  no defined semantics.
* When ``scope == "federated"`` the slice MUST bound its reach with at
  least one of ``entity_ids``/``fblocks``/``layers`` — federated with no
  bound is unbounded and forbidden.
* The **digest** (see :func:`compute_slice_digest`) excludes
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

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from architecture_model.lifecycle.serialization import digest as _digest
from architecture_model.lifecycle.versions import SchemaVersions

import re

_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

Scope = Literal["local", "descendants", "federated"]
Closure = Literal["strict", "boundary-stubs", "transitive"]
SharedRefs = Literal["none", "explicit", "transitive"]


class Selectors(BaseModel):
    """Dimensions along which the slice picks entities."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_kinds: list[str] | None = None
    entity_ids: list[str] | None = None
    layers: list[str] | None = None
    fblocks: list[str] | None = None
    tags: list[str] | None = None
    paths: list[str] | None = None  # POSIX globs

    @model_validator(mode="after")
    def _require_at_least_one(self) -> "Selectors":
        if not any(
            v is not None
            for v in (
                self.entity_kinds,
                self.entity_ids,
                self.layers,
                self.fblocks,
                self.tags,
                self.paths,
            )
        ):
            raise ValueError(
                "Selectors must nominate at least one dimension "
                "(entity_kinds, entity_ids, layers, fblocks, tags, or paths)"
            )
        return self


class Curation(BaseModel):
    """Post-selection include/exclude/redact hints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    include: list[str] | None = None
    exclude: list[str] | None = None
    redactions: list[str] | None = None


class ModelSlice(BaseModel):
    """Reproducible curated view spec over an architecture model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    contract_version: str = SchemaVersions.MODEL_SLICE
    architecture_id: str
    model_revision: str
    scope: Scope
    closure: Closure
    shared_refs: SharedRefs
    selectors: Selectors
    curation: Curation = Field(default_factory=Curation)
    parameters: dict[str, Any] = Field(default_factory=dict)
    generated_at: str | None = None
    signatures: list[dict] | None = None

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not v or not _ID_RE.match(v):
            raise ValueError(
                f"invalid slice id {v!r}: must match [A-Za-z0-9._-]+ and be non-empty"
            )
        return v

    @field_validator("architecture_id", "model_revision")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("must be a non-empty string")
        return v

    @field_validator("contract_version")
    @classmethod
    def _check_version(cls, v: str) -> str:
        if v != SchemaVersions.MODEL_SLICE:
            raise ValueError(
                f"contract_version {v!r} does not match frozen "
                f"SchemaVersions.MODEL_SLICE ({SchemaVersions.MODEL_SLICE!r})"
            )
        return v

    @model_validator(mode="after")
    def _check_federated(self) -> "ModelSlice":
        if self.scope == "federated":
            s = self.selectors
            if not any(
                v is not None
                for v in (s.entity_ids, s.fblocks, s.layers)
            ):
                raise ValueError(
                    "scope='federated' requires at least one bounding "
                    "selector (entity_ids, fblocks, or layers)"
                )
        return self


def compute_slice_digest(slice: ModelSlice) -> str:
    """Return the content digest of ``slice``.

    Excludes ``generated_at`` and ``signatures`` from the hashed payload
    so envelope metadata does not perturb identity.
    """
    payload = slice.model_dump(mode="json")
    return _digest(
        payload,
        exclude_paths=(("generated_at",), ("signatures",)),
    )


__all__ = [
    "ModelSlice",
    "Selectors",
    "Curation",
    "compute_slice_digest",
    "Scope",
    "Closure",
    "SharedRefs",
]
