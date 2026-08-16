"""Main runner + CLI for the development simulation benchmark."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def run_benchmark(
    repo_url: str,
    days: int = 180,
    checkpoint_interval: int = 3,
    phase: str = "deterministic",
    relay_url: str = "http://localhost:8400",
    sample_rate: int = 1,
    output_dir: str = "",
) -> None:
    """Run the full development simulation benchmark."""
    from .checkout import (
        clone_repo,
        get_daily_commits,
        get_commits_between,
        checkout,
        get_commit_files,
    )
    from .extractor import extract_at_checkpoint
    from .slice_evaluator import evaluate_slice
    from .drift_tracker import track_drift
    from .cohesion import analyze_cohesion
    from .regen_scorer import score_regenability
    from .report import generate_report, save_report, save_json_results

    # Determine target directory
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    base_dir = Path(__file__).parent.parent.parent / "projects" / repo_name
    cache_dir = base_dir / ".benchmark-cache"

    if not output_dir:
        output_dir_path = base_dir / "benchmark-results"
    else:
        output_dir_path = Path(output_dir)

    print(f"=== Development Simulation Benchmark ===")
    print(f"  Repo: {repo_url}")
    print(f"  Target: {base_dir}")
    print(f"  Days: {days}, Checkpoint interval: {checkpoint_interval}")
    print(f"  Phase: {phase}")
    print()

    # Step 1: Clone
    print("[1/7] Cloning repository...")
    t0 = time.monotonic()
    clone_repo(repo_url, base_dir, days=days)
    print(f"  Done ({time.monotonic() - t0:.1f}s)")

    # Step 2: Get daily commits
    print("[2/7] Gathering commit history...")
    daily_commits = get_daily_commits(base_dir, days=days)
    print(f"  Found {len(daily_commits)} daily commits over {days} days")

    if not daily_commits:
        print("  ERROR: No commits found. Aborting.")
        return

    # Step 3: Determine checkpoints
    checkpoints = daily_commits[::checkpoint_interval]
    print(f"  Checkpoints: {len(checkpoints)} (every {checkpoint_interval} days)")

    # Step 4: Extract at each checkpoint
    print(f"[3/7] Extracting models at {len(checkpoints)} checkpoints...")
    snapshots = []
    for i, cp in enumerate(checkpoints):
        print(
            f"  [{i + 1}/{len(checkpoints)}] {cp.date[:10]} ({cp.sha[:8]})...", end=" ", flush=True
        )
        checkout(base_dir, cp.sha)
        snapshot = extract_at_checkpoint(base_dir, cache_dir=cache_dir)
        snapshot.date = cp.date
        snapshots.append(snapshot)
        status = (
            f"score={snapshot.validation_score:.0f} comps={snapshot.component_count}"
            if not snapshot.error
            else f"ERROR: {snapshot.error[:50]}"
        )
        print(status)

    # Step 5: Evaluate slices
    print(f"[4/7] Evaluating slice quality across commits...")
    slice_metrics = []
    for i in range(len(snapshots) - 1):
        # Get commits between this checkpoint and next
        commits_between = get_commits_between(base_dir, checkpoints[i].sha, checkpoints[i + 1].sha)
        model = snapshots[i].model

        for commit in commits_between:
            # Get file details for this commit
            detailed = get_commit_files(base_dir, commit.sha)
            metrics = evaluate_slice(model, detailed)
            slice_metrics.append(metrics)

    print(f"  Evaluated {len(slice_metrics)} commits")
    if slice_metrics:
        avg_recall = sum(m.slice_recall for m in slice_metrics) / len(slice_metrics)
        avg_f1 = sum(m.slice_f1 for m in slice_metrics) / len(slice_metrics)
        print(f"  Avg slice recall: {avg_recall:.0%}, F1: {avg_f1:.0%}")

    # Step 6: Drift tracking
    print("[5/7] Tracking model drift...")
    # Enrich daily commits with file info for drift tracking
    drift = track_drift(snapshots, daily_commits, checkpoint_interval)
    print(
        f"  Avg freshness: {drift.avg_freshness:.1f}, Update needed every {drift.recommended_update_frequency} commits"
    )

    # Step 7: Cohesion analysis
    print("[6/7] Analyzing co-change cohesion...")
    # Use all commits with file details for cohesion
    all_detailed_commits = []
    for commit in daily_commits:
        try:
            detailed = get_commit_files(base_dir, commit.sha)
            all_detailed_commits.append(detailed)
        except Exception:
            pass

    final_model = snapshots[-1].model if snapshots else None
    cohesion = analyze_cohesion(all_detailed_commits, final_model)
    print(
        f"  Cohesion: {cohesion.intra_component_cohesion:.0%}, Cross-boundary: {cohesion.cross_boundary_rate:.0%}"
    )

    # Step 8: Regenability
    print("[7/7] Scoring regenability...")
    regen = score_regenability(final_model)
    print(f"  Overall: {regen.overall_grade} ({regen.overall_score:.0f}%)")
    print(
        f"  Components avg: {regen.component_avg:.0f}%, Capabilities avg: {regen.capability_avg:.0f}%"
    )

    # Generate report
    print("\n=== Generating Report ===")
    cold_start = snapshots[0] if snapshots else None
    report_text = generate_report(cold_start, snapshots, slice_metrics, drift, cohesion, regen)
    save_report(report_text, output_dir_path)
    save_json_results(snapshots, slice_metrics, drift, cohesion, regen, output_dir_path)

    print(f"\n  Report saved to: {output_dir_path / 'benchmark-report.md'}")
    print(f"  JSON results: {output_dir_path / 'benchmark-results.json'}")
    print(f"\n{'=' * 50}")
    print(f"  DONE in {time.monotonic() - t0:.0f}s")


def main():
    parser = argparse.ArgumentParser(description="Development Simulation Benchmark")
    parser.add_argument("--repo", required=True, help="Git repo URL to benchmark")
    parser.add_argument("--days", type=int, default=180, help="Days of history (default: 180)")
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=3,
        help="Days between extraction checkpoints (default: 3)",
    )
    parser.add_argument("--phase", choices=["deterministic", "llm"], default="deterministic")
    parser.add_argument(
        "--relay", default="http://localhost:8400", help="Copilot relay URL (Phase 2)"
    )
    parser.add_argument("--sample-rate", type=int, default=1, help="LLM sample rate (1=every day)")
    parser.add_argument("--output", default="", help="Output directory")

    args = parser.parse_args()

    run_benchmark(
        repo_url=args.repo,
        days=args.days,
        checkpoint_interval=args.checkpoint_interval,
        phase=args.phase,
        relay_url=args.relay,
        sample_rate=args.sample_rate,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
