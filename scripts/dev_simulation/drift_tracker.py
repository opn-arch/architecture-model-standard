"""Drift tracker — measures model freshness over time."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DriftPoint:
    """Model freshness at a point in time."""

    date: str
    commits_since_extraction: int
    files_changed_outside_model: int = 0
    files_added_since: int = 0
    files_removed_since: int = 0
    freshness_score: float = 100.0  # starts at 100 at extraction, degrades


@dataclass
class DriftCurve:
    """Full drift measurement across the benchmark period."""

    points: list[DriftPoint] = field(default_factory=list)
    avg_freshness: float = 0.0
    min_freshness: float = 0.0
    commits_until_below_80: int = 0  # how many commits before model is "stale"
    recommended_update_frequency: int = 0  # commits


def track_drift(
    snapshots: list[Any],  # ModelSnapshot
    daily_commits: list[Any],  # CommitInfo
    checkpoint_interval: int = 3,
) -> DriftCurve:
    """Track how model freshness degrades between extraction checkpoints.

    Freshness degrades based on:
    - New files added that aren't in the model (structural drift)
    - Files deleted that were in the model (stale references)
    - Changed files not covered by any component (blind spots)
    """
    curve = DriftCurve()

    if not snapshots or not daily_commits:
        return curve

    # Map snapshot dates to indices
    snapshot_dates = {s.date[:10]: s for s in snapshots if hasattr(s, "date") and s.date}

    # Get file map from model (use injected _file_component_map)
    file_map: dict[str, str] = {}
    current_snapshot = snapshots[0] if snapshots else None

    def _refresh_file_map(snap: Any) -> dict[str, str]:
        if snap and snap.model and hasattr(snap.model, "_file_component_map"):
            return dict(snap.model._file_component_map)
        # Fallback: extract from components
        fmap: dict[str, str] = {}
        if snap and snap.model:
            for comp in snap.model.entities.components or []:
                for f in comp.files or []:
                    fmap[str(f)] = comp.id
        return fmap

    file_map = _refresh_file_map(current_snapshot)
    model_file_count = len(file_map)

    commits_since = 0
    cumulative_unmodeled_changes = 0
    cumulative_new_files = 0
    cumulative_removed_files = 0

    for commit in daily_commits:
        day = commit.date[:10] if hasattr(commit, "date") else ""

        # Check if this day is a new extraction checkpoint
        if day in snapshot_dates:
            snap = snapshot_dates[day]
            file_map = _refresh_file_map(snap)
            model_file_count = len(file_map)
            commits_since = 0
            cumulative_unmodeled_changes = 0
            cumulative_new_files = 0
            cumulative_removed_files = 0
        else:
            commits_since += 1

        # Count changes outside model coverage
        changed = getattr(commit, "files_changed", [])
        added = getattr(commit, "files_added", [])
        removed = getattr(commit, "files_deleted", [])

        unmodeled = sum(1 for f in changed if f not in file_map and f.endswith(".py"))
        new_unmodeled = sum(1 for f in added if f.endswith(".py"))
        removed_modeled = sum(1 for f in removed if f in file_map)

        cumulative_unmodeled_changes += unmodeled
        cumulative_new_files += new_unmodeled
        cumulative_removed_files += removed_modeled

        # Freshness formula:
        # - Each unmodeled change represents a blind spot (-1 per occurrence)
        # - New files not in model (-2 each, structural gap)
        # - Removed files still in model (-3 each, stale reference)
        # Normalized by model size to keep scale reasonable
        if model_file_count > 0:
            penalty = (
                (
                    cumulative_unmodeled_changes * 1.0
                    + cumulative_new_files * 2.0
                    + cumulative_removed_files * 3.0
                )
                / model_file_count
                * 10
            )
        else:
            # No file map = instant drift
            penalty = commits_since * 5.0

        freshness = max(0.0, 100.0 - penalty)

        curve.points.append(
            DriftPoint(
                date=day,
                commits_since_extraction=commits_since,
                files_changed_outside_model=unmodeled,
                files_added_since=cumulative_new_files,
                files_removed_since=cumulative_removed_files,
                freshness_score=round(freshness, 1),
            )
        )

    # Compute summary stats
    if curve.points:
        scores = [p.freshness_score for p in curve.points]
        curve.avg_freshness = sum(scores) / len(scores)
        curve.min_freshness = min(scores)

        # Find first point where score drops below 80
        for p in curve.points:
            if p.freshness_score < 80:
                curve.commits_until_below_80 = p.commits_since_extraction
                break

        if curve.commits_until_below_80 == 0:
            curve.commits_until_below_80 = max(p.commits_since_extraction for p in curve.points)

        curve.recommended_update_frequency = max(1, curve.commits_until_below_80 // 2)

    return curve
