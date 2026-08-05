"""Manage structured architecture corrections stored in .architecture/corrections.yaml."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CORRECTION_TYPES = [
    "split_component",
    "merge_components",
    "add_component",
    "remove_component",
    "add_relationship",
    "remove_relationship",
    "rename",
    "reclassify",
]

_CORRECTIONS_FILE = ".architecture/corrections.yaml"


def load_corrections(repo_path: Path) -> list[dict]:
    """Load corrections from .architecture/corrections.yaml. Returns [] if missing."""
    path = repo_path / _CORRECTIONS_FILE
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("corrections", [])


def store_correction(repo_path: Path, correction: dict) -> dict:
    """Append a correction with auto-generated id, created_at, and applied=false."""
    existing = load_corrections(repo_path)

    # Auto-generate ID
    max_n = 0
    for c in existing:
        cid = c.get("id", "")
        if cid.startswith("COR-"):
            try:
                max_n = max(max_n, int(cid[4:]))
            except ValueError:
                pass
    next_id = f"COR-{max_n + 1}"

    correction = dict(correction)
    correction["id"] = next_id
    correction["applied"] = False
    correction["created_at"] = datetime.now(timezone.utc).isoformat()

    existing.append(correction)

    # Write
    path = repo_path / _CORRECTIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump({"corrections": existing}, default_flow_style=False, sort_keys=False))

    return correction


def apply_corrections(model: Any, corrections: list[dict]) -> tuple[Any, list[str]]:
    """Apply unapplied rename and add_relationship corrections to a model."""
    applied_ids: list[str] = []

    for cor in corrections:
        if cor.get("applied", False):
            continue

        ctype = cor.get("type")

        if ctype == "rename":
            target_id = cor.get("target")
            new_name = cor.get("suggestion", {}).get("name")
            if target_id and new_name:
                entity = _find_entity(model, target_id)
                if entity is not None:
                    entity.name = new_name
                    applied_ids.append(cor["id"])

        elif ctype == "add_relationship":
            suggestion = cor.get("suggestion", {})
            from_id = suggestion.get("from")
            to_id = suggestion.get("to")
            rel_type = suggestion.get("type")
            if from_id and to_id and rel_type:
                from architecture_model.core.types import Relationship, RelationType
                model.relationships.append(
                    Relationship(
                        type=RelationType.parse(rel_type),
                        from_id=from_id,
                        to_id=to_id,
                    )
                )
                applied_ids.append(cor["id"])
        # Other types: skip silently

    return model, applied_ids


def mark_applied(repo_path: Path, correction_ids: list[str]) -> None:
    """Mark specified corrections as applied=true in the YAML file."""
    corrections = load_corrections(repo_path)
    for cor in corrections:
        if cor.get("id") in correction_ids:
            cor["applied"] = True

    path = repo_path / _CORRECTIONS_FILE
    path.write_text(yaml.dump({"corrections": corrections}, default_flow_style=False, sort_keys=False))


def _find_entity(model: Any, entity_id: str) -> Any | None:
    """Find an entity by ID across all entity lists."""
    entities = model.entities
    for attr in (
        "actors", "capabilities", "behaviors", "interfaces", "constraints",
        "layers", "components", "systems", "data", "events", "resources",
        "environments", "quality_attributes", "decisions", "lifecycles",
    ):
        for e in getattr(entities, attr, []):
            if e.id == entity_id:
                return e
    return None
