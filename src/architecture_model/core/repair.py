"""Repair architecture models by backfilling missing entities from subsidiary models.

Finds dangling entity references (IDs in relationships that don't exist as entities)
and backfills them from source models (e.g., full-model.yaml, subsystem models).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .parser import load_model, save_model
from .types import ArchitectureModel
from .validator import validate_model


def find_dangling_ids(model: ArchitectureModel) -> set[str]:
    """Find entity IDs referenced in relationships but not defined as entities."""
    defined = model.all_entity_ids
    referenced: set[str] = set()
    for rel in model.relationships:
        referenced.add(rel.from_id)
        referenced.add(rel.to_id)
    return referenced - defined


def _collect_entities_by_id(model: ArchitectureModel) -> dict[str, Any]:
    """Build a dict mapping entity_id -> (list_name, entity_object) for all entities."""
    index: dict[str, tuple[str, Any]] = {}
    entity_lists = [
        ("actors", model.entities.actors),
        ("capabilities", model.entities.capabilities),
        ("behaviors", model.entities.behaviors),
        ("interfaces", model.entities.interfaces),
        ("constraints", model.entities.constraints),
        ("layers", model.entities.layers),
        ("components", model.entities.components),
        ("systems", model.entities.systems),
        ("requirements", model.entities.requirements),
        ("data", model.entities.data),
        ("events", model.entities.events),
        ("resources", model.entities.resources),
        ("environments", model.entities.environments),
        ("quality_attributes", model.entities.quality_attributes),
        ("decisions", model.entities.decisions),
        ("lifecycles", model.entities.lifecycles),
        ("external_systems", model.entities.external_systems),
    ]
    for list_name, entities in entity_lists:
        for e in entities:
            index[e.id] = (list_name, e)
    return index


def backfill_from_source(
    model: ArchitectureModel,
    source: ArchitectureModel,
    return_stats: bool = False,
) -> ArchitectureModel | tuple[ArchitectureModel, dict]:
    """Backfill dangling entity references from a source model.

    Only adds entities that are dangling in `model` and exist in `source`.
    Does not duplicate existing entities.

    Args:
        model: The model to repair (modified in place).
        source: Source model containing potential backfill entities.
        return_stats: If True, return (model, stats_dict).

    Returns:
        The repaired model, or (model, stats) if return_stats=True.
    """
    dangling = find_dangling_ids(model)
    if not dangling:
        if return_stats:
            return model, {"backfilled": 0, "still_dangling": 0}
        return model

    source_index = _collect_entities_by_id(source)
    backfilled = 0

    for eid in dangling:
        if eid in source_index:
            list_name, entity = source_index[eid]
            target_list = getattr(model.entities, list_name)
            # Don't duplicate
            if not any(e.id == eid for e in target_list):
                target_list.append(entity)
                backfilled += 1

    still_dangling = len(find_dangling_ids(model))

    if return_stats:
        return model, {"backfilled": backfilled, "still_dangling": still_dangling}
    return model


def repair_model(
    model_path: str | Path,
    source_paths: list[str | Path] | None = None,
) -> dict:
    """Repair a model by backfilling missing entities from source models.

    Args:
        model_path: Path to the model YAML to repair.
        source_paths: Explicit source model paths. If None, auto-discovers
            YAML files in .architecture-models/ next to the model.

    Returns:
        Stats dict with backfilled count, score_before, score_after, etc.
    """
    model_path = Path(model_path)
    model = load_model(model_path)

    # Score before
    val_before = validate_model(model)
    score_before = val_before.score
    dangling_before = len(find_dangling_ids(model))

    # Auto-discover source models
    if source_paths is None:
        source_paths = []
        models_dir = model_path.parent / ".architecture-models"
        if models_dir.is_dir():
            # Check common locations
            for candidate in [
                models_dir / "full-model.yaml",
                models_dir / ".architecture-model.yaml",
            ]:
                if candidate.is_file():
                    source_paths.append(candidate)
            # Also check subsystem dirs
            for subdir in sorted(models_dir.iterdir()):
                if subdir.is_dir():
                    sub_model = subdir / ".architecture-model.yaml"
                    if sub_model.is_file():
                        source_paths.append(sub_model)

    # Backfill from each source
    total_backfilled = 0
    for sp in source_paths:
        try:
            source = load_model(Path(sp))
            _, stats = backfill_from_source(model, source, return_stats=True)
            total_backfilled += stats["backfilled"]
        except Exception:
            continue

    # Save repaired model
    save_model(model, model_path)

    # Score after
    val_after = validate_model(model)

    return {
        "backfilled": total_backfilled,
        "dangling_before": dangling_before,
        "dangling_after": len(find_dangling_ids(model)),
        "score_before": score_before,
        "score_after": val_after.score,
        "issues_before": len(val_before.issues),
        "issues_after": len(val_after.issues),
    }
