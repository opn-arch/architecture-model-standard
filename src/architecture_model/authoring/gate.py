"""Development gate: check if code reality tracks toward authored architecture intent."""

from __future__ import annotations

from dataclasses import dataclass, field

from architecture_model.core.types import ArchitectureModel, RelationType
from architecture_model.manifest.types import Manifest


@dataclass
class GateResult:
    capability_realization: float  # % of capabilities realized by components
    constraint_allocation: float  # % of constraints with allocated-to edges
    file_coverage: float  # % of source files mapped to components
    overall: float  # weighted average
    phase: str  # "concept" or "production"
    phase_requirements_met: bool
    issues: list[str] = field(default_factory=list)


def check_development_gate(
    model: ArchitectureModel,
    manifest: Manifest,
    phase: str | None = None,
) -> GateResult:
    """Check if code reality is tracking toward authored architecture intent.

    Args:
        model: The architecture model to check.
        manifest: The reality manifest from code scanning.
        phase: Override lifecycle phase ("concept" or "production").
               If None, defaults to "production".
    """
    if phase is None:
        phase = "production"

    # Calculate capability realization
    cap_ids = {c.id for c in model.entities.capabilities}
    realized_caps = set()
    for rel in model.relationships:
        if rel.type == RelationType.REALIZES and rel.to_id in cap_ids:
            realized_caps.add(rel.to_id)
    capability_realization = (len(realized_caps) / len(cap_ids) * 100) if cap_ids else 100.0

    # Calculate constraint allocation
    con_ids = {c.id for c in model.entities.constraints}
    allocated_cons = set()
    for rel in model.relationships:
        if rel.type == RelationType.ALLOCATED_TO and rel.from_id in con_ids:
            allocated_cons.add(rel.from_id)
    constraint_allocation = (len(allocated_cons) / len(con_ids) * 100) if con_ids else 100.0

    # Calculate file coverage
    manifest_files = {m.file for m in manifest.modules}
    component_files: set[str] = set()
    for comp in model.entities.components:
        component_files.update(comp.files)
    file_coverage = (len(manifest_files & component_files) / len(manifest_files) * 100) if manifest_files else 100.0

    # Weighted average
    overall = (capability_realization * 0.4 + constraint_allocation * 0.3 + file_coverage * 0.3)

    # Phase-specific requirements
    issues: list[str] = []
    if phase == "concept":
        # Lenient: just need some entities
        has_content = len(model.entities.capabilities) > 0 or len(model.entities.constraints) > 0
        phase_requirements_met = has_content
        if not has_content:
            issues.append("No capabilities or constraints defined")
    else:
        # production: strict
        phase_requirements_met = True
        if file_coverage < 80:
            phase_requirements_met = False
            issues.append(f"File coverage {file_coverage:.1f}% < 80% threshold")
        if capability_realization < 100:
            phase_requirements_met = False
            issues.append(f"Not all capabilities realized ({capability_realization:.1f}%)")
        if constraint_allocation < 100:
            phase_requirements_met = False
            issues.append(f"Not all constraints allocated ({constraint_allocation:.1f}%)")

    return GateResult(
        capability_realization=capability_realization,
        constraint_allocation=constraint_allocation,
        file_coverage=file_coverage,
        overall=overall,
        phase=phase,
        phase_requirements_met=phase_requirements_met,
        issues=issues,
    )
