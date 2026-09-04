"""Typed validators for AI proposals.

Each :class:`Proposal` kind has a dedicated validator that returns a
:class:`ValidationReport`. Validators are pure: no side effects, no
mutation of inputs, no file writes.

Top-level :func:`validate` performs the cross-cutting revision-drift
check and dispatches on ``proposal.kind`` via
:data:`PROPOSAL_VALIDATORS`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from typing import Any, Callable

from architecture_model.ai.proposals import (
    ArtifactCandidate,
    DecompositionProposal,
    ImpactAssessment,
    ModelPatch,
    Proposal,
    SliceProposal,
    ViewCurationProposal,
)
from architecture_model.ai.work_order import ProposalKind, WorkOrder

_VALID_OPS = frozenset({"add", "remove", "replace", "move"})


# ---------- reporting types --------------------------------------------------


@dataclass(frozen=True)
class ValidationFinding:
    """A single validation issue."""

    severity: str  # "error" | "warning" | "info"
    message: str
    path: str  # JSON-pointer-ish location
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
        }
        if self.code is not None:
            d["code"] = self.code
        return d


@dataclass(frozen=True)
class ValidationReport:
    """Aggregate result of validating a proposal."""

    passed: bool
    findings: list[ValidationFinding] = field(default_factory=list)

    @classmethod
    def from_findings(
        cls, findings: list[ValidationFinding]
    ) -> "ValidationReport":
        passed = not any(f.severity == "error" for f in findings)
        return cls(passed=passed, findings=list(findings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------- helpers ----------------------------------------------------------


_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def _load_spec_schema(name: str) -> dict[str, Any]:
    if name not in _SCHEMA_CACHE:
        text = (
            resources.files("architecture_model.spec")
            .joinpath(name)
            .read_text(encoding="utf-8")
        )
        _SCHEMA_CACHE[name] = json.loads(text)
    return _SCHEMA_CACHE[name]


def _schema_findings(
    data: dict[str, Any], schema_name: str, base_path: str
) -> list[ValidationFinding]:
    import jsonschema

    schema = _load_spec_schema(schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    findings: list[ValidationFinding] = []
    for err in sorted(
        validator.iter_errors(data), key=lambda e: list(e.absolute_path)
    ):
        sub = "/".join(str(p) for p in err.absolute_path)
        path = f"{base_path}/{sub}" if sub else base_path
        findings.append(
            ValidationFinding(
                severity="error",
                message=err.message,
                path=path,
                code="schema",
            )
        )
    return findings


def _collect_slice_entity_ids(input_slices: dict[str, dict]) -> set[str]:
    ids: set[str] = set()
    for sl in input_slices.values():
        frag = sl.get("fragment") or {}
        ents = frag.get("entities") or {}
        for _kind, items in ents.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and "id" in item:
                    ids.add(item["id"])
    return ids


def _provenance_findings(
    proposal: Proposal, work_order: WorkOrder
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    if proposal.provenance.work_order_id != work_order.id:
        findings.append(
            ValidationFinding(
                severity="error",
                message=(
                    f"provenance.work_order_id "
                    f"{proposal.provenance.work_order_id!r} does not match "
                    f"work_order.id {work_order.id!r}"
                ),
                path="/provenance/work_order_id",
                code="provenance-mismatch",
            )
        )
    return findings


def _drift_findings(
    proposal: Proposal, work_order: WorkOrder, input_slices: dict[str, dict]
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    expected = proposal.provenance.model_version
    for ref in work_order.input_slice_refs:
        sl = input_slices.get(ref.slice_id)
        if sl is None:
            continue
        actual = sl.get("model_revision")
        if actual != expected:
            findings.append(
                ValidationFinding(
                    severity="error",
                    message=(
                        f"cross-revision drift for slice {ref.slice_id!r}: "
                        f"slice model_revision={actual!r} != "
                        f"provenance.model_version={expected!r}"
                    ),
                    path=f"/input_slices/{ref.slice_id}/model_revision",
                    code="cross-revision-drift",
                )
            )
    return findings


# ---------- per-kind validators ---------------------------------------------


def validate_model_patch(
    proposal: ModelPatch,
    *,
    work_order: WorkOrder,
    input_slices: dict[str, dict],
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    findings.extend(_provenance_findings(proposal, work_order))

    known_ids = _collect_slice_entity_ids(input_slices)
    for idx, op in enumerate(proposal.operations):
        op_val = op.get("op") if isinstance(op, dict) else None
        if op_val not in _VALID_OPS:
            findings.append(
                ValidationFinding(
                    severity="error",
                    message=(
                        f"invalid op {op_val!r}; must be one of "
                        f"{sorted(_VALID_OPS)}"
                    ),
                    path=f"/operations/{idx}/op",
                    code="invalid-op",
                )
            )
        target = op.get("target_id") if isinstance(op, dict) else None
        if target is not None and target not in known_ids:
            findings.append(
                ValidationFinding(
                    severity="error",
                    message=(
                        f"operation target_id {target!r} not present in "
                        f"any input slice fragment"
                    ),
                    path=f"/operations/{idx}/target_id",
                    code="unknown-entity",
                )
            )
    return ValidationReport.from_findings(findings)


def validate_decomposition_proposal(
    proposal: DecompositionProposal,
    *,
    work_order: WorkOrder,
    input_slices: dict[str, dict],
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    findings.extend(_provenance_findings(proposal, work_order))

    if not proposal.proposed_systems:
        findings.append(
            ValidationFinding(
                severity="error",
                message="proposed_systems must be non-empty",
                path="/proposed_systems",
                code="empty",
            )
        )
    seen: set[str] = set()
    for idx, sys in enumerate(proposal.proposed_systems):
        if not isinstance(sys, dict):
            findings.append(
                ValidationFinding(
                    severity="error",
                    message="entry must be an object",
                    path=f"/proposed_systems/{idx}",
                    code="shape",
                )
            )
            continue
        sid = sys.get("id")
        name = sys.get("name")
        if not sid:
            findings.append(
                ValidationFinding(
                    severity="error",
                    message="missing id",
                    path=f"/proposed_systems/{idx}/id",
                    code="missing-field",
                )
            )
        if not name:
            findings.append(
                ValidationFinding(
                    severity="error",
                    message="missing name",
                    path=f"/proposed_systems/{idx}/name",
                    code="missing-field",
                )
            )
        if sid:
            if sid in seen:
                findings.append(
                    ValidationFinding(
                        severity="error",
                        message=f"duplicate id {sid!r}",
                        path=f"/proposed_systems/{idx}/id",
                        code="duplicate-id",
                    )
                )
            seen.add(sid)
    return ValidationReport.from_findings(findings)


def validate_slice_proposal(
    proposal: SliceProposal,
    *,
    work_order: WorkOrder,
    input_slices: dict[str, dict],
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    findings.extend(_provenance_findings(proposal, work_order))
    findings.extend(
        _schema_findings(proposal.slice, "model-slice.schema.json", "/slice")
    )
    return ValidationReport.from_findings(findings)


def validate_view_curation_proposal(
    proposal: ViewCurationProposal,
    *,
    work_order: WorkOrder,
    input_slices: dict[str, dict],
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    findings.extend(_provenance_findings(proposal, work_order))
    findings.extend(
        _schema_findings(
            proposal.view_spec, "view-spec.schema.json", "/view_spec"
        )
    )
    return ValidationReport.from_findings(findings)


def validate_artifact_candidate(
    proposal: ArtifactCandidate,
    *,
    work_order: WorkOrder,
    input_slices: dict[str, dict],
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    findings.extend(_provenance_findings(proposal, work_order))
    findings.extend(
        _schema_findings(
            proposal.artifact_spec,
            "artifact-spec.schema.json",
            "/artifact_spec",
        )
    )
    return ValidationReport.from_findings(findings)


def validate_impact_assessment(
    proposal: ImpactAssessment,
    *,
    work_order: WorkOrder,
    input_slices: dict[str, dict],
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    findings.extend(_provenance_findings(proposal, work_order))

    known_ids = _collect_slice_entity_ids(input_slices)
    for idx, entity_id in enumerate(proposal.affected_ids):
        if entity_id not in known_ids:
            findings.append(
                ValidationFinding(
                    severity="error",
                    message=(
                        f"affected_ids entry {entity_id!r} not present in "
                        f"any input slice fragment"
                    ),
                    path=f"/affected_ids/{idx}",
                    code="unknown-entity",
                )
            )
    if not proposal.summary or not proposal.summary.strip():
        findings.append(
            ValidationFinding(
                severity="error",
                message="summary must be non-empty",
                path="/summary",
                code="empty",
            )
        )
    return ValidationReport.from_findings(findings)


# ---------- registry + dispatcher -------------------------------------------


PROPOSAL_VALIDATORS: dict[ProposalKind, Callable[..., ValidationReport]] = {
    ProposalKind.MODEL_PATCH: validate_model_patch,
    ProposalKind.DECOMPOSITION_PROPOSAL: validate_decomposition_proposal,
    ProposalKind.SLICE_PROPOSAL: validate_slice_proposal,
    ProposalKind.VIEW_CURATION_PROPOSAL: validate_view_curation_proposal,
    ProposalKind.ARTIFACT_CANDIDATE: validate_artifact_candidate,
    ProposalKind.IMPACT_ASSESSMENT: validate_impact_assessment,
}


def validate(
    proposal: Proposal,
    *,
    work_order: WorkOrder,
    input_slices: dict[str, dict],
) -> ValidationReport:
    """Dispatch to the typed validator for ``proposal.kind``.

    Applies the cross-revision drift check first, then merges its
    findings with those from the typed validator.
    """
    drift = _drift_findings(proposal, work_order, input_slices)
    validator = PROPOSAL_VALIDATORS[proposal.kind]
    typed = validator(
        proposal, work_order=work_order, input_slices=input_slices
    )
    combined = list(drift) + list(typed.findings)
    return ValidationReport.from_findings(combined)


__all__ = [
    "PROPOSAL_VALIDATORS",
    "ValidationFinding",
    "ValidationReport",
    "validate",
    "validate_artifact_candidate",
    "validate_decomposition_proposal",
    "validate_impact_assessment",
    "validate_model_patch",
    "validate_slice_proposal",
    "validate_view_curation_proposal",
]
