"""Apply ModelPatch proposals to ArchitectureModel.

The executor supports three operations:
  - ``add``:     append value to entities.<target_kind> list
  - ``remove``:  drop entity with matching target_id from any entities list
  - ``replace``: setattr(entity[target_id], field, value)

Note: the validator (``ai.validators._VALID_OPS``) also lists ``move`` as a
syntactically valid op, but the semantics of ``move`` are not yet specified;
the executor raises ``ParseError`` for it.
"""
from __future__ import annotations

import copy
import dataclasses
from typing import Any

from architecture_model.ai.proposals import ModelPatch
from architecture_model.core.errors import ParseError
from architecture_model.core.types import ArchitectureModel, Entities

__all__ = ["apply_model_patch"]


def apply_model_patch(
    model: ArchitectureModel, patch: ModelPatch
) -> ArchitectureModel:
    """Apply ``patch`` to ``model``, returning a new ``ArchitectureModel``.

    Does not mutate ``model``. Raises :class:`ParseError` on unknown or
    malformed operations.
    """
    result = copy.deepcopy(model)
    for op in patch.operations:
        if not isinstance(op, dict):
            raise ParseError(f"patch op must be a dict: {op!r}")
        kind = op.get("op")
        if kind == "add":
            _apply_add(result, op)
        elif kind == "remove":
            _apply_remove(result, op)
        elif kind == "replace":
            _apply_replace(result, op)
        elif kind == "move":
            raise ParseError("patch op 'move' is not yet supported by executor")
        else:
            raise ParseError(f"unknown patch op: {kind!r}")
    return result


def _entity_lists(entities: Entities) -> list[tuple[str, list]]:
    """Return (field_name, list) pairs for every entity collection."""
    return [(f.name, getattr(entities, f.name)) for f in dataclasses.fields(entities)]


def _apply_add(model: ArchitectureModel, op: dict[str, Any]) -> None:
    target_kind = op.get("target_kind")
    value = op.get("value")
    if not target_kind or not isinstance(value, dict):
        raise ParseError(
            f"add op requires 'target_kind' and dict 'value': {op!r}"
        )
    # Re-parse the value through the model parser so we get the right dataclass
    # instance for the target list. Wrap into a minimal model shape and pluck
    # the resulting list.
    from architecture_model.core.parser import _parse_raw

    raw = {
        "meta": {"project": "_patch", "schema_version": "1.3"},
        "entities": {target_kind: [value]},
        "relationships": [],
    }
    try:
        parsed = _parse_raw(raw)
    except Exception as exc:  # pragma: no cover - defensive
        raise ParseError(f"add op value failed to parse: {exc}") from exc
    try:
        new_items = getattr(parsed.entities, target_kind)
    except AttributeError as exc:
        raise ParseError(f"unknown target_kind {target_kind!r}") from exc
    if not new_items:
        raise ParseError(f"add op produced no entity for target_kind {target_kind!r}")
    try:
        getattr(model.entities, target_kind).append(new_items[0])
    except AttributeError as exc:
        raise ParseError(f"unknown target_kind {target_kind!r}") from exc


def _apply_remove(model: ArchitectureModel, op: dict[str, Any]) -> None:
    target_id = op.get("target_id")
    if not target_id:
        raise ParseError(f"remove op requires 'target_id': {op!r}")
    removed = False
    for _name, items in _entity_lists(model.entities):
        for i, ent in enumerate(list(items)):
            if getattr(ent, "id", None) == target_id:
                items.pop(i)
                removed = True
                break
        if removed:
            return
    # Silent no-op if not found — validator flags unknown-entity separately.


def _apply_replace(model: ArchitectureModel, op: dict[str, Any]) -> None:
    target_id = op.get("target_id")
    field_name = op.get("field")
    if not target_id or not field_name:
        raise ParseError(
            f"replace op requires 'target_id' and 'field': {op!r}"
        )
    value = op.get("value")
    for _name, items in _entity_lists(model.entities):
        for ent in items:
            if getattr(ent, "id", None) == target_id:
                if not hasattr(ent, field_name):
                    raise ParseError(
                        f"entity {target_id!r} has no field {field_name!r}"
                    )
                setattr(ent, field_name, value)
                return
    # Silent no-op if not found.
