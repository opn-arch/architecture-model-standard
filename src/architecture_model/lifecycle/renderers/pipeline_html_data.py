"""Build the JSON payload consumed by the pipeline-dashboard HTML shell.

The output shape is intentionally simple and JSON-serializable so it can be
embedded directly into an interactive HTML view:

    {
      "nodes":  [{"id", "name", "kind", ...}, ...],
      "edges":  [{"from", "to", "type"}, ...],
      "badges": {node_id: {validation_score?, invocations_7d?, ...}, ...},
    }

The SIL store is duck-typed: any object exposing
``rollup(component_id) -> dict | None`` is accepted. Passing ``None``
yields an empty badges dict — the AMS builder has no dependency on OCA.
"""

from __future__ import annotations

from typing import Any, Protocol


class _SILProtocol(Protocol):
    def rollup(self, component_id: str) -> dict | None: ...


# (attribute on Entities, short kind label for the node payload)
_ENTITY_KINDS: tuple[tuple[str, str], ...] = (
    ("capabilities", "capability"),
    ("components", "component"),
    ("constraints", "constraint"),
    ("actors", "actor"),
    ("behaviors", "behavior"),
    ("interfaces", "interface"),
    ("layers", "layer"),
    ("systems", "system"),
    ("data", "data"),
    ("events", "event"),
    ("resources", "resource"),
    ("environments", "environment"),
    ("quality_attributes", "quality_attribute"),
    ("decisions", "decision"),
    ("lifecycles", "lifecycle"),
    ("requirements", "requirement"),
    ("external_systems", "external_system"),
)


def _rel_type(rel: Any) -> str:
    t = rel.type
    return getattr(t, "value", t) if t is not None else ""


def build(materialized_slice: Any, sil_store: _SILProtocol | None = None) -> dict:
    """Convert a ``MaterializedSlice`` into a nodes/edges/badges dict."""
    frag = materialized_slice.model_fragment
    entities = frag.entities

    nodes: list[dict] = []
    for attr, kind_label in _ENTITY_KINDS:
        for ent in getattr(entities, attr, ()) or ():
            nodes.append(
                {
                    "id": ent.id,
                    "name": getattr(ent, "name", "") or "",
                    "kind": kind_label,
                }
            )

    edges: list[dict] = [
        {"from": r.from_id, "to": r.to_id, "type": _rel_type(r)}
        for r in frag.relationships
    ]

    badges: dict[str, dict] = {}
    if sil_store is not None:
        for n in nodes:
            r = sil_store.rollup(n["id"])
            if r:
                badges[n["id"]] = dict(r)

    return {"nodes": nodes, "edges": edges, "badges": badges}


__all__ = ["build"]
