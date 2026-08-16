"""Co-change cohesion analyzer — measures if component boundaries match real change patterns."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CohesionReport:
    """Results of co-change cohesion analysis."""

    intra_component_cohesion: float = 0.0  # % co-changing pairs in same component
    intra_system_cohesion: float = 0.0  # % co-changing pairs in same system
    cross_boundary_rate: float = 0.0  # % commits touching >1 component
    cross_system_rate: float = 0.0  # % commits touching >1 system
    avg_components_per_commit: float = 0.0
    avg_systems_per_commit: float = 0.0
    boundary_suggestions: list[str] = field(default_factory=list)
    # Details
    total_commits_analyzed: int = 0
    cross_boundary_commits: int = 0
    co_change_pairs: int = 0
    same_component_pairs: int = 0


def _get_file_component_map(model: Any) -> dict[str, str]:
    """Build file → component_id mapping."""
    # Prefer injected map from allocate stage (most accurate)
    if hasattr(model, "_file_component_map") and model._file_component_map:
        return model._file_component_map

    file_map: dict[str, str] = {}
    if not model:
        return file_map
    for comp in model.entities.components or []:
        for f in comp.files or []:
            file_map[str(f)] = comp.id
    return file_map

    # First try components (which have files directly)
    for comp in model.entities.components or []:
        for f in comp.files or []:
            file_map[str(f)] = comp.id

    # If no component files, build mapping from systems using directory prefix heuristic
    if not file_map and model.entities.systems:
        # Build system name→id lookup for prefix matching
        system_prefixes: list[tuple[str, str]] = []
        for sys in model.entities.systems:
            # Convert system name to likely directory prefix
            name_slug = sys.name.lower().replace(" ", "_").replace("-", "_")
            system_prefixes.append((name_slug, sys.id))

        # This is approximate — we match files by checking if any path segment
        # contains the system name slug
        # (The actual file list isn't stored on systems, so we rely on the model
        # being used with actual commit data in the cohesion analysis)
        file_map["__use_prefix_matching__"] = ""  # sentinel
        file_map["__prefixes__"] = ""  # store for later use

    return file_map


def analyze_cohesion(commits: list[Any], model: Any) -> CohesionReport:
    """Analyze how well component boundaries align with change patterns."""
    report = CohesionReport()
    file_map = _get_file_component_map(model)
    # System-level map (coarser)
    system_map: dict[str, str] = {}
    if model and hasattr(model, "_file_system_map"):
        system_map = model._file_system_map

    if not file_map or not commits:
        return report

    # Track co-change patterns and cross-boundary commits
    co_change_counter: Counter = Counter()  # (comp_a, comp_b) → count
    component_touches_per_commit: list[int] = []
    system_touches_per_commit: list[int] = []
    per_commit_coherence: list[float] = []  # fraction of files in dominant component
    same_system_pairs = 0
    total_system_pairs = 0

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
        file_systems = []
        for f in all_files:
            comp_id = file_map.get(f)
            if comp_id:
                file_components.append((f, comp_id))
            sys_id = system_map.get(f)
            if sys_id:
                file_systems.append((f, sys_id))

        if not file_components:
            continue

        report.total_commits_analyzed += 1

        # Count unique components/systems touched
        unique_comps = set(comp_id for _, comp_id in file_components)
        unique_systems = set(sys_id for _, sys_id in file_systems)
        component_touches_per_commit.append(len(unique_comps))
        system_touches_per_commit.append(len(unique_systems))

        if len(unique_comps) > 1:
            report.cross_boundary_commits += 1

        # Per-commit coherence: fraction of files in dominant component
        comp_counts = Counter(comp_id for _, comp_id in file_components)
        dominant_count = comp_counts.most_common(1)[0][1]
        commit_coherence = dominant_count / len(file_components)
        per_commit_coherence.append(commit_coherence)

        # Track total pairs for backward compat reporting
        report.co_change_pairs += len(file_components)
        report.same_component_pairs += dominant_count

        # Track frequently co-changing component pairs for suggestions
        comp_ids_unique = list(unique_comps)
        for i in range(len(comp_ids_unique)):
            for j in range(i + 1, len(comp_ids_unique)):
                a, b = sorted([comp_ids_unique[i], comp_ids_unique[j]])
                co_change_counter[(a, b)] += 1

        # System-level pairs
        sys_ids = [sys_id for _, sys_id in file_systems]
        for i in range(len(sys_ids)):
            for j in range(i + 1, len(sys_ids)):
                total_system_pairs += 1
                if sys_ids[i] == sys_ids[j]:
                    same_system_pairs += 1

    # Compute metrics
    if report.total_commits_analyzed > 0:
        report.cross_boundary_rate = report.cross_boundary_commits / report.total_commits_analyzed
        report.avg_components_per_commit = (
            sum(component_touches_per_commit) / len(component_touches_per_commit)
            if component_touches_per_commit
            else 0.0
        )
        report.avg_systems_per_commit = (
            sum(system_touches_per_commit) / len(system_touches_per_commit)
            if system_touches_per_commit
            else 0.0
        )
        cross_system_commits = sum(1 for t in system_touches_per_commit if t > 1)
        report.cross_system_rate = cross_system_commits / report.total_commits_analyzed

    if report.co_change_pairs > 0:
        # Use per-commit coherence average (more meaningful than quadratic pair ratio)
        report.intra_component_cohesion = (
            sum(per_commit_coherence) / len(per_commit_coherence) if per_commit_coherence else 0.0
        )

    if total_system_pairs > 0:
        report.intra_system_cohesion = same_system_pairs / total_system_pairs

    # Suggest boundary adjustments for frequently co-changing components
    for (comp_a, comp_b), count in co_change_counter.most_common(5):
        if count >= 3:  # threshold: co-changed 3+ times
            report.boundary_suggestions.append(
                f"Consider merging {comp_a} and {comp_b} (co-changed {count} times)"
            )

    return report
