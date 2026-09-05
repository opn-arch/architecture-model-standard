"""Typed AI proposal contracts.

One dataclass per :class:`ProposalKind`. Each proposal carries mandatory
:class:`Provenance` linking it back to the originating work order and the
model revision + prompt the agent was given.

Serialization: every proposal exposes ``to_dict`` / ``from_dict`` with a
top-level ``kind`` discriminator; :func:`proposal_from_dict` dispatches
on that value using :data:`PROPOSAL_TYPES`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Union

from architecture_model.ai.work_order import ProposalKind


@dataclass(frozen=True)
class Provenance:
    """Where a proposal came from."""

    work_order_id: str
    model_version: str
    prompt_digest: str

    def __post_init__(self) -> None:
        if not self.prompt_digest:
            raise ValueError("provenance.prompt_digest must be non-empty")
        if not self.work_order_id:
            raise ValueError("provenance.work_order_id must be non-empty")
        if not self.model_version:
            raise ValueError("provenance.model_version must be non-empty")

    def to_dict(self) -> dict[str, str]:
        return {
            "work_order_id": self.work_order_id,
            "model_version": self.model_version,
            "prompt_digest": self.prompt_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Provenance":
        return cls(
            work_order_id=data["work_order_id"],
            model_version=data["model_version"],
            prompt_digest=data["prompt_digest"],
        )


def _clone_list_of_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Preserve nested structure exactly; dataclasses are frozen, so we copy
    # defensively at construction/serialization boundaries.
    return [dict(item) for item in items]


@dataclass(frozen=True)
class ModelPatch:
    """JSON-patch-like operations against model entities."""

    provenance: Provenance
    operations: list[dict[str, Any]] = field(default_factory=list)

    kind: ClassVar[ProposalKind] = ProposalKind.MODEL_PATCH

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "provenance": self.provenance.to_dict(),
            "operations": list(self.operations),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelPatch":
        return cls(
            provenance=Provenance.from_dict(data["provenance"]),
            operations=list(data.get("operations", [])),
        )


@dataclass(frozen=True)
class DecompositionProposal:
    """Proposed system decomposition."""

    provenance: Provenance
    proposed_systems: list[dict[str, Any]] = field(default_factory=list)

    kind: ClassVar[ProposalKind] = ProposalKind.DECOMPOSITION_PROPOSAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "provenance": self.provenance.to_dict(),
            "proposed_systems": list(self.proposed_systems),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecompositionProposal":
        return cls(
            provenance=Provenance.from_dict(data["provenance"]),
            proposed_systems=list(data.get("proposed_systems", [])),
        )


@dataclass(frozen=True)
class SliceProposal:
    """Proposed new ModelSlice (spec-shaped dict)."""

    provenance: Provenance
    slice: dict[str, Any] = field(default_factory=dict)

    kind: ClassVar[ProposalKind] = ProposalKind.SLICE_PROPOSAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "provenance": self.provenance.to_dict(),
            "slice": dict(self.slice),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SliceProposal":
        return cls(
            provenance=Provenance.from_dict(data["provenance"]),
            slice=dict(data.get("slice", {})),
        )


@dataclass(frozen=True)
class ViewCurationProposal:
    """Proposed curated view spec."""

    provenance: Provenance
    view_spec: dict[str, Any] = field(default_factory=dict)

    kind: ClassVar[ProposalKind] = ProposalKind.VIEW_CURATION_PROPOSAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "provenance": self.provenance.to_dict(),
            "view_spec": dict(self.view_spec),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ViewCurationProposal":
        return cls(
            provenance=Provenance.from_dict(data["provenance"]),
            view_spec=dict(data.get("view_spec", {})),
        )


@dataclass(frozen=True)
class ArtifactCandidate:
    """Proposed artifact spec (candidate for generation)."""

    provenance: Provenance
    artifact_spec: dict[str, Any] = field(default_factory=dict)

    kind: ClassVar[ProposalKind] = ProposalKind.ARTIFACT_CANDIDATE

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "provenance": self.provenance.to_dict(),
            "artifact_spec": dict(self.artifact_spec),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactCandidate":
        return cls(
            provenance=Provenance.from_dict(data["provenance"]),
            artifact_spec=dict(data.get("artifact_spec", {})),
        )


@dataclass(frozen=True)
class ImpactAssessment:
    """Structured impact statement over a set of entity ids."""

    provenance: Provenance
    affected_ids: list[str] = field(default_factory=list)
    summary: str = ""

    kind: ClassVar[ProposalKind] = ProposalKind.IMPACT_ASSESSMENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "provenance": self.provenance.to_dict(),
            "affected_ids": list(self.affected_ids),
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImpactAssessment":
        return cls(
            provenance=Provenance.from_dict(data["provenance"]),
            affected_ids=list(data.get("affected_ids", [])),
            summary=data.get("summary", ""),
        )


Proposal = Union[
    ModelPatch,
    DecompositionProposal,
    SliceProposal,
    ViewCurationProposal,
    ArtifactCandidate,
    ImpactAssessment,
]


PROPOSAL_TYPES: dict[ProposalKind, type] = {
    ProposalKind.MODEL_PATCH: ModelPatch,
    ProposalKind.DECOMPOSITION_PROPOSAL: DecompositionProposal,
    ProposalKind.SLICE_PROPOSAL: SliceProposal,
    ProposalKind.VIEW_CURATION_PROPOSAL: ViewCurationProposal,
    ProposalKind.ARTIFACT_CANDIDATE: ArtifactCandidate,
    ProposalKind.IMPACT_ASSESSMENT: ImpactAssessment,
}


def proposal_from_dict(data: dict[str, Any]) -> Proposal:
    """Dispatch to the concrete proposal type by ``data["kind"]``."""
    raw_kind = data.get("kind")
    try:
        kind = ProposalKind(raw_kind)
    except ValueError:
        valid = ", ".join(k.value for k in ProposalKind)
        from architecture_model.core.errors import ParseError
        raise ParseError(
            f"unknown proposal kind {raw_kind!r}; valid kinds: {valid}"
        ) from None
    cls = PROPOSAL_TYPES[kind]
    return cls.from_dict(data)
