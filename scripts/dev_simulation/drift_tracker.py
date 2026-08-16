"""Drift tracker — measures model freshness over time."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DriftPoint:
    """Model freshness at a point in time."""

    date: str
    commits_since_extraction: int
    files_added_since: int = 0
    files_removed_since: int = 0
    freshness_score: float = 100.0  # starts at extraction score, degrades


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
    """Track how model freshness degrades between extraction checkpoints."""
    curve = DriftCurve()

    if not snapshots or not daily_commits:
        return curve

    # Map snapshot dates to indices in daily_commits
    snapshot_dates = {s.date[:10]: s for s in snapshots if hasattr(s, "date")}

    current_snapshot_idx = 0
    commits_since = 0
    files_in_model = set()

    # Initialize with first snapshot's files
    if snapshots[0].model:
        for comp in snapshots[0].model.entities.components or []:
            files_in_model.update(comp.files)

    base_score = snapshots[0].validation_score if snapshots else 100.0

    for i, commit in enumerate(daily_commits):
        day = commit.date[:10] if hasattr(commit, "date") else ""

        # Check if this day is a new extraction checkpoint
        if day in snapshot_dates:
            # Reset — new extraction happened
            snap = snapshot_dates[day]
            base_score = snap.validation_score
            commits_since = 0
            files_in_model = set()
            if snap.model:
                for comp in snap.model.entities.components or []:
                    files_in_model.update(comp.files)
        else:
            commits_since += 1

        # Estimate freshness degradation
        # Each commit with new/removed files degrades score slightly
        new_files = len(getattr(commit, "files_added", []))
        removed_files = len(getattr(commit, "files_deleted", []))

        # Degradation: -0.5 per new file not in model, -0.3 per removed file still in model
        degradation = new_files * 0.5 + removed_files * 0.3
        freshness = max(0, base_score - degradation * commits_since * 0.1)

        curve.points.append(
            DriftPoint(
                date=day,
                commits_since_extraction=commits_since,
                files_added_since=new_files,
                files_removed_since=removed_files,
                freshness_score=freshness,
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
