"""pipeline_v3.slice — v3-native slicer (T0.14 Phase 9).

Produces token-budgeted focused views over a v3 model dict. Two entry
points:

- :func:`slice_by_component` — target component + optional 1-hop
  neighborhood, with relationships filtered to edges wholly inside
  the retained set.
- :func:`slice_by_promise` — owner component narrowed to a single
  promise, with relationships dropped (promise-scoped views don't
  need the component graph).

Sizing concern was deliberately deferred from earlier phases (per
plan Phase 9 — "premature optimization would have distorted schema
decisions"). Now that the v3 shape is locked, slicing is a pure
dict → dict transform: deterministic, side-effect-free, safe for
downstream LLM prompts and doc projectors.

Both functions:

- Preserve ``meta.schema_version`` and other meta keys.
- Deep-copy the retained components (original model is never mutated).
- Add ``meta.sliced_from`` = original project name.
- Add ``meta.slice_spec`` = ``{"kind", "target"}`` provenance.
"""

from __future__ import annotations

import copy
from typing import Any

__all__ = ["SliceError", "slice_by_component", "slice_by_promise"]


class SliceError(KeyError):
    """Raised when a slice target is not present in the model."""


def _components(model: dict[str, Any]) -> list[dict[str, Any]]:
    return list(model.get("entities", {}).get("components", []))


def _all_entities_by_kind(model: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return {kind_plural: [entity_dict, ...]} across all entity kinds."""
    ents = model.get("entities", {})
    out: dict[str, list[dict[str, Any]]] = {}
    for kind, lst in ents.items():
        if isinstance(lst, list):
            out[kind] = list(lst)
    return out


def _id_to_kind(model: dict[str, Any]) -> dict[str, str]:
    """Map every entity id → kind_plural across all entity buckets."""
    out: dict[str, str] = {}
    for kind, lst in _all_entities_by_kind(model).items():
        for ent in lst:
            eid = ent.get("id")
            if eid:
                out[eid] = kind
    return out


def _relationships(model: dict[str, Any]) -> list[dict[str, Any]]:
    return list(model.get("relationships", []))


def _meta_with_slice(model: dict[str, Any], kind: str, target: str) -> dict[str, Any]:
    meta = dict(model.get("meta", {}))
    meta["sliced_from"] = meta.get("project", "unknown")
    meta["slice_spec"] = {"kind": kind, "target": target}
    return meta


def slice_by_component(
    model: dict[str, Any],
    component_id: str,
    *,
    include_neighbors: bool = True,
) -> dict[str, Any]:
    """Return a sub-model rooted at ``component_id``.

    Parameters
    ----------
    model:
        Full v3 model dict.
    component_id:
        Target component id (must exist).
    include_neighbors:
        When True (default), pulls in the 1-hop neighborhood: any entity
        (of any kind) at the other end of a ``relationships`` edge
        touching the target. This closes over cross-kind edges
        (``realizes`` → capability, ``exposes`` → interface,
        ``traces-to`` → behavior, ``constrained-by`` → constraint,
        ``contains`` → layer, etc.) so the resulting sub-model preserves
        the graph downstream walkers expect (L16). When False, returns
        only the target component.

    Raises
    ------
    SliceError
        If ``component_id`` is not present in the model.
    """
    comps = _components(model)
    by_id = {c["id"]: c for c in comps}
    if component_id not in by_id:
        raise SliceError(f"unknown component: {component_id}")

    id_to_kind = _id_to_kind(model)
    keep_ids: set[str] = {component_id}
    if include_neighbors:
        for rel in _relationships(model):
            f, t = rel.get("from"), rel.get("to")
            if f == component_id and t in id_to_kind:
                keep_ids.add(t)
            if t == component_id and f in id_to_kind:
                keep_ids.add(f)

    # Group retained entities by their original kind bucket. This preserves
    # cross-kind neighbors (capabilities, interfaces, behaviors, ...) so
    # walk-substrate consumers see the graph, not just an isolated
    # component list.
    kept_by_kind: dict[str, list[dict[str, Any]]] = {}
    for kind, lst in _all_entities_by_kind(model).items():
        for ent in lst:
            if ent.get("id") in keep_ids:
                kept_by_kind.setdefault(kind, []).append(copy.deepcopy(ent))
    # Deterministic order within each bucket.
    for kind in kept_by_kind:
        kept_by_kind[kind].sort(key=lambda e: e.get("id", ""))

    kept_rels = [
        copy.deepcopy(r)
        for r in _relationships(model)
        if r.get("from") in keep_ids and r.get("to") in keep_ids
    ]

    return {
        "meta": _meta_with_slice(model, "component", component_id),
        "entities": kept_by_kind,
        "relationships": kept_rels,
    }


def slice_by_promise(model: dict[str, Any], promise_id: str) -> dict[str, Any]:
    """Return the owner component narrowed to a single promise.

    Relationships are always dropped — promise-scoped views focus on
    the semantic content of one obligation, not the component graph.

    Raises
    ------
    SliceError
        If ``promise_id`` is not present in the model.
    """
    for comp in _components(model):
        for pr in comp.get("promises", []):
            if pr.get("id") == promise_id:
                narrowed = copy.deepcopy(comp)
                narrowed["promises"] = [copy.deepcopy(pr)]
                return {
                    "meta": _meta_with_slice(model, "promise", promise_id),
                    "entities": {"components": [narrowed]},
                    "relationships": [],
                }
    raise SliceError(f"unknown promise: {promise_id}")
