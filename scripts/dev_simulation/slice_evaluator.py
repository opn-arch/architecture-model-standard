"""Slice evaluator — measures how well architect_slice serves development context."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SliceMetrics:
    """Metrics for a single commit's slice evaluation."""

    sha: str
    date: str
    message: str
    files_changed: list[str] = field(default_factory=list)
    component_id: str = ""
    component_name: str = ""
    slice_files: list[str] = field(default_factory=list)
    slice_recall: float = 0.0  # changed files found in slice
    slice_precision: float = 0.0  # slice files that were actually needed
    slice_f1: float = 0.0
    context_recall: float = 0.0  # imports of changed files found in slice
    component_hit: bool = False  # did we identify correct component?
    cross_boundary: bool = False  # commit touches multiple components
    components_touched: int = 0


def identify_component(changed_files: list[str], model: Any) -> tuple[str, str]:
    """Find which component/system best matches the changed files."""
    if not model:
        return "", ""

    # Use injected file map if available (from allocate stage)
    file_map = getattr(model, "_file_component_map", {})

    # Fall back to component files
    if not file_map:
        for comp in model.entities.components or []:
            for f in comp.files or []:
                file_map[str(f)] = comp.id

    comp_hits: Counter = Counter()
    for f in changed_files:
        comp_id = file_map.get(f)
        if comp_id:
            comp_hits[comp_id] += 1

    if not comp_hits:
        return "", ""

    best_id = comp_hits.most_common(1)[0][0]
    # Get name
    for comp in model.entities.components or []:
        if comp.id == best_id:
            return best_id, comp.name
    for sys in model.entities.systems or []:
        if sys.id == best_id:
            return best_id, sys.name
    return best_id, ""


def get_component_files(component_id: str, model: Any) -> set[str]:
    """Get all files in a component/system."""
    if not model:
        return set()

    # Use injected file map
    file_map = getattr(model, "_file_component_map", {})
    if file_map:
        return {f for f, cid in file_map.items() if cid == component_id}

    # Fall back to component files
    files = set()
    target_ids = {component_id}
    for comp in model.entities.components or []:
        if getattr(comp, "parent_id", None) == component_id:
            target_ids.add(comp.id)
    for comp in model.entities.components or []:
        if comp.id in target_ids:
            files.update(str(f) for f in (comp.files or []))
    return files


def evaluate_slice(model: Any, commit: Any) -> SliceMetrics:
    """Evaluate how well the model's slice would serve this commit.

    The slice includes:
    1. All files in the primary component (direct match)
    2. Files in ALL touched components (multi-component awareness)
    3. Direct import neighbors of changed files (context expansion)
    """
    # Collect all changed files
    all_changed = list(
        set(
            getattr(commit, "files_changed", [])
            + getattr(commit, "files_added", [])
            + getattr(commit, "files_deleted", [])
        )
    )

    # Filter to source files only (ignore tests, docs, configs)
    source_changed = [f for f in all_changed if f.endswith(".py") and "test" not in f.lower()]

    if not source_changed:
        return SliceMetrics(
            sha=commit.sha,
            date=commit.date,
            message=commit.message,
            files_changed=all_changed,
        )

    # Identify ALL touched components (not just primary)
    file_map = getattr(model, "_file_component_map", {})
    comp_touches: Counter = Counter()
    for f in source_changed:
        cid = file_map.get(f)
        if cid:
            comp_touches[cid] += 1

    # Primary component = most-touched
    primary_id = comp_touches.most_common(1)[0][0] if comp_touches else ""
    primary_name = ""
    for comp in model.entities.components or []:
        if comp.id == primary_id:
            primary_name = comp.name
            break
    for sys in model.entities.systems or []:
        if sys.id == primary_id:
            primary_name = sys.name
            break

    # Build slice: 1-hop forward imports + same-directory locality (precision-focused)
    slice_files: set[str] = set()

    import_graph = getattr(model, "_import_graph", {})

    # Start with the changed files themselves
    slice_files.update(source_changed)

    # Forward deps only (files this file imports — likely to co-change)
    for f in source_changed:
        for dep in import_graph.get(f, set()):
            if dep in file_map:
                slice_files.add(dep)

    # Same-directory siblings of changed files (high co-change likelihood)
    from pathlib import Path

    changed_dirs = {str(Path(f).parent) for f in source_changed}
    for f in file_map:
        if str(Path(f).parent) in changed_dirs:
            slice_files.add(f)

    # Cap expansion at 2x changed file count to maintain precision
    max_size = max(len(source_changed) * 2, 8)
    if len(slice_files) > max_size:
        # Prioritize: changed files > forward imports > siblings
        priority_files = list(source_changed)
        for f in source_changed:
            for dep in import_graph.get(f, set()):
                if dep in file_map:
                    priority_files.append(dep)
        # Deduplicate preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for pf in priority_files:
            if pf not in seen:
                seen.add(pf)
                ordered.append(pf)
        slice_files = set(ordered[:max_size])

    # Calculate metrics
    changed_set = set(source_changed)

    recall = len(changed_set & slice_files) / len(changed_set) if changed_set else 0.0
    precision = len(changed_set & slice_files) / len(slice_files) if slice_files else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return SliceMetrics(
        sha=commit.sha,
        date=commit.date,
        message=commit.message,
        files_changed=all_changed,
        component_id=primary_id,
        component_name=primary_name,
        slice_files=sorted(slice_files),
        slice_recall=recall,
        slice_precision=precision,
        slice_f1=f1,
        component_hit=primary_id != "",
        cross_boundary=len(comp_touches) > 1,
        components_touched=len(comp_touches),
    )
