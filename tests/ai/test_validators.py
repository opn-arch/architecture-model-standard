"""Tests for typed proposal validators (Task 22)."""

from __future__ import annotations

import copy

import pytest

from architecture_model.ai.proposals import (
    ArtifactCandidate,
    DecompositionProposal,
    ImpactAssessment,
    ModelPatch,
    Provenance,
    SliceProposal,
    ViewCurationProposal,
)
from architecture_model.ai.validators import (
    PROPOSAL_VALIDATORS,
    ValidationFinding,
    ValidationReport,
    validate,
    validate_artifact_candidate,
    validate_decomposition_proposal,
    validate_impact_assessment,
    validate_model_patch,
    validate_slice_proposal,
    validate_view_curation_proposal,
)
from architecture_model.ai.work_order import (
    Budget,
    ProposalKind,
    SliceRef,
    WorkOrder,
)


# ---------- fixtures ---------------------------------------------------------


def make_slice(revision: str = "rev-a", entities=None, slice_id: str = "s1") -> dict:
    return {
        "contract_version": "1.0.0",
        "slice_id": slice_id,
        "model_revision": revision,
        "fragment": {"entities": {"components": entities or []}},
    }


def make_work_order(
    slice_ids=("s1",),
    revisions=("rev-a",),
    kinds=(ProposalKind.MODEL_PATCH,),
) -> WorkOrder:
    return WorkOrder(
        id="WO-1",
        intent="test",
        input_slice_refs=[
            SliceRef(slice_id=sid, model_revision=rev)
            for sid, rev in zip(slice_ids, revisions)
        ],
        expected_proposal_kinds=list(kinds),
        budget=Budget(max_tokens=1000, max_wall_seconds=60),
        requested_by="tester",
        created_at="2026-09-03T00:00:00",
    )


def prov(model_version: str = "rev-a", wo_id: str = "WO-1") -> Provenance:
    return Provenance(
        work_order_id=wo_id, model_version=model_version, prompt_digest="dg"
    )


def valid_slice_dict() -> dict:
    return {
        "id": "sl-1",
        "contract_version": "1.0.0",
        "architecture_id": "arch",
        "model_revision": "rev-a",
        "scope": "local",
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_ids": ["COMP-1"]},
    }


def valid_view_dict() -> dict:
    return {
        "id": "v-1",
        "contract_version": "1.0.0",
        "slice_ref": {"slice_id": "sl-1", "model_revision": "rev-a"},
        "projector": "components",
        "output_content_kind": "diagram",
    }


def valid_artifact_dict() -> dict:
    return {
        "id": "a-1",
        "contract_version": "1.0.0",
        "renderer": "svg",
        "view_ref": {"view_id": "v-1", "model_revision": "rev-a"},
    }


# ---------- 1. model_patch happy path ---------------------------------------


