"""Co-change cohesion analyzer — measures if component boundaries match real change patterns."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CohesionReport:
    """Results of co-change cohesion analysis."""

    intra_component_cohesion: float = 0.0  # % co-changing pairs in same component
    cross_boundary_rate: float = 0.0  # % commits touching >1 component
    avg_components_per_commit: float = 0.0
    boundary_suggestions: list[str] = field(default_factory=list)
    # Details
    total_commits_analyzed: int = 0
    cross_boundary_commits: int = 0
    co_change_pairs: int = 0
    same_component_pairs: int = 0


def _get_file_component_map(model: Any) -> dict[str, str]:
    """Build file → component_id mapping."""
    file_map: dict[str, str] = {}
    if not model or not model.entities.components:
        return file_map
    for comp in model.entities.components:
        for f in comp.files:
            file_map[f] = comp.id
    return file_map


def analyze_cohesion(commits: list[Any], model: Any) -> CohesionReport:
    """Analyze how well component boundaries align with change patterns."""
    report = CohesionReport()
    file_map = _get_file_component_map(model)

    if not file_map or not commits:
        return report

    # Track co-change patterns and cross-boundary commits
    co_change_counter: Counter = Counter()  # (comp_a, comp_b) → count
    component_touches_per_commit: list[int] = []

    for commit in commits:
        all_files = list(
            set(
                getattr(commit, "files_changed", [])
                + getattr(commit, "files_added", [])
                + getattr(commit, "files_deleted", [])
            )
        )

        # Filter to source files with known components
        file_components = []
        for f in all_files:
            comp_id = file_map.get(f)
            if comp_id:
                file_components.append((f, comp_id))

        if not file_components:
            continue

        report.total_commits_analyzed += 1

        # Count unique components touched
        unique_comps = set(comp_id for _, comp_id in file_components)
        component_touches_per_commit.append(len(unique_comps))

        if len(unique_comps) > 1:
            report.cross_boundary_commits += 1

        # Build co-change pairs
        comp_ids = [comp_id for _, comp_id in file_components]
        for i in range(len(comp_ids)):
            for j in range(i + 1, len(comp_ids)):
                a, b = sorted([comp_ids[i], comp_ids[j]])
                report.co_change_pairs += 1
                if a == b:
                    report.same_component_pairs += 1
                else:
                    co_change_counter[(a, b)] += 1

    # Compute metrics
    if report.total_commits_analyzed > 0:
        report.cross_boundary_rate = report.cross_boundary_commits / report.total_commits_analyzed
        report.avg_components_per_commit = (
            sum(component_touches_per_commit) / len(component_touches_per_commit)
            if component_touches_per_commit
            else 0.0
        )

    if report.co_change_pairs > 0:
        report.intra_component_cohesion = report.same_component_pairs / report.co_change_pairs

    # Suggest boundary adjustments for frequently co-changing components
    for (comp_a, comp_b), count in co_change_counter.most_common(5):
        if count >= 3:  # threshold: co-changed 3+ times
            report.boundary_suggestions.append(
                f"Consider merging {comp_a} and {comp_b} (co-changed {count} times)"
            )

    return report
