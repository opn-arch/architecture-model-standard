"""pipeline_v3.adapters.legacy_pipeline — v3→2.x model converter (T0.14 Phase 11).

Adapter that converts a v3 model dict (Promise-graph shape) into a
2.x :class:`~architecture_model.core.types.ArchitectureModel` dataclass
so surviving legacy consumers (visualize, docs) can be invoked from
v3 call sites without duplicating their logic.

Per Plan B' Phase 11: adapters are the LAST phase because the v3 shape
had to stabilize first. Building adapters before Phase 6/7 would have
locked in v3-shape decisions prematurely.

Mapping (v3 → 2.x)
------------------

- ``meta.project``, ``meta.generated_at`` → ``ModelMeta`` (schema_version
  stamped as ``2.2`` — the latest 2.x — so legacy validators accept it).
- Each v3 component becomes a 2.x :class:`Component` with:
    - ``id``, ``name`` copied verbatim
    - ``files`` populated from ``module_names`` (dotted → path/py)
    - ``responsibilities`` populated from ``delivers``-attribute Promises
    - ``kind`` defaulted to :class:`ComponentKind.SERVICE`
- Each v3 relationship (``depends-on`` only in Phase 6/7 output) becomes
  a :class:`Relationship` with :class:`RelationType.DEPENDS_ON`.

Only the fields legacy consumers actually read are populated. Everything
else uses dataclass defaults. Input dict is never mutated.
"""

from __future__ import annotations

import copy
from typing import Any

from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    ComponentKind,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)

__all__ = ["v3_to_legacy_model"]


def _module_to_file(dotted: str) -> str:
    """Convert dotted module name to a rel-path with ``.py`` suffix."""
    return dotted.replace(".", "/") + ".py"


def _v3_components_to_2x(v3_comps: list[dict[str, Any]]) -> list[Component]:
    out: list[Component] = []
    for c in v3_comps:
        delivers: list[str] = []
        for pr in c.get("promises", []) or []:
            if pr.get("attribute") == "delivers":
                delivers.extend(pr.get("content", []) or [])
        files = [_module_to_file(m) for m in c.get("module_names", []) or []]
        out.append(
            Component(
                id=c["id"],
                name=c.get("name", c["id"]),
                status=Status.ACTIVE,
                kind=ComponentKind.SERVICE,
                files=files,
                responsibilities=sorted(set(delivers)),
            )
        )
    return out


def _v3_rels_to_2x(v3_rels: list[dict[str, Any]]) -> list[Relationship]:
    out: list[Relationship] = []
    for r in v3_rels:
        # Accept both on-wire (`from`/`to`/`type`, per publish.py) and
        # internal (`from_cluster`/`to_cluster`/`kind`, per containerize)
        # relationship shapes so the adapter is safe against either.
        src = r.get("from", r.get("from_cluster"))
        dst = r.get("to", r.get("to_cluster"))
        kind = r.get("type", r.get("kind", "depends-on"))
        if src is None or dst is None:
            continue
        try:
            rtype = RelationType(kind)
        except ValueError:
            rtype = RelationType.DEPENDS_ON
        out.append(Relationship(type=rtype, from_id=src, to_id=dst))
    return out


def v3_to_legacy_model(v3_model: dict[str, Any]) -> ArchitectureModel:
    """Convert a v3 model dict to a 2.x :class:`ArchitectureModel`.

    The input dict is deep-copied on read so the source is never
    mutated. The returned model carries ``schema_version="2.2"`` so
    downstream 2.x validators / renderers accept it as current-gen.
    """
    src = copy.deepcopy(v3_model)
    meta_src = src.get("meta", {})
    meta = ModelMeta(
        schema_version="2.2",
        project=meta_src.get("project", ""),
        generated_at=meta_src.get("generated_at", ""),
    )
    comps = _v3_components_to_2x(src.get("entities", {}).get("components", []))
    rels = _v3_rels_to_2x(src.get("relationships", []))
    return ArchitectureModel(
        meta=meta,
        entities=Entities(components=comps),
        relationships=rels,
    )
