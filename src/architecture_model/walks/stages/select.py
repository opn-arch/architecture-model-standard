"""architecture_model.walks.stages.select — Entity selection.

Given a WalkSpec and a model, produce the set of entities the walk
should audit. Supports two modes:

1. Kind + predicate: filter entities by kind matching scope.kind and
   the predicate expression.
2. Composition: consume the emit payload of a prior walk (scope.from_walk).

Predicate DSL: minimal boolean expression over attribute presence.
Grows only as retrofits demand.
"""

from __future__ import annotations

from typing import Any

from architecture_model.pipeline_v3.substrate import (
    Stage,
    StageContext,
    StageResult,
    wrap_function,
)
from architecture_model.walks.spec.loader import ScopeSpec, WalkSpec

__all__ = ["select_stage", "SelectInput", "SelectOutput"]


# For now, entities are plain dicts. Later we may type them via v3 model types.
Entity = dict[str, Any]


class SelectInput(dict):
    """Input to select stage.

    Keys: ``model`` (dict), ``spec`` (WalkSpec), ``prior_walk_output``
    (optional list of cards from a composed walk).
    """


class SelectOutput(dict):
    """Output: selected entities + carried spec/model."""


def _entities_of_kind(model: dict[str, Any], kind: str) -> list[Entity]:
    """Extract entities of a given kind from the v3 model.

    Recognizes plural keys under ``entities`` (components, capabilities,
    behaviors, interfaces, actors, constraints).
    """
    ents = model.get("entities", {})
    # Map singular scope kind to plural entity bucket.
    bucket_map = {
        "component": "components",
        "capability": "capabilities",
        "behavior": "behaviors",
        "interface": "interfaces",
        "actor": "actors",
        "constraint": "constraints",
    }
    bucket = bucket_map.get(kind, kind + "s")
    return list(ents.get(bucket, []))


def _eval_predicate(predicate: str | None, entity: Entity) -> bool:
    """Evaluate a simple attribute-presence predicate.

    Supported forms:
      - None or "true": always True
      - "has:<attr>": entity has non-empty attribute
      - "missing:<attr>": entity lacks or has empty attribute
      - combined via " and " / " or "
    """
    if predicate is None or predicate.strip() in ("", "true"):
        return True

    def eval_atom(atom: str) -> bool:
        atom = atom.strip()
        if atom == "true":
            return True
        if atom == "false":
            return False
        if atom.startswith("has:"):
            attr = atom[4:].strip()
            v = entity.get(attr)
            return v is not None and v != "" and v != [] and v != {}
        if atom.startswith("missing:"):
            attr = atom[8:].strip()
            v = entity.get(attr)
            return v is None or v == "" or v == [] or v == {}
        # Unknown atom: conservative False
        return False

    # Naive AND/OR split, left-to-right, no parens.
    if " and " in predicate:
        return all(eval_atom(p) for p in predicate.split(" and "))
    if " or " in predicate:
        return any(eval_atom(p) for p in predicate.split(" or "))
    return eval_atom(predicate)


def _run_select(input: SelectInput) -> SelectOutput:
    spec: WalkSpec = input["spec"]
    scope: ScopeSpec = spec.scope

    # Composition: from_walk mode
    if scope.from_walk is not None:
        prior = input.get("prior_walk_output", [])
        entities = [card.get("entity", card) for card in prior]
    else:
        model = input["model"]
        candidates = _entities_of_kind(model, scope.kind)
        entities = [
            e for e in candidates if _eval_predicate(scope.predicate, e)
        ]

    return SelectOutput(
        model=input.get("model", {}),
        spec=spec,
        entities=entities,
    )


def select_stage() -> Stage:
    """Construct the select stage."""
    return wrap_function("select", _run_select)
