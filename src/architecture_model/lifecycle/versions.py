"""Frozen contract versions for the architecture lifecycle.

This module is the single source of truth for the schema version of every
persisted artifact in the architecture lifecycle: models, packages,
manifests, model slices, view specs, artifact specs, and AI work orders.

Invariants:

* Every persisted artifact declares a ``schema_version`` matching the
  constant defined here for its :class:`ContractKind`.
* Bumping any constant in this module REQUIRES a matching migration in
  ``architecture_model.lifecycle.migrations`` and a documented terminology
  update in ``terminology.md``.
* The ``DIGEST_ALGO`` constant identifies the canonicalization + hash
  algorithm used to compute content-addressed revisions; changing it is a
  breaking change for every stored revision id.
* Enum values are hyphen-cased lowercase strings so they round-trip
  cleanly through JSON Schema ``enum`` declarations without translation.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class ContractKind(str, Enum):
    """Every kind of persisted lifecycle artifact."""

    MODEL = "model"
    PACKAGE = "package"
    MANIFEST = "manifest"
    MODEL_SLICE = "model-slice"
    VIEW_SPEC = "view-spec"
    ARTIFACT_SPEC = "artifact-spec"
    AI_WORK_ORDER = "ai-work-order"


class SchemaVersions:
    """Frozen schema versions for each :class:`ContractKind`."""

    MODEL: Final[str] = "2.1.0"
    PACKAGE: Final[str] = "1.0.0"
    MANIFEST: Final[str] = "1.0.0"
    MODEL_SLICE: Final[str] = "1.0.0"
    VIEW_SPEC: Final[str] = "1.0.0"
    ARTIFACT_SPEC: Final[str] = "1.0.0"
    AI_WORK_ORDER: Final[str] = "1.0.0"
    # Alias for AI_WORK_ORDER used by architecture_model.ai.work_order.
    WORK_ORDER: Final[str] = "1.0.0"

    DIGEST_ALGO: Final[str] = "sha256-v1"

    _BY_KIND: Final[dict[ContractKind, str]] = {
        ContractKind.MODEL: MODEL,
        ContractKind.PACKAGE: PACKAGE,
        ContractKind.MANIFEST: MANIFEST,
        ContractKind.MODEL_SLICE: MODEL_SLICE,
        ContractKind.VIEW_SPEC: VIEW_SPEC,
        ContractKind.ARTIFACT_SPEC: ARTIFACT_SPEC,
        ContractKind.AI_WORK_ORDER: AI_WORK_ORDER,
    }

    @classmethod
    def for_kind(cls, kind: ContractKind) -> str:
        """Return the frozen schema version for the given contract kind."""
        return cls._BY_KIND[kind]
