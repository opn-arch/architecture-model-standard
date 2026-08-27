"""Auto-correction applier for LLM review corrections."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .stage_review import Correction

SAFE_FIELDS = {"intent", "moes", "failure_modes", "trade_offs", "status", "goals", "layer"}
STRUCTURAL_FIELDS = {"name", "id", "files", "relationships"}
CONFIDENCE_THRESHOLD = 0.8


@dataclass
class CorrectionLog:
    """Record of corrections applied and skipped."""
    applied: int = 0
    skipped: int = 0
    entries: list[dict[str, Any]] = field(default_factory=list)


def apply_corrections(
    model_dict: dict[str, Any],
    corrections: list[Correction],
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    structural_fields: set[str] | None = None,
) -> CorrectionLog:
    """Apply auto-corrections to a model dict. Returns log of changes."""
    if structural_fields is None:
        structural_fields = STRUCTURAL_FIELDS

    log = CorrectionLog()
    entity_index = _build_entity_index(model_dict)

    for corr in corrections:
        if corr.confidence < confidence_threshold:
            log.skipped += 1
            log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "reason": "low_confidence", "confidence": corr.confidence})
            continue
        if corr.field in structural_fields:
            log.skipped += 1
            log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "reason": "structural_field"})
            continue
        if corr.field not in SAFE_FIELDS:
            log.skipped += 1
            log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "reason": "unknown_field"})
            continue
        entity = entity_index.get(corr.entity_id)
        if entity is None:
            log.skipped += 1
            log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "reason": "entity_not_found"})
            continue
        old_value = entity.get(corr.field, "")
        if corr.action == "add" and isinstance(corr.value, list):
            existing = entity.get(corr.field, [])
            entity[corr.field] = existing + corr.value if isinstance(existing, list) else corr.value
        else:
            entity[corr.field] = corr.value
        log.applied += 1
        log.entries.append({"entity_id": corr.entity_id, "field": corr.field, "action": corr.action, "old": old_value, "new": corr.value, "confidence": corr.confidence})

    return log


def _build_entity_index(model_dict: dict[str, Any]) -> dict[str, dict]:
    """Build id -> entity dict mapping from model dict."""
    index: dict[str, dict] = {}
    entities = model_dict.get("entities", {})
    for entity_type in entities.values():
        if isinstance(entity_type, list):
            for entity in entity_type:
                if isinstance(entity, dict) and "id" in entity:
                    index[entity["id"]] = entity
    return index
