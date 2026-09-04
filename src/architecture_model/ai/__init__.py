"""AI contracts: work orders and proposals for architecture-model reasoning."""

from architecture_model.ai.work_order import (
    Budget,
    ProposalKind,
    SliceRef,
    WorkOrder,
)
from architecture_model.ai.proposals import (
    ArtifactCandidate,
    DecompositionProposal,
    ImpactAssessment,
    ModelPatch,
    PROPOSAL_TYPES,
    Provenance,
    SliceProposal,
    ViewCurationProposal,
    proposal_from_dict,
)

__all__ = [
    "Budget",
    "ProposalKind",
    "SliceRef",
    "WorkOrder",
    "Provenance",
    "ModelPatch",
    "DecompositionProposal",
    "SliceProposal",
    "ViewCurationProposal",
    "ArtifactCandidate",
    "ImpactAssessment",
    "PROPOSAL_TYPES",
    "proposal_from_dict",
]
