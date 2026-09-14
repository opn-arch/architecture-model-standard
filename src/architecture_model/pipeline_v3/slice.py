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
        When True (default), pulls in components at the other end of
        any ``relationships`` edge touching the target (both inbound
        and outbound). When False, returns only the target.

    Raises
    ------
    SliceError
        If ``component_id`` is not present in the model.
    """
    comps = _components(model)
    by_id = {c["id"]: c for c in comps}
    if component_id not in by_id:
        raise SliceError(f"unknown component: {component_id}")

    keep_ids: set[str] = {component_id}
    if include_neighbors:
        for rel in _relationships(model):
            f, t = rel.get("from"), rel.get("to")
            if f == component_id and t in by_id:
                keep_ids.add(t)
            if t == component_id and f in by_id:
                keep_ids.add(f)

    kept_comps = [copy.deepcopy(by_id[i]) for i in sorted(keep_ids)]
    kept_rels = [
        copy.deepcopy(r)
        for r in _relationships(model)
        if r.get("from") in keep_ids and r.get("to") in keep_ids
    ]

    return {
        "meta": _meta_with_slice(model, "component", component_id),
        "entities": {"components": kept_comps},
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
