"""Drill-down link emission for root-family projectors (Phase 3 Task 16).

Every root-family view (``family3.component_diagram``,
``family6.icd``, etc.) lists a subset of the model's entities in its
rendered body. This module supplies a ``drill_to`` map — a dict of
``{entity_id: "familyN.entity_page:entity_id"}`` — that root-family
adapters attach to their :class:`DiagramSpec` facets. Renderers may
later use these to emit hyperlinks or hover targets. The map has no
visual effect on the rendered body itself.

Coverage per family mirrors the ``EntityPageProjector`` dispatch
matrix in ``entity_pages.py``:

* family1 — actor, capability, behavior, interface, constraint, layer, component
* family2 — capability, component, behavior
* family3 — component, layer
* family4 — behavior, actor
* family6 — interface, component
* family7 — component, capability, behavior, interface, constraint
* family8 — component, capability, interface
"""

from __future__ import annotations

from typing import Any

# Family → tuple of entity-collection attribute names on ArchitectureModel.entities
_FAMILY_KINDS: dict[int, tuple[str, ...]] = {
    1: ("actors", "capabilities", "behaviors", "interfaces", "constraints", "layers", "components"),
    2: ("capabilities", "components", "behaviors"),
    3: ("components", "layers"),
    4: ("behaviors", "actors"),
    6: ("interfaces", "components"),
    7: ("components", "capabilities", "behaviors", "interfaces", "constraints"),
    8: ("components", "capabilities", "interfaces"),
}


def drill_to_map(fragment: Any, family: int) -> dict[str, str]:
    """Return {entity_id: 'familyN.entity_page:entity_id'} for entities in the fragment.

    Ids are collected in canonical fragment order across the kinds
    supported by ``family``. Duplicates are dropped (first-seen wins).
    Empty result when the family has no coverage or the fragment has no
    matching entities.
    """
    kinds = _FAMILY_KINDS.get(family, ())
    if not kinds:
        return {}
    entities = getattr(fragment, "entities", None)
    if entities is None:
        return {}
    out: dict[str, str] = {}
    prefix = f"family{family}.entity_page:"
    for kind in kinds:
        for ent in getattr(entities, kind, ()) or ():
            eid = getattr(ent, "id", None)
            if not eid or eid in out:
                continue
            out[eid] = prefix + eid
    return out


__all__ = ["drill_to_map"]
