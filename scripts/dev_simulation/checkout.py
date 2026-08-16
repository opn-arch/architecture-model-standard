"""Git operations for the development simulation benchmark."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class CommitInfo:
    """A single git commit."""

    sha: str
    date: str  # ISO format
    message: str
    files_changed: list[str] = field(default_factory=list)
    files_added: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


def _run_git(repo_dir: Path, *args: str, timeout: int = 60) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr[:200]}")
    return result.stdout


def clone_repo(url: str, target_dir: Path, days: int = 180) -> None:
    """Clone a repo with enough history for the benchmark."""
    if target_dir.exists() and (target_dir / ".git").exists():
        print(f"  Repo already cloned at {target_dir}")
        return

    target_dir.mkdir(parents=True, exist_ok=True)

    # Shallow clone with enough depth for daily commits
    # Use --shallow-since for date-based shallow clone
    since_date = (datetime.now() - timedelta(days=days + 7)).strftime("%Y-%m-%d")
    subprocess.run(
        ["git", "clone", "--shallow-since", since_date, url, str(target_dir)],
        check=True,
        timeout=120,
    )
    print(f"  Cloned {url} to {target_dir}")


def get_daily_commits(repo_dir: Path, days: int = 180) -> list[CommitInfo]:
    """Get one commit per day (last commit of each day) for the past N days."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Get all commits with dates
    log_output = _run_git(
        repo_dir,
        "log",
        "--format=%H|%aI|%s",
        f"--since={since}",
        "--reverse",
        timeout=30,
    )

    if not log_output.strip():
        return []

    # Group by date, take last commit per day
    daily: dict[str, CommitInfo] = {}
    for line in log_output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        sha, date_str, message = parts
        day = date_str[:10]  # YYYY-MM-DD
        daily[day] = CommitInfo(sha=sha, date=date_str, message=message)

    # Sort by date
    commits = [daily[k] for k in sorted(daily.keys())]
    return commits


def get_commits_between(repo_dir: Path, sha_a: str, sha_b: str) -> list[CommitInfo]:
    """Get all commits between two SHAs (exclusive of sha_a, inclusive of sha_b)."""
    log_output = _run_git(
        repo_dir,
        "log",
        "--format=%H|%aI|%s",
        f"{sha_a}..{sha_b}",
        "--reverse",
        timeout=30,
    )

    commits = []
    for line in log_output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        sha, date_str, message = parts
        commits.append(CommitInfo(sha=sha, date=date_str, message=message))

    return commits


def get_commit_files(repo_dir: Path, sha: str) -> CommitInfo:
    """Get detailed file changes for a specific commit."""
    # Get basic info
    info_output = _run_git(repo_dir, "log", "-1", "--format=%H|%aI|%s", sha)
    parts = info_output.strip().split("|", 2)
    commit = CommitInfo(sha=parts[0], date=parts[1], message=parts[2] if len(parts) > 2 else "")

    # Get file changes
    diff_output = _run_git(repo_dir, "diff-tree", "--no-commit-id", "-r", "--name-status", sha)
    for line in diff_output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) < 2:
            continue
        status, filepath = parts[0], parts[1]
        if status.startswith("A"):
            commit.files_added.append(filepath)
        elif status.startswith("D"):
            commit.files_deleted.append(filepath)
        else:
            commit.files_changed.append(filepath)

    # Get stats
    stat_output = _run_git(repo_dir, "diff-tree", "--no-commit-id", "--stat", sha)
    for line in stat_output.strip().split("\n"):
        if "insertion" in line or "deletion" in line:
            # Parse "X files changed, Y insertions(+), Z deletions(-)"
            import re

            ins = re.search(r"(\d+) insertion", line)
            dels = re.search(r"(\d+) deletion", line)
            if ins:
                commit.insertions = int(ins.group(1))
            if dels:
                commit.deletions = int(dels.group(1))

    return commit


def checkout(repo_dir: Path, sha: str) -> None:
    """Checkout a specific commit (detached HEAD)."""
    _run_git(repo_dir, "checkout", "--force", sha, timeout=30)


def get_all_files(repo_dir: Path) -> list[str]:
    """Get all tracked files at current checkout."""
    output = _run_git(repo_dir, "ls-files")
    return [f for f in output.strip().split("\n") if f.strip()]
