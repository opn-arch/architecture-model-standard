"""LLM-based file prediction for Phase 2 of the Development Simulation Benchmark.

Uses the copilot-relay to ask an LLM which files would need modification
given a commit message (task description). Compares predictions with and
without architecture context to measure the model's value-add.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


@dataclass
class PredictionResult:
    """Result of a single LLM file prediction."""

    sha: str
    date: str
    message: str
    actual_files: list[str] = field(default_factory=list)
    # With architecture context
    predicted_files_with_context: list[str] = field(default_factory=list)
    recall_with_context: float = 0.0
    precision_with_context: float = 0.0
    f1_with_context: float = 0.0
    # Without architecture context (baseline)
    predicted_files_no_context: list[str] = field(default_factory=list)
    recall_no_context: float = 0.0
    precision_no_context: float = 0.0
    f1_no_context: float = 0.0
    # With MCP tool (architect_slice) context
    predicted_files_mcp: list[str] = field(default_factory=list)
    recall_mcp: float = 0.0
    precision_mcp: float = 0.0
    f1_mcp: float = 0.0
    # Per-type metrics (with context)
    source_recall: float = 0.0
    test_recall: float = 0.0
    doc_recall: float = 0.0
    # Metadata
    error: str = ""
    latency_with_context: float = 0.0
    latency_no_context: float = 0.0
    latency_mcp: float = 0.0
    mcp_context_chars: int = 0


def _call_relay(relay_url: str, content: str, system_prompt: str) -> str:
    """Call copilot relay and collect streamed response."""
    import urllib.request

    payload = json.dumps({"content": content, "system_prompt": system_prompt}).encode()
    req = Request(
        f"{relay_url}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    full_text = ""
    with urllib.request.urlopen(req, timeout=120) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line or not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            if data.get("type") == "chunk":
                full_text += data.get("content", "")
            elif data.get("type") == "done":
                break
    return full_text


def _parse_file_list(response: str) -> list[str]:
    """Parse file paths from LLM response.

    Expects files in a code block or one per line with path-like patterns.
    """
    # Try to extract from code block first
    code_block = re.search(r"```(?:\w*\n)?(.*?)```", response, re.DOTALL)
    if code_block:
        lines = code_block.group(1).strip().splitlines()
    else:
        lines = response.strip().splitlines()

    files = []
    for line in lines:
        line = line.strip().lstrip("- ").lstrip("* ").strip("`")
        # Must look like a file path (has / or . extension)
        if line and ("/" in line or "." in line) and not line.startswith("#"):
            # Clean common prefixes
            line = line.lstrip("./")
            files.append(line)
    return files


def _compute_metrics(predicted: list[str], actual: list[str]) -> tuple[float, float, float]:
    """Compute recall, precision, F1 between predicted and actual file sets."""
    if not actual:
        return 0.0, 0.0, 0.0

    pred_set = set(predicted)
    actual_set = set(actual)

    if not pred_set:
        return 0.0, 0.0, 0.0

    tp = len(pred_set & actual_set)
    recall = tp / len(actual_set) if actual_set else 0.0
    precision = tp / len(pred_set) if pred_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return recall, precision, f1


def _classify_file(path: str) -> str:
    """Classify a file as 'source', 'test', or 'doc'."""
    from pathlib import Path as _P

    parts = _P(path).parts
    stem = _P(path).stem
    # Test files
    if any(p in ("tests", "test", "testing") for p in parts[:-1]):
        return "test"
    if stem.startswith("test_") or stem.endswith("_test") or stem == "conftest":
        return "test"
    # Doc files
    if any(p in ("docs", "doc", "documentation") for p in parts):
        return "doc"
    if path.endswith((".rst", ".md", ".txt")) and not path.endswith("requirements.txt"):
        return "doc"
    return "source"


def _compute_typed_recall(predicted: list[str], actual: list[str]) -> tuple[float, float, float]:
    """Compute recall separately for source, test, and doc files.

    Returns: (source_recall, test_recall, doc_recall)
    """
    pred_set = set(predicted)
    source_actual = [f for f in actual if _classify_file(f) == "source"]
    test_actual = [f for f in actual if _classify_file(f) == "test"]
    doc_actual = [f for f in actual if _classify_file(f) == "doc"]

    def _recall(actual_subset: list[str]) -> float:
        if not actual_subset:
            return 0.0
        return len(pred_set & set(actual_subset)) / len(actual_subset)

    return _recall(source_actual), _recall(test_actual), _recall(doc_actual)


def _build_architecture_context(model: Any, commit_files: list[str]) -> str:
    """Build a rich, hierarchical architecture context for LLM prediction.

    Model-based engineering approach: provide the LLM with enough structural
    understanding to reason about change propagation, not just file lists.

    Strategy: Full overview + focused detail on the most relevant system.
    """
    if not model:
        return ""

    # Build reverse maps
    file_map = getattr(model, "_file_component_map", {})
    file_sys_map = getattr(model, "_file_system_map", {})
    import_graph = getattr(model, "_import_graph", {})
    reverse_graph = getattr(model, "_reverse_import_graph", {})

    # Load sub-model data if available (has named components)
    sub_data = getattr(model, "_sub_models_data", None)

    lines = ["# Architecture Model — Textual TUI Framework\n"]
    lines.append("Hierarchical: Systems → Components → Files.")
    lines.append("Use relationships and imports for impact propagation.\n")

    if sub_data:
        # Full overview (compact)
        lines.append("## Systems Overview")
        for sys_name, sys_info in sorted(sub_data.items()):
            comps = sys_info.get("components", [])
            if not comps:
                continue
            comp_names = [c["name"] for c in comps if c.get("files")]
            all_files = [f for c in comps for f in c.get("files", [])]
            lines.append(
                f"- **{sys_name.replace('-', ' ').title()}** ({len(comp_names)} components, {len(all_files)} files)"
            )
            lines.append(f"  Components: {', '.join(comp_names[:10])}")
        lines.append("")

        # Detailed section: ALL systems with files (needed for full recall)
        lines.append("## Detailed Component → File Mapping")
        for sys_name, sys_info in sorted(sub_data.items()):
            comps = sys_info.get("components", [])
            if not comps:
                continue
            lines.append(f"### {sys_name.replace('-', ' ').title()}")
            for comp in comps:
                files = comp.get("files", [])
                if not files:
                    continue
                lines.append(f"  **{comp['name']}**: {', '.join(files)}")
            lines.append("")
    else:
        # Fallback: use file_map grouped by component
        comp_files: dict[str, list[str]] = {}
        for f, cid in file_map.items():
            comp_files.setdefault(cid, []).append(f)
        lines.append("## Components → Files")
        for cid, files in sorted(comp_files.items()):
            lines.append(f"  {cid}: {', '.join(sorted(files))}")
        lines.append("")

    # Import dependencies (focused — only show files with dependencies)
    if import_graph:
        lines.append("## Key Import Dependencies")
        lines.append("(file → files it imports, for predicting cascading changes)")
        # Show only files in the model
        model_files = set(file_map.keys())
        shown = 0
        for src in sorted(import_graph.keys()):
            if src not in model_files:
                continue
            targets_in_model = sorted(t for t in import_graph[src] if t in model_files)
            if targets_in_model:
                lines.append(f"  {src} → {', '.join(targets_in_model[:6])}")
                shown += 1
                if shown >= 60:
                    remaining = sum(1 for s in import_graph if s in model_files) - shown
                    if remaining > 0:
                        lines.append(f"  ... +{remaining} more import relationships")
                    break
        lines.append("")

    # Reverse imports (who depends on each file)
    if reverse_graph:
        lines.append("## Reverse Dependencies (who imports this file)")
        lines.append("(Use this to find files that might need updating when a file changes)")
        model_files = set(file_map.keys())
        shown = 0
        for tgt in sorted(reverse_graph.keys()):
            if tgt not in model_files:
                continue
            importers = sorted(s for s in reverse_graph[tgt] if s in model_files)
            if importers:
                lines.append(f"  {tgt} ← {', '.join(importers[:6])}")
                shown += 1
                if shown >= 40:
                    break
        lines.append("")

    # System-level relationships
    rels = model.relationships or []
    if rels:
        lines.append("## System-Level Dependencies")
        for r in rels:
            rtype = r.type.value if hasattr(r.type, "value") else str(r.type)
            lines.append(f"  {r.from_id} --{rtype}--> {r.to_id}")
        lines.append("")

    # Test mapping (source → test files that import it)
    test_map = getattr(model, "_test_map", {})
    if test_map:
        lines.append("## Test Mapping (source file → test files that import it)")
        lines.append("(If you change a source file, these tests likely need updating)")
        shown = 0
        for src_file in sorted(test_map.keys()):
            tests = test_map[src_file]
            tests_str = ", ".join(sorted(tests)[:5])
            if len(tests) > 5:
                tests_str += f" +{len(tests) - 5} more"
            lines.append(f"  {src_file} → {tests_str}")
            shown += 1
            if shown >= 80:
                remaining = len(test_map) - shown
                if remaining > 0:
                    lines.append(f"  ... +{remaining} more source→test mappings")
                break
        lines.append("")

    return "\n".join(lines)


def _build_file_list(model: Any, repo_path: str = "") -> str:
    """Build a flat file list (for no-context baseline).

    If repo_path is provided, scans the actual filesystem for ALL files.
    Otherwise falls back to model files only.
    This is the 'without architecture' baseline to measure value-add.
    """
    all_files: set[str] = set()

    if repo_path:
        from pathlib import Path as _P

        repo = _P(repo_path)
        for f in repo.rglob("*.py"):
            parts = f.parts
            if any(
                p in parts
                for p in (".git", "__pycache__", ".tox", "node_modules", ".benchmark-cache")
            ):
                continue
            try:
                rel = str(f.relative_to(repo))
                all_files.add(rel)
            except ValueError:
                pass

    if not all_files and model:
        file_map = getattr(model, "_file_component_map", {})
        all_files.update(file_map.keys())
        if not all_files:
            for comp in model.entities.components or []:
                for f in comp.files or []:
                    all_files.add(str(f))

    if not all_files:
        return ""

    sorted_files = sorted(all_files)
    lines = ["# Repository Files (flat list, no architecture)\n"]
    for f in sorted_files[:500]:
        lines.append(f"- {f}")
    if len(sorted_files) > 500:
        lines.append(f"... and {len(sorted_files) - 500} more files")
    return "\n".join(lines)


def is_predictable_commit(message: str, files_changed: list[str] | None = None) -> bool:
    """Filter out commits that are inherently unpredictable from their message alone.

    Unpredictable = vague messages where no model could help.
    Also filters doc-only and CI-only commits (architecture can't help with those).
    Returns True if the commit message has enough info for meaningful prediction.
    """
    msg = message.lower().strip()

    # Too short to be meaningful
    if len(msg) < 15:
        return False

    # Vague/generic messages that don't identify a target
    vague_patterns = [
        "fix typo",
        "typos",
        "formatting",
        "whitespace",
        "minor fix",
        "cleanup",
        "clean up",
        "wip",
        "another edge",
        "more fixes",
        "misc",
        "various",
        "remove superfluous",
        "logic not",
    ]
    for p in vague_patterns:
        if p in msg:
            return False

    # If we have file info, filter commits that architecture can't help with
    if files_changed:
        has_source = any(
            f.endswith(".py")
            and "/tests/" not in f
            and "/test/" not in f
            and not f.startswith("docs/")
            and not f.startswith("doc/")
            and not f.endswith(".txt")
            and not f.endswith(".rst")
            and not f.endswith(".yml")
            and not f.endswith(".yaml")
            and not f.endswith(".cfg")
            and not f.endswith(".toml")
            for f in files_changed
        )
        if not has_source:
            # Doc-only, CI-only, or test-only commit — architecture model can't help
            return False

    return True


SYSTEM_PROMPT = """You are a software architecture expert performing impact analysis. Given a task description (commit message) and architecture context, predict which files would need modification.

Your reasoning process:
1. Identify which component(s) the task relates to based on names and descriptions
2. Find the primary files in that component
3. Use import dependencies to identify secondary files that would need changes (callers, dependents, tests)
4. Consider: CHANGELOG.md changes for user-facing fixes, test files for bug fixes, __init__.py for new exports

Rules:
- Return ONLY a list of file paths, one per line, in a code block
- Be specific — use exact paths from the architecture model
- Include both primary files AND files that would need updating due to dependencies
- For bug fixes: include the fix file + test file + CHANGELOG.md
- For new features: include implementation + tests + docs + __init__ exports
- Do NOT explain your reasoning, ONLY output the file list"""

PROMPT_WITH_CONTEXT = """Given this architecture model and the task below, predict which files would need to be modified.

{context}

## Task Description
"{message}"

Using the architecture structure and dependency information above, predict ALL files that would need to change (including tests, docs, and dependent files):"""

PROMPT_NO_CONTEXT = """Given this list of files in a repository and the task below, predict which files would need to be modified.

{file_list}

## Task Description
"{message}"

Based only on file names and paths, predict which files would need to change:"""


def predict_files(
    commit: Any,
    model: Any,
    relay_url: str = "http://localhost:8400",
    skip_baseline: bool = False,
    repo_path: str = "",
) -> PredictionResult:
    """Predict which files a commit would change, with and without architecture context.

    Args:
        commit: CommitInfo with sha, date, message, files_changed
        model: Architecture model (from snapshot)
        relay_url: Copilot relay URL
        skip_baseline: If True, skip the no-context baseline prediction
    """
    result = PredictionResult(
        sha=commit.sha,
        date=commit.date,
        message=commit.message,
        actual_files=commit.files_changed or [],
    )

    if not commit.message or not result.actual_files:
        result.error = "No message or no files"
        return result

    # Build context — use full architecture + focused section if possible
    context = _build_architecture_context(model, commit.files_changed)

    # Prediction WITH architecture context
    try:
        prompt = PROMPT_WITH_CONTEXT.format(context=context, message=commit.message)

        t0 = time.monotonic()
        response = _call_relay(relay_url, prompt, SYSTEM_PROMPT)
        result.latency_with_context = time.monotonic() - t0

        result.predicted_files_with_context = _parse_file_list(response)
        r, p, f1 = _compute_metrics(result.predicted_files_with_context, result.actual_files)
        result.recall_with_context = r
        result.precision_with_context = p
        result.f1_with_context = f1
        # Per-type breakdown
        sr, tr, dr = _compute_typed_recall(result.predicted_files_with_context, result.actual_files)
        result.source_recall = sr
        result.test_recall = tr
        result.doc_recall = dr
    except Exception as e:
        result.error = f"with_context: {e}"
        return result

    # Prediction WITHOUT context (baseline)
    if not skip_baseline:
        try:
            file_list = _build_file_list(model, repo_path=repo_path)
            prompt = PROMPT_NO_CONTEXT.format(file_list=file_list, message=commit.message)

            t0 = time.monotonic()
            response = _call_relay(relay_url, prompt, SYSTEM_PROMPT)
            result.latency_no_context = time.monotonic() - t0

            result.predicted_files_no_context = _parse_file_list(response)
            r, p, f1 = _compute_metrics(result.predicted_files_no_context, result.actual_files)
            result.recall_no_context = r
            result.precision_no_context = p
            result.f1_no_context = f1
        except Exception as e:
            result.error = f"no_context: {e}"

    return result


def _get_mcp_context(repo_path: str, commit_message: str) -> str:
    """Get context via architect_slice MCP tool, simulating real developer workflow.

    Strategy (what a smart AI developer would do):
    1. Call slice with focus='all' for overview
    2. If the repo has sub-models, try to identify relevant system from message
       and slice that specific sub-model for deeper context
    """
    import asyncio
    import sys as _sys

    _sys.path.insert(0, "/Users/baigm2/Documents/Projects/opencode-arch/src")
    from opencode_arch.mcp.tools.slice import slice_context
    from pathlib import Path as _Path

    path = _Path(repo_path)
    parts = []

    # Step 1: Get full model overview
    overview = asyncio.run(slice_context(str(path), focus="all", budget=4000, detail="full"))
    parts.append(overview)

    # Step 2: Try to slice relevant sub-model based on commit keywords
    sub_models_dir = path / ".architecture" / ".architecture-models"
    if not sub_models_dir.exists():
        sub_models_dir = path / ".architecture-models"
    if sub_models_dir.exists():
        msg_lower = commit_message.lower()
        msg_words = set(msg_lower.replace("-", " ").replace("_", " ").split())

        # Score all sub-model directories by word overlap with commit message
        scored_subdirs: list[tuple[int, "_Path"]] = []
        for subdir in sub_models_dir.iterdir():
            if not subdir.is_dir():
                continue
            sub_model = subdir / ".architecture-model.yaml"
            if not sub_model.exists():
                continue
            # Extract words from directory name (e.g., "layouts-widgets-core" → {"layouts", "widgets", "core"})
            dir_words = set(subdir.name.replace("-", " ").replace("_", " ").split())
            # Score: number of overlapping words (only count words > 2 chars)
            overlap = sum(1 for w in dir_words if len(w) > 2 and w in msg_words)
            # Also check if any dir word is a substring of commit message
            substring_score = sum(1 for w in dir_words if len(w) > 3 and w in msg_lower)
            total_score = overlap * 2 + substring_score
            if total_score > 0:
                scored_subdirs.append((total_score, subdir))

        # Pick the best match (above threshold of 1)
        matched_subdir = None
        if scored_subdirs:
            scored_subdirs.sort(key=lambda x: x[0], reverse=True)
            if scored_subdirs[0][0] >= 1:
                matched_subdir = scored_subdirs[0][1]

        if matched_subdir:
            sub_slice = asyncio.run(
                slice_context(str(matched_subdir), focus="all", budget=4000, detail="full")
            )
            parts.append(f"\n## Focused System: {matched_subdir.name}\n{sub_slice}")

    return "\n".join(parts)


def predict_files_mcp(
    commit: Any,
    repo_path: str,
    relay_url: str = "http://localhost:8400",
) -> PredictionResult:
    """Predict files using MCP architect_slice tool as context source.

    This simulates how a real AI developer would use the MCP tools:
    1. Call architect_slice to get architecture context
    2. Use that context + commit message to predict file changes
    """
    result = PredictionResult(
        sha=commit.sha,
        date=commit.date,
        message=commit.message,
        actual_files=commit.files_changed or [],
    )

    if not commit.message or not result.actual_files:
        result.error = "No message or no files"
        return result

    try:
        # Get MCP context
        mcp_context = _get_mcp_context(repo_path, commit.message)
        result.mcp_context_chars = len(mcp_context)

        prompt = PROMPT_WITH_CONTEXT.format(context=mcp_context, message=commit.message)

        t0 = time.monotonic()
        response = _call_relay(relay_url, prompt, SYSTEM_PROMPT)
        result.latency_mcp = time.monotonic() - t0

        result.predicted_files_mcp = _parse_file_list(response)
        r, p, f1 = _compute_metrics(result.predicted_files_mcp, result.actual_files)
        result.recall_mcp = r
        result.precision_mcp = p
        result.f1_mcp = f1
    except Exception as e:
        result.error = f"mcp: {e}"

    return result


def run_phase2(
    commits: list[Any],
    snapshots: list[Any],
    checkpoint_commits: list[Any],
    relay_url: str = "http://localhost:8400",
    sample_rate: int = 1,
) -> list[PredictionResult]:
    """Run Phase 2 predictions for sampled commits.

    For each sampled commit, uses the most recent checkpoint's model
    as context (simulating real development where model isn't always fresh).

    Args:
        commits: All daily commits (enriched with files_changed)
        snapshots: Model snapshots at checkpoints
        checkpoint_commits: The CommitInfo objects at checkpoint boundaries
        relay_url: Copilot relay URL
        sample_rate: Predict every Nth commit (1=all, 3=every 3rd)
    """
    results = []

    # Build checkpoint index: sha -> snapshot
    checkpoint_map = {}
    for cp, snap in zip(checkpoint_commits, snapshots):
        checkpoint_map[cp.sha] = snap

    # For each commit, find the most recent preceding checkpoint model
    current_model = None
    checkpoint_idx = 0

    for i, commit in enumerate(commits):
        # Update current model if we've passed a checkpoint
        if (
            checkpoint_idx < len(checkpoint_commits)
            and commit.sha == checkpoint_commits[checkpoint_idx].sha
        ):
            current_model = snapshots[checkpoint_idx].model
            checkpoint_idx += 1

        # Sample rate
        if i % sample_rate != 0:
            continue

        # Skip if no model yet (before first checkpoint)
        if current_model is None:
            continue

        # Skip commits with no files or trivial messages
        if not getattr(commit, "files_changed", None):
            continue
        if not is_predictable_commit(commit.message, getattr(commit, "files_changed", None)):
            continue

        print(
            f"    [{len(results) + 1}] {commit.date[:10]} {commit.sha[:8]}: {commit.message[:60]}...",
            end=" ",
            flush=True,
        )

        pred = predict_files(commit, current_model, relay_url=relay_url)
        results.append(pred)

        if pred.error:
            print(f"ERR: {pred.error[:40]}")
        else:
            print(
                f"R={pred.recall_with_context:.0%}/P={pred.precision_with_context:.0%} (baseline R={pred.recall_no_context:.0%})"
            )

    return results


@dataclass
class Phase2Summary:
    """Aggregate Phase 2 results."""

    total_predictions: int = 0
    errors: int = 0
    # With context
    avg_recall_with_context: float = 0.0
    avg_precision_with_context: float = 0.0
    avg_f1_with_context: float = 0.0
    # Baseline (no context)
    avg_recall_no_context: float = 0.0
    avg_precision_no_context: float = 0.0
    avg_f1_no_context: float = 0.0
    # Per-type (with context)
    avg_source_recall: float = 0.0
    avg_test_recall: float = 0.0
    avg_doc_recall: float = 0.0
    # Value-add
    recall_lift: float = 0.0  # with_context - no_context
    f1_lift: float = 0.0
    # Latency
    avg_latency: float = 0.0


def summarize_phase2(results: list[PredictionResult]) -> Phase2Summary:
    """Compute aggregate metrics from Phase 2 predictions."""
    summary = Phase2Summary(total_predictions=len(results))

    valid = [r for r in results if not r.error]
    summary.errors = len(results) - len(valid)

    if not valid:
        return summary

    summary.avg_recall_with_context = sum(r.recall_with_context for r in valid) / len(valid)
    summary.avg_precision_with_context = sum(r.precision_with_context for r in valid) / len(valid)
    summary.avg_f1_with_context = sum(r.f1_with_context for r in valid) / len(valid)

    summary.avg_recall_no_context = sum(r.recall_no_context for r in valid) / len(valid)
    summary.avg_precision_no_context = sum(r.precision_no_context for r in valid) / len(valid)
    summary.avg_f1_no_context = sum(r.f1_no_context for r in valid) / len(valid)

    # Per-type recall
    summary.avg_source_recall = sum(r.source_recall for r in valid) / len(valid)
    summary.avg_test_recall = sum(r.test_recall for r in valid) / len(valid)
    summary.avg_doc_recall = sum(r.doc_recall for r in valid) / len(valid)

    summary.recall_lift = summary.avg_recall_with_context - summary.avg_recall_no_context
    summary.f1_lift = summary.avg_f1_with_context - summary.avg_f1_no_context

    summary.avg_latency = sum(r.latency_with_context for r in valid) / len(valid)

    return summary
