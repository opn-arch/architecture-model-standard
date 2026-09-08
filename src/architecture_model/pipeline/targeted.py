"""Targeted extraction: map changed files → impacted subsystems + M1 decision.

Given a list of changed source files and a repo root that contains
``.architecture-models/<subsystem>/.architecture-model.yaml`` sub-models,
compute which subsystems own any of the changed files (must re-extract)
and whether the M1 aggregation must also re-run (any hit or any unknown
file → yes).

Ownership is derived from ``entities.components[*].files`` in each
sub-model. Files not owned by any subsystem are surfaced as
``unknown_files`` for human/agent investigation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DispatchPlan:
    subsystems_to_extract: list[str] = field(default_factory=list)
    needs_m1_aggregation: bool = False
    unknown_files: list[Path] = field(default_factory=list)


def _load_file_ownership(repo_root: Path) -> dict[str, set[str]]:
    """Return {subsystem_name: set of owned file paths (repo-relative strings)}."""
    ownership: dict[str, set[str]] = {}
    models_dir = repo_root / ".architecture-models"
    if not models_dir.exists():
        return ownership
    for sub_dir in sorted(models_dir.iterdir()):
        if not sub_dir.is_dir():
            continue
        model_path = sub_dir / ".architecture-model.yaml"
        if not model_path.exists():
            continue
        data = yaml.safe_load(model_path.read_text()) or {}
        files: set[str] = set()
        components = (data.get("entities") or {}).get("components") or []
        for comp in components:
            for f in comp.get("files", []) or []:
                files.add(f)
        ownership[sub_dir.name] = files
    return ownership


def compute_dispatch_plan(
    changed_files: list[Path],
    repo_root: Path,
) -> DispatchPlan:
    """Compute the dispatch plan for a set of changed files.

    Parameters
    ----------
    changed_files
        Repo-relative paths of files that have changed.
    repo_root
        Repository root containing ``.architecture-models/``.

    Returns
    -------
    DispatchPlan
        Which subsystems must re-extract, whether M1 aggregation is
        required, and which files could not be attributed.
    """
    ownership = _load_file_ownership(repo_root)
    plan = DispatchPlan()
    for cf in changed_files:
        cf_str = str(cf)
        matched = False
        for sub, files in ownership.items():
            if cf_str in files:
                if sub not in plan.subsystems_to_extract:
                    plan.subsystems_to_extract.append(sub)
                matched = True
        if not matched:
            plan.unknown_files.append(cf)
    plan.needs_m1_aggregation = bool(plan.subsystems_to_extract) or bool(plan.unknown_files)
    return plan
