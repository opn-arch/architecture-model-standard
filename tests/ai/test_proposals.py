"""Tests for architecture_model.ai.proposals."""

from __future__ import annotations

import pytest

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
from architecture_model.ai.work_order import ProposalKind


def _prov() -> Provenance:
    return Provenance(
        work_order_id="WO-1",
        model_version="rev-abc",
        prompt_digest="sha256-v1:deadbeef",
    )


def test_all_six_types_round_trip():
    cases = [
        ModelPatch(provenance=_prov(), operations=[{"op": "add", "path": "/x", "value": 1}]),
        DecompositionProposal(
            provenance=_prov(),
            proposed_systems=[{"id": "S1", "files": ["a.py"]}],
        ),
        SliceProposal(provenance=_prov(), slice={"id": "slice-1", "selectors": {}}),
        ViewCurationProposal(
            provenance=_prov(), view_spec={"id": "view-1", "kind": "logical"}
        ),
        ArtifactCandidate(
            provenance=_prov(), artifact_spec={"id": "art-1", "kind": "doc"}
        ),
        ImpactAssessment(
            provenance=_prov(), affected_ids=["COMP-1", "COMP-2"], summary="rippling"
        ),
    ]
    for p in cases:
        d = p.to_dict()
        assert d["kind"] == p.kind.value
        p2 = type(p).from_dict(d)
        assert p2 == p


def test_kind_classvar_matches_enum():
    assert ModelPatch.kind == ProposalKind.MODEL_PATCH
    assert DecompositionProposal.kind == ProposalKind.DECOMPOSITION_PROPOSAL
    assert SliceProposal.kind == ProposalKind.SLICE_PROPOSAL
    assert ViewCurationProposal.kind == ProposalKind.VIEW_CURATION_PROPOSAL
    assert ArtifactCandidate.kind == ProposalKind.ARTIFACT_CANDIDATE
    assert ImpactAssessment.kind == ProposalKind.IMPACT_ASSESSMENT


def test_missing_provenance_raises_type_error():
    with pytest.raises(TypeError):
        ModelPatch(operations=[])  # type: ignore[call-arg]


def test_empty_prompt_digest_raises():
    with pytest.raises(ValueError, match="prompt_digest"):
        Provenance(work_order_id="WO-1", model_version="rev", prompt_digest="")


def test_proposal_from_dict_dispatches_all_kinds():
    cases = [
        (ModelPatch, {"operations": []}),
        (DecompositionProposal, {"proposed_systems": []}),
        (SliceProposal, {"slice": {"id": "s"}}),
        (ViewCurationProposal, {"view_spec": {"id": "v"}}),
        (ArtifactCandidate, {"artifact_spec": {"id": "a"}}),
        (ImpactAssessment, {"affected_ids": [], "summary": "x"}),
    ]
    for cls, extra in cases:
        p = cls(provenance=_prov(), **extra)
        d = p.to_dict()
        p2 = proposal_from_dict(d)
        assert isinstance(p2, cls)
        assert p2 == p


def test_proposal_from_dict_unknown_kind_lists_valid():
    with pytest.raises(ValueError) as excinfo:
        proposal_from_dict({"kind": "bogus", "provenance": _prov().to_dict()})
    msg = str(excinfo.value)
    for k in ProposalKind:
        assert k.value in msg


def test_proposal_types_registry_complete():
    assert set(PROPOSAL_TYPES.keys()) == set(ProposalKind)
    assert len(PROPOSAL_TYPES) == 6


def test_model_patch_empty_operations_is_valid():
    p = ModelPatch(provenance=_prov(), operations=[])
    assert p.operations == []
    d = p.to_dict()
    assert d["operations"] == []
    assert ModelPatch.from_dict(d) == p


def test_nested_dict_structure_preserved():
    nested = {
        "op": "replace",
        "path": "/entities/components/0",
        "value": {"id": "C1", "meta": {"tags": ["a", "b"], "n": 2}},
    }
    p = ModelPatch(provenance=_prov(), operations=[nested])
    d = p.to_dict()
    p2 = ModelPatch.from_dict(d)
    assert p2.operations == [nested]

    sp = SliceProposal(
        provenance=_prov(),
        slice={"id": "s", "selectors": {"fblocks": ["F1"], "meta": {"x": 1}}},
    )
    assert SliceProposal.from_dict(sp.to_dict()) == sp


def test_provenance_round_trip():
    prov = _prov()
    d = prov.to_dict()
    assert Provenance.from_dict(d) == prov
