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

SupplementaryKind = Literal[
    "manifest",
    "sil",
    "gates",
    "drift",
    "test_results",
    "learning",
]

_GEN_RE = re.compile(r"^\d{7}$")
# Loose ISO-8601 UTC guard: YYYY-MM-DDTHH:MM:SS(.fff)?Z
_ISO_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
)


class RevisionRange(BaseModel):
    """Bounded range over published architecture-package generations.

    ``from_`` and ``to`` are 7-digit generation ids (e.g. ``"0000001"``);
    both endpoints are inclusive. Serialization uses ``from`` (the
    field name is aliased to avoid the Python keyword).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    from_: str = Field(alias="from")
    to: str

    @field_validator("from_", "to")
    @classmethod
    def _check_gen_id(cls, v: str) -> str:
        if not _GEN_RE.match(v):
            raise ValueError(
                f"generation id {v!r} must match ^\\d{{7}}$ (e.g. '0000001')"
            )
        return v

    @model_validator(mode="after")
    def _check_order(self) -> "RevisionRange":
        if self.from_ > self.to:
            raise ValueError(
                f"revision range must be ascending: from={self.from_!r} "
                f"to={self.to!r}"
            )
        return self


class TimeWindow(BaseModel):
    """Bounded ISO-8601 UTC window.

    ``from_`` is inclusive; ``to`` is exclusive (half-open interval)
    matching the SI&L loader's ``since`` / ``until`` semantics.
    Serialization uses ``from``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    from_: str = Field(alias="from")
    to: str

    @field_validator("from_", "to")
    @classmethod
    def _check_iso_utc(cls, v: str) -> str:
        if not _ISO_UTC_RE.match(v):
            raise ValueError(
                f"timestamp {v!r} must be ISO-8601 UTC "
                "(YYYY-MM-DDTHH:MM:SS[.fff]Z)"
            )
        return v

    @model_validator(mode="after")
    def _check_order(self) -> "TimeWindow":
        if self.from_ >= self.to:
            raise ValueError(
                f"time window must be strictly ascending: from={self.from_!r} "
                f"to={self.to!r}"
            )
        return self


class SupplementaryRef(BaseModel):
    """Reference to non-model data attached to a slice (Phase 2, schema 2.1).

    ``SupplementaryRef`` names an out-of-model data source that a projector
    or renderer needs alongside the entity graph — the AST manifest, SI&L
    events, gate/drift/test-result feedback journals, or the learning
    store. The materializer resolves each ref to a bounded fragment;
    empty tuples on ``ModelSlice.supplementary_refs`` mean "model-only".

    ``kind`` is a closed enum; ``path`` optionally overrides the
    well-known repo-relative location; ``filter`` is a kind-specific
    scoping dict (e.g. ``{"component_id": "COMP-3"}`` for ``sil``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: SupplementaryKind
    path: str | None = None
    filter: dict[str, Any] | None = None


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
    # Phase 2 (schema 2.1): supplementary out-of-model data references.
    # Empty tuple ((), the default) means "model-only" and is excluded
    # from the slice digest so pre-Phase-2 content-hashes remain stable.
    supplementary_refs: tuple[SupplementaryRef, ...] = ()
    # Phase 2 Task 11: temporal fields. Both None-default and excluded
    # from the digest when unset so pre-Phase-2 slice digests remain stable.
    revision_range: RevisionRange | None = None
    time_window: TimeWindow | None = None
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
    payload = slice.model_dump(mode="json", by_alias=True)
    # Back-compat: when supplementary_refs is empty (the default, i.e.
    # the pre-Phase-2 shape), strip it from the hashed payload so
    # content-addressed lookups of pre-Phase-2 slices remain stable.
    if not payload.get("supplementary_refs"):
        payload.pop("supplementary_refs", None)
    # Same rule for temporal fields (Phase 2 Task 11): when unset, they
    # must not perturb pre-Phase-2 digests.
    if payload.get("revision_range") is None:
        payload.pop("revision_range", None)
    if payload.get("time_window") is None:
        payload.pop("time_window", None)
    return _digest(
        payload,
        exclude_paths=(("generated_at",), ("signatures",)),
    )


__all__ = [
    "ModelSlice",
    "Selectors",
    "Curation",
    "SupplementaryRef",
    "SupplementaryKind",
    "RevisionRange",
    "TimeWindow",
    "compute_slice_digest",
    "Scope",
    "Closure",
    "SharedRefs",
]
