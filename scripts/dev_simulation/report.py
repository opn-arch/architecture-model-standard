"""Report generator — produces benchmark markdown and JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any


def generate_report(
    cold_start: Any,  # ModelSnapshot
    snapshots: list[Any],  # list[ModelSnapshot]
    slice_metrics: list[Any],  # list[SliceMetrics]
    drift: Any,  # DriftCurve
    cohesion: Any,  # CohesionReport
    regen: Any,  # RegenReport
    dev_results: list[Any] | None = None,  # Phase 2 results
) -> str:
    """Generate full benchmark report as markdown."""
    lines = []
    lines.append("# Development Simulation Benchmark Report\n")

    # --- Summary ---
    lines.append("## Summary\n")

    avg_recall = (
        sum(m.slice_recall for m in slice_metrics) / len(slice_metrics) if slice_metrics else 0
    )
    avg_precision = (
        sum(m.slice_precision for m in slice_metrics) / len(slice_metrics) if slice_metrics else 0
    )
    avg_f1 = sum(m.slice_f1 for m in slice_metrics) / len(slice_metrics) if slice_metrics else 0
    final_snap = snapshots[-1] if snapshots else cold_start

    lines.append("| Metric | Score | Grade |")
    lines.append("|--------|-------|-------|")
    lines.append(f"| Slice Recall (avg) | {avg_recall:.0%} | {_grade_pct(avg_recall)} |")
    lines.append(f"| Slice Precision (avg) | {avg_precision:.0%} | {_grade_pct(avg_precision)} |")
    lines.append(f"| Slice F1 (avg) | {avg_f1:.0%} | {_grade_pct(avg_f1)} |")
    lines.append(
        f"| Model Completeness (final) | {final_snap.file_coverage:.0f}% | {_grade_pct(final_snap.file_coverage / 100)} |"
    )
    lines.append(
        f"| Architecture Accuracy (system cohesion) | {getattr(cohesion, 'intra_system_cohesion', cohesion.intra_component_cohesion):.0%} | {_grade_pct(getattr(cohesion, 'intra_system_cohesion', cohesion.intra_component_cohesion))} |"
    )
    lines.append(
        f"| Regen Readiness (overall) | {regen.overall_score:.0f}% | {regen.overall_grade} |"
    )
    lines.append(
        f"| Update Frequency Needed | every {drift.recommended_update_frequency} commits | — |"
    )
    lines.append(
        f"| Cold Start Score | {cold_start.validation_score:.0f} | {_grade_pct(cold_start.validation_score / 100)} |"
    )
    lines.append("")

    # --- Cold Start ---
    lines.append("## Cold Start\n")
    lines.append(f"- Time to first model: {cold_start.extraction_time_ms}ms")
    lines.append(f"- Initial validation score: {cold_start.validation_score:.0f}")
    lines.append(
        f"- Components detected: {cold_start.component_count} (vs final: {final_snap.component_count})"
    )
    lines.append(
        f"- Capabilities: {cold_start.capability_count} (vs final: {final_snap.capability_count})"
    )
    lines.append(
        f"- Behaviors: {cold_start.behavior_count} (vs final: {final_snap.behavior_count})"
    )
    lines.append(
        f"- Relationships: {cold_start.relationship_count} (vs final: {final_snap.relationship_count})"
    )
    if cold_start.error:
        lines.append(f"- Error: {cold_start.error}")
    lines.append("")

    # --- Drift Curve (ASCII) ---
    lines.append("## Drift Curve\n")
    lines.append(f"- Average freshness: {drift.avg_freshness:.1f}")
    lines.append(f"- Minimum freshness: {drift.min_freshness:.1f}")
    lines.append(f"- Commits until below 80: {drift.commits_until_below_80}")
    lines.append(
        f"- Recommended update frequency: every {drift.recommended_update_frequency} commits"
    )
    lines.append("")

    if drift.points:
        lines.append("```")
        # ASCII chart — sample every 10 points
        sampled = drift.points[:: max(1, len(drift.points) // 20)]
        max_score = 100
        width = 40
        for p in sampled:
            bar_len = int(p.freshness_score / max_score * width)
            bar = "█" * bar_len
            marker = " ← below 80" if p.freshness_score < 80 else ""
            lines.append(f"  {p.date} | {bar} {p.freshness_score:.0f}{marker}")
        lines.append("```\n")

    # --- Regenability by Level ---
    lines.append("## Regenability by Level\n")
    lines.append("| Level | A | B | C | D | F | Avg |")
    lines.append("|-------|---|---|---|---|---|-----|")
    lines.append(
        f"| Systems | {regen.system_grades.get('A', 0)} | {regen.system_grades.get('B', 0)} | {regen.system_grades.get('C', 0)} | {regen.system_grades.get('D', 0)} | {regen.system_grades.get('F', 0)} | {regen.system_avg:.0f}% |"
    )
    lines.append(
        f"| Components | {regen.component_grades.get('A', 0)} | {regen.component_grades.get('B', 0)} | {regen.component_grades.get('C', 0)} | {regen.component_grades.get('D', 0)} | {regen.component_grades.get('F', 0)} | {regen.component_avg:.0f}% |"
    )
    lines.append(
        f"| Capabilities | {regen.capability_grades.get('A', 0)} | {regen.capability_grades.get('B', 0)} | {regen.capability_grades.get('C', 0)} | {regen.capability_grades.get('D', 0)} | {regen.capability_grades.get('F', 0)} | {regen.capability_avg:.0f}% |"
    )
    lines.append(
        f"| Behaviors | {regen.behavior_grades.get('A', 0)} | {regen.behavior_grades.get('B', 0)} | {regen.behavior_grades.get('C', 0)} | {regen.behavior_grades.get('D', 0)} | {regen.behavior_grades.get('F', 0)} | {regen.behavior_avg:.0f}% |"
    )
    lines.append("")

    # --- Slice Quality ---
    lines.append("## Slice Quality\n")
    lines.append(f"- Total commits evaluated: {len(slice_metrics)}")
    cross_boundary = sum(1 for m in slice_metrics if m.cross_boundary)
    lines.append(
        f"- Cross-boundary commits: {cross_boundary} ({cross_boundary / len(slice_metrics):.0%})"
        if slice_metrics
        else "- No commits"
    )
    component_hits = sum(1 for m in slice_metrics if m.component_hit)
    lines.append(
        f"- Component identification rate: {component_hits / len(slice_metrics):.0%}"
        if slice_metrics
        else ""
    )
    lines.append("")

    # --- Co-Change Cohesion ---
    lines.append("## Co-Change Cohesion\n")
    lines.append(f"- Intra-component cohesion: {cohesion.intra_component_cohesion:.0%}")
    lines.append(f"- Intra-system cohesion: {getattr(cohesion, 'intra_system_cohesion', 0):.0%}")
    lines.append(f"- Cross-component rate: {cohesion.cross_boundary_rate:.0%}")
    lines.append(f"- Cross-system rate: {getattr(cohesion, 'cross_system_rate', 0):.0%}")
    lines.append(f"- Avg components per commit: {cohesion.avg_components_per_commit:.1f}")
    lines.append(f"- Avg systems per commit: {getattr(cohesion, 'avg_systems_per_commit', 0):.1f}")
    if cohesion.boundary_suggestions:
        lines.append("\n**Boundary suggestions:**")
        for s in cohesion.boundary_suggestions:
            lines.append(f"- {s}")
    lines.append("")

    # --- Extraction Progress ---
    lines.append("## Extraction Checkpoints\n")
    lines.append("| Date | Score | Components | Capabilities | Rels | Time |")
    lines.append("|------|-------|------------|--------------|------|------|")
    for snap in snapshots[:20]:  # show first 20
        lines.append(
            f"| {snap.date[:10]} | {snap.validation_score:.0f} | "
            f"{snap.component_count} | {snap.capability_count} | "
            f"{snap.relationship_count} | {snap.extraction_time_ms}ms |"
        )
    if len(snapshots) > 20:
        lines.append(f"| ... | ({len(snapshots) - 20} more checkpoints) | | | | |")
    lines.append("")

    # --- Phase 2 (if available) ---
    if dev_results:
        lines.append("## Phase 2: LLM Development Simulation\n")
        avg_accuracy = sum(getattr(r, "file_accuracy", 0) for r in dev_results) / len(dev_results)
        lines.append(f"- Commits simulated: {len(dev_results)}")
        lines.append(f"- File prediction accuracy: {avg_accuracy:.0%}")
        lines.append("")

    return "\n".join(lines)


def _grade_pct(value: float) -> str:
    if value >= 0.9:
        return "A"
    elif value >= 0.7:
        return "B"
    elif value >= 0.5:
        return "C"
    elif value >= 0.3:
        return "D"
    return "F"


def save_report(report_text: str, output_dir: Path) -> None:
    """Save report to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "benchmark-report.md").write_text(report_text)


