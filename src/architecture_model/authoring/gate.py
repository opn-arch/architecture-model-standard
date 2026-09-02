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
    root_local_file_coverage: float = 0.0


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

    from architecture_model.core.hierarchy import load_model_hierarchy

    models, hierarchy_issues = load_model_hierarchy(model, manifest.project_root)

    def _boundary_counts(current: ArchitectureModel) -> tuple[int, int, int, int]:
        cap_ids = {c.id for c in current.entities.capabilities}
        con_ids = {c.id for c in current.entities.constraints}
        realized = {
            rel.to_id for rel in current.relationships
            if rel.type == RelationType.REALIZES and rel.to_id in cap_ids
        }
        allocated = {
            rel.from_id for rel in current.relationships
            if rel.type == RelationType.ALLOCATED_TO and rel.from_id in con_ids
        }
        return len(realized), len(cap_ids), len(allocated), len(con_ids)

    counts = [_boundary_counts(current) for current in models]
    realized_count = sum(item[0] for item in counts)
    cap_count = sum(item[1] for item in counts)
    allocated_count = sum(item[2] for item in counts)
    con_count = sum(item[3] for item in counts)
    capability_realization = realized_count / cap_count * 100 if cap_count else 100.0

    # Calculate constraint allocation
    constraint_allocation = allocated_count / con_count * 100 if con_count else 100.0

    # Calculate file coverage
    manifest_files = {m.file for m in manifest.modules}
    component_files: set[str] = set()
    root_component_files = {
        path for comp in model.entities.components for path in comp.files
    }
    for current in models:
        for comp in current.entities.components:
            component_files.update(comp.files)
    file_coverage = (len(manifest_files & component_files) / len(manifest_files) * 100) if manifest_files else 100.0
    root_local_file_coverage = (
        len(manifest_files & root_component_files) / len(manifest_files) * 100
        if manifest_files else 100.0
    )

    # Weighted average
    overall = (capability_realization * 0.4 + constraint_allocation * 0.3 + file_coverage * 0.3)

    # Phase-specific requirements
    issues: list[str] = list(hierarchy_issues)
    if phase == "concept":
        # Lenient: just need some entities
        has_content = len(model.entities.capabilities) > 0 or len(model.entities.constraints) > 0
        phase_requirements_met = has_content and not hierarchy_issues
        if not has_content:
            issues.append("No capabilities or constraints defined")
    else:
        # production: strict
        phase_requirements_met = True
        if hierarchy_issues:
            phase_requirements_met = False
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
        root_local_file_coverage=root_local_file_coverage,
    )
