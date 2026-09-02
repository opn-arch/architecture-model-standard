"""Safe loading of architecture model hierarchies without flattening models."""

from __future__ import annotations

from pathlib import Path

from architecture_model.core.types import ArchitectureModel


def load_model_hierarchy(
    model: ArchitectureModel,
    project_root: str | Path,
) -> tuple[list[ArchitectureModel], list[str]]:
    """Load valid descendant models while rejecting unsafe hierarchy references."""
    from architecture_model.core.parser import load_model

    root = Path(project_root).resolve()
    root_path = Path(getattr(model, "_source_path", root / ".architecture-model.yaml")).resolve()
    models = [model]
    issues: list[str] = []
    visited = {root_path}
    active = {root_path}

    def visit(current: ArchitectureModel, current_path: Path) -> None:
        for system in current.entities.systems:
            if not system.sub_model_ref:
                continue
            local_candidate = (current_path.parent / system.sub_model_ref).resolve()
            root_candidate = (root / system.sub_model_ref).resolve()
            candidate = local_candidate if local_candidate.is_file() else root_candidate
            try:
                candidate.relative_to(root)
            except ValueError:
                issues.append(
                    f"Path traversal in sub-model reference for {system.id}: {system.sub_model_ref}"
                )
                continue
            if candidate in active:
                issues.append(f"Hierarchy cycle detected at {candidate}")
                continue
            if candidate in visited:
                continue
            if not candidate.is_file():
                issues.append(f"Missing sub-model for {system.id}: {system.sub_model_ref}")
                continue
            try:
                child = load_model(candidate)
            except Exception as exc:
                issues.append(f"Invalid sub-model for {system.id}: {exc}")
                continue
            visited.add(candidate)
            active.add(candidate)
            models.append(child)
            visit(child, candidate)
            active.remove(candidate)

    visit(model, root_path)
    return models, issues