def test_model_patch_valid_passes():
    wo = make_work_order()
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = ModelPatch(
        provenance=prov(),
        operations=[{"op": "add", "target_id": "COMP-1", "value": {}}],
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert r.passed
    assert r.findings == []


# 2. work-order mismatch
def test_model_patch_provenance_mismatch_fails():
    wo = make_work_order()
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = ModelPatch(
        provenance=prov(wo_id="WO-OTHER"),
        operations=[{"op": "add", "target_id": "COMP-1"}],
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed
    assert any(f.severity == "error" for f in r.findings)


# 3. unknown target id
def test_model_patch_unknown_target_error_path():
    wo = make_work_order()
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = ModelPatch(
        provenance=prov(),
        operations=[
            {"op": "add", "target_id": "COMP-1"},
            {"op": "replace", "target_id": "COMP-UNKNOWN"},
        ],
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed
    assert any(
        f.severity == "error" and f.path == "/operations/1/target_id"
        for f in r.findings
    )


# 4. invalid op
def test_model_patch_invalid_op_fails():
    wo = make_work_order()
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = ModelPatch(
        provenance=prov(),
        operations=[{"op": "delete", "target_id": "COMP-1"}],
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed
    assert any("op" in f.path for f in r.findings if f.severity == "error")


# 5. empty operations is a valid no-op
def test_model_patch_empty_operations_valid():
    wo = make_work_order()
    slices = {"s1": make_slice()}
    p = ModelPatch(provenance=prov(), operations=[])
    r = validate(p, work_order=wo, input_slices=slices)
    assert r.passed


# 6. cross-revision drift
def test_cross_revision_drift_errors():
    wo = make_work_order(revisions=("rev-a",))
    slices = {"s1": make_slice(revision="rev-DIFFERENT")}
    p = ModelPatch(provenance=prov(model_version="rev-a"), operations=[])
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed
    assert any("drift" in f.message.lower() for f in r.findings)


# 7. decomposition happy
def test_decomposition_valid():
    wo = make_work_order(kinds=(ProposalKind.DECOMPOSITION_PROPOSAL,))
    slices = {"s1": make_slice()}
    p = DecompositionProposal(
        provenance=prov(),
        proposed_systems=[
            {"id": "S1", "name": "One"},
            {"id": "S2", "name": "Two"},
        ],
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert r.passed


# 8. decomposition duplicate ids
def test_decomposition_duplicate_ids_fails():
    wo = make_work_order(kinds=(ProposalKind.DECOMPOSITION_PROPOSAL,))
    slices = {"s1": make_slice()}
    p = DecompositionProposal(
        provenance=prov(),
        proposed_systems=[
            {"id": "S1", "name": "One"},
            {"id": "S1", "name": "Dup"},
        ],
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed


# 9. decomposition empty
def test_decomposition_empty_fails():
    wo = make_work_order(kinds=(ProposalKind.DECOMPOSITION_PROPOSAL,))
    slices = {"s1": make_slice()}
    p = DecompositionProposal(provenance=prov(), proposed_systems=[])
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed


# 10. slice proposal schema-invalid
def test_slice_proposal_schema_invalid_fails():
    wo = make_work_order(kinds=(ProposalKind.SLICE_PROPOSAL,))
    slices = {"s1": make_slice()}
    bad = {"id": "sl-1"}  # missing required
    p = SliceProposal(provenance=prov(), slice=bad)
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed


# 11. slice proposal schema-valid
def test_slice_proposal_schema_valid_passes():
    wo = make_work_order(kinds=(ProposalKind.SLICE_PROPOSAL,))
    slices = {"s1": make_slice()}
    p = SliceProposal(provenance=prov(), slice=valid_slice_dict())
    r = validate(p, work_order=wo, input_slices=slices)
    assert r.passed, r.findings


# 12. view curation schema-invalid
def test_view_curation_schema_invalid_fails():
    wo = make_work_order(kinds=(ProposalKind.VIEW_CURATION_PROPOSAL,))
    slices = {"s1": make_slice()}
    p = ViewCurationProposal(provenance=prov(), view_spec={"id": "v-1"})
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed


def test_view_curation_valid_passes():
    wo = make_work_order(kinds=(ProposalKind.VIEW_CURATION_PROPOSAL,))
    slices = {"s1": make_slice()}
    p = ViewCurationProposal(provenance=prov(), view_spec=valid_view_dict())
    r = validate(p, work_order=wo, input_slices=slices)
    assert r.passed, r.findings


# 13. artifact candidate schema-invalid
def test_artifact_candidate_schema_invalid_fails():
    wo = make_work_order(kinds=(ProposalKind.ARTIFACT_CANDIDATE,))
    slices = {"s1": make_slice()}
    p = ArtifactCandidate(provenance=prov(), artifact_spec={"id": "a-1"})
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed


def test_artifact_candidate_valid_passes():
    wo = make_work_order(kinds=(ProposalKind.ARTIFACT_CANDIDATE,))
    slices = {"s1": make_slice()}
    p = ArtifactCandidate(provenance=prov(), artifact_spec=valid_artifact_dict())
    r = validate(p, work_order=wo, input_slices=slices)
    assert r.passed, r.findings


# 14. impact assessment unknown id
def test_impact_unknown_id_fails():
    wo = make_work_order(kinds=(ProposalKind.IMPACT_ASSESSMENT,))
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = ImpactAssessment(
        provenance=prov(),
        affected_ids=["COMP-1", "COMP-UNKNOWN"],
        summary="stuff changed",
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed


# 15. impact assessment empty summary
def test_impact_empty_summary_fails():
    wo = make_work_order(kinds=(ProposalKind.IMPACT_ASSESSMENT,))
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = ImpactAssessment(
        provenance=prov(), affected_ids=["COMP-1"], summary=""
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert not r.passed


def test_impact_valid_passes():
    wo = make_work_order(kinds=(ProposalKind.IMPACT_ASSESSMENT,))
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = ImpactAssessment(
        provenance=prov(), affected_ids=["COMP-1"], summary="ok"
    )
    r = validate(p, work_order=wo, input_slices=slices)
    assert r.passed, r.findings


# 16. registry has all 6 kinds
def test_proposal_validators_registry_complete():
    assert set(PROPOSAL_VALIDATORS.keys()) == set(ProposalKind)
    assert len(PROPOSAL_VALIDATORS) == 6


# 17. report passed logic
def test_report_passed_only_when_no_errors():
    r = ValidationReport(
        passed=True,
        findings=[ValidationFinding(severity="warning", message="w", path="/x")],
    )
    # constructor: passed reflects presence of errors — recompute
    assert ValidationReport.from_findings(r.findings).passed is True
    fs = [
        ValidationFinding(severity="warning", message="w", path="/x"),
        ValidationFinding(severity="error", message="e", path="/y"),
    ]
    assert ValidationReport.from_findings(fs).passed is False
    assert ValidationReport.from_findings([]).passed is True


# 18. round-trip to_dict
def test_report_to_dict_structure():
    fs = [
        ValidationFinding(
            severity="error", message="bad", path="/a", code="E1"
        ),
        ValidationFinding(severity="info", message="ok", path="/b"),
    ]
    r = ValidationReport.from_findings(fs)
    d = r.to_dict()
    assert d["passed"] is False
    assert isinstance(d["findings"], list)
    assert d["findings"][0]["severity"] == "error"
    assert d["findings"][0]["code"] == "E1"
    assert d["findings"][0]["path"] == "/a"
    assert d["findings"][0]["message"] == "bad"
    assert d["findings"][1]["severity"] == "info"


# 19. no mutation of inputs
def test_validators_do_not_mutate_inputs():
    wo = make_work_order()
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = ModelPatch(
        provenance=prov(),
        operations=[{"op": "add", "target_id": "COMP-1"}],
    )
    snap_slices = copy.deepcopy(slices)
    snap_p = p.to_dict()
    validate(p, work_order=wo, input_slices=slices)
    assert slices == snap_slices
    assert p.to_dict() == snap_p


# 20. dispatch parametrize
@pytest.mark.parametrize(
    "kind,proposal_factory,valid_extra",
    [
        (
            ProposalKind.MODEL_PATCH,
            lambda: ModelPatch(provenance=prov(), operations=[]),
            {},
        ),
        (
            ProposalKind.DECOMPOSITION_PROPOSAL,
            lambda: DecompositionProposal(
                provenance=prov(),
                proposed_systems=[{"id": "S1", "name": "One"}],
            ),
            {},
        ),
        (
            ProposalKind.SLICE_PROPOSAL,
            lambda: SliceProposal(provenance=prov(), slice=valid_slice_dict()),
            {},
        ),
        (
            ProposalKind.VIEW_CURATION_PROPOSAL,
            lambda: ViewCurationProposal(
                provenance=prov(), view_spec=valid_view_dict()
            ),
            {},
        ),
        (
            ProposalKind.ARTIFACT_CANDIDATE,
            lambda: ArtifactCandidate(
                provenance=prov(), artifact_spec=valid_artifact_dict()
            ),
            {},
        ),
        (
            ProposalKind.IMPACT_ASSESSMENT,
            lambda: ImpactAssessment(
                provenance=prov(),
                affected_ids=["COMP-1"],
                summary="ok",
            ),
            {},
        ),
    ],
)
def test_dispatch_all_kinds(kind, proposal_factory, valid_extra):
    wo = make_work_order(kinds=(kind,))
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    p = proposal_factory()
    r = validate(p, work_order=wo, input_slices=slices)
    assert isinstance(r, ValidationReport)
    assert r.passed, (kind, r.findings)


# extra: per-kind module functions individually callable
def test_per_kind_functions_callable():
    wo = make_work_order()
    slices = {"s1": make_slice(entities=[{"id": "COMP-1"}])}
    assert validate_model_patch(
        ModelPatch(provenance=prov(), operations=[]),
        work_order=wo,
        input_slices=slices,
    ).passed
    assert validate_decomposition_proposal(
        DecompositionProposal(
            provenance=prov(),
            proposed_systems=[{"id": "S1", "name": "N"}],
        ),
        work_order=wo,
        input_slices=slices,
    ).passed
    assert validate_slice_proposal(
        SliceProposal(provenance=prov(), slice=valid_slice_dict()),
        work_order=wo,
        input_slices=slices,
    ).passed
    assert validate_view_curation_proposal(
        ViewCurationProposal(provenance=prov(), view_spec=valid_view_dict()),
        work_order=wo,
        input_slices=slices,
    ).passed
    assert validate_artifact_candidate(
        ArtifactCandidate(
            provenance=prov(), artifact_spec=valid_artifact_dict()
        ),
        work_order=wo,
        input_slices=slices,
    ).passed
    assert validate_impact_assessment(
        ImpactAssessment(
            provenance=prov(), affected_ids=["COMP-1"], summary="ok"
        ),
        work_order=wo,
        input_slices=slices,
    ).passed