def save_json_results(
    snapshots: list,
    slice_metrics: list,
    drift: Any,
    cohesion: Any,
    regen: Any,
    output_dir: Path,
) -> None:
    """Save machine-readable results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "snapshots": [s.to_dict() if hasattr(s, "to_dict") else {} for s in snapshots],
        "slice_summary": {
            "count": len(slice_metrics),
            "avg_recall": sum(m.slice_recall for m in slice_metrics) / len(slice_metrics)
            if slice_metrics
            else 0,
            "avg_precision": sum(m.slice_precision for m in slice_metrics) / len(slice_metrics)
            if slice_metrics
            else 0,
            "avg_f1": sum(m.slice_f1 for m in slice_metrics) / len(slice_metrics)
            if slice_metrics
            else 0,
        },
        "drift": {
            "avg_freshness": drift.avg_freshness,
            "min_freshness": drift.min_freshness,
            "commits_until_below_80": drift.commits_until_below_80,
            "recommended_update_frequency": drift.recommended_update_frequency,
        },
        "cohesion": {
            "intra_component": cohesion.intra_component_cohesion,
            "cross_boundary_rate": cohesion.cross_boundary_rate,
        },
        "regen": {
            "overall": regen.overall_score,
            "grade": regen.overall_grade,
            "system_avg": regen.system_avg,
            "component_avg": regen.component_avg,
            "capability_avg": regen.capability_avg,
            "behavior_avg": regen.behavior_avg,
        },
    }

    (output_dir / "benchmark-results.json").write_text(json.dumps(results, indent=2))
