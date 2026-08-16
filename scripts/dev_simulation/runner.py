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

    # Step 2: Get daily commits (ensure we're on default branch first)
    print("[2/7] Gathering commit history...")
    import subprocess

    # Find default branch and checkout to get full history
    default_branch = (
        subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=base_dir,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .replace("refs/remotes/origin/", "")
    )
    if not default_branch:
        default_branch = "main"
    subprocess.run(
        ["git", "checkout", "--force", default_branch],
        cwd=base_dir,
        capture_output=True,
        timeout=30,
    )
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

    # Step 6: Drift tracking (needs file-enriched commits)
    print("[5/7] Tracking model drift...")
    # Enrich daily commits with file info for accurate drift detection
    enriched_daily = []
    for commit in daily_commits:
        try:
            detailed = get_commit_files(base_dir, commit.sha)
            enriched_daily.append(detailed)
        except Exception:
            enriched_daily.append(commit)
    drift = track_drift(snapshots, enriched_daily, checkpoint_interval)
    print(
        f"  Avg freshness: {drift.avg_freshness:.1f}, Update needed every {drift.recommended_update_frequency} commits"
    )

    # Step 7: Cohesion analysis (reuse enriched daily commits)
    print("[6/7] Analyzing co-change cohesion...")
    final_model = snapshots[-1].model if snapshots else None
    cohesion = analyze_cohesion(enriched_daily, final_model)
    print(
        f"  Component cohesion: {cohesion.intra_component_cohesion:.0%}, System cohesion: {cohesion.intra_system_cohesion:.0%}"
    )
    print(
        f"  Cross-component: {cohesion.cross_boundary_rate:.0%}, Cross-system: {cohesion.cross_system_rate:.0%}"
    )

    # Step 8: Regenability
    print("[7/7] Scoring regenability...")
    regen = score_regenability(final_model)
    print(f"  Overall: {regen.overall_grade} ({regen.overall_score:.0f}%)")
    print(
        f"  Components avg: {regen.component_avg:.0f}%, Capabilities avg: {regen.capability_avg:.0f}%"
    )

    # Phase 2: LLM predictions
    phase2_results = None
    phase2_summary = None
    if phase == "llm":
        from .llm_predictor import run_phase2, summarize_phase2

        print(f"\n=== Phase 2: LLM File Predictions ===")
        print(f"  Relay: {relay_url}")
        print(f"  Sample rate: every {sample_rate} commit(s)")
        print(f"  Commits to evaluate: ~{len(enriched_daily) // sample_rate}")

        phase2_results = run_phase2(
            commits=enriched_daily,
            snapshots=snapshots,
            checkpoint_commits=checkpoints,
            relay_url=relay_url,
            sample_rate=sample_rate,
        )
        phase2_summary = summarize_phase2(phase2_results)

        print(f"\n  --- Phase 2 Results ---")
        print(f"  Predictions: {phase2_summary.total_predictions} ({phase2_summary.errors} errors)")
        print(
            f"  With context:    R={phase2_summary.avg_recall_with_context:.0%} P={phase2_summary.avg_precision_with_context:.0%} F1={phase2_summary.avg_f1_with_context:.0%}"
        )
        print(
            f"  Without context: R={phase2_summary.avg_recall_no_context:.0%} P={phase2_summary.avg_precision_no_context:.0%} F1={phase2_summary.avg_f1_no_context:.0%}"
        )
        print(
            f"  Value-add (lift): Recall +{phase2_summary.recall_lift:+.0%}, F1 +{phase2_summary.f1_lift:+.0%}"
        )
        print(f"  Avg latency: {phase2_summary.avg_latency:.1f}s")

        # Save Phase 2 results
        import json as json_mod

        phase2_out = output_dir_path / "phase2-results.json"
        phase2_data = {
            "summary": {
                "total": phase2_summary.total_predictions,
                "errors": phase2_summary.errors,
                "with_context": {
                    "recall": phase2_summary.avg_recall_with_context,
                    "precision": phase2_summary.avg_precision_with_context,
                    "f1": phase2_summary.avg_f1_with_context,
                },
                "no_context": {
                    "recall": phase2_summary.avg_recall_no_context,
                    "precision": phase2_summary.avg_precision_no_context,
                    "f1": phase2_summary.avg_f1_no_context,
                },
                "lift": {"recall": phase2_summary.recall_lift, "f1": phase2_summary.f1_lift},
                "avg_latency_s": phase2_summary.avg_latency,
            },
            "predictions": [
                {
                    "sha": r.sha,
                    "date": r.date,
                    "message": r.message[:100],
                    "actual_files": r.actual_files[:20],
                    "predicted_with_context": r.predicted_files_with_context[:20],
                    "predicted_no_context": r.predicted_files_no_context[:20],
                    "recall_with": r.recall_with_context,
                    "precision_with": r.precision_with_context,
                    "f1_with": r.f1_with_context,
                    "recall_no": r.recall_no_context,
                    "precision_no": r.precision_no_context,
                    "f1_no": r.f1_no_context,
                    "error": r.error,
                }
                for r in phase2_results
            ],
        }
        output_dir_path.mkdir(parents=True, exist_ok=True)
        phase2_out.write_text(json_mod.dumps(phase2_data, indent=2))
        print(f"  Saved to: {phase2_out}")

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
