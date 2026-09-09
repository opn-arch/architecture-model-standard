"""EntityPageProjector base class with kind dispatch (Phase 3 Task 7).

Rather than register ``family1.entity_page.component``,
``family1.entity_page.capability``, ... as separate projectors (14 kinds
* 7 families = 98 names), each family registers a single
``familyN.entity_page`` projector: an instance of a
:class:`EntityPageProjector` subclass that dispatches internally by the
scope entity's kind.

Scope info is injected into the projector config by
:func:`architecture_model.lifecycle.view_projection.project` from the
materialized slice's ``provenance['scope_metadata']`` for entity-scoped
slices. The two keys consumed here are:

* ``__scope_entity_id`` — the id from ``scope=entity(<id>)``.
* ``__scope_entity_kind`` — the singular canonical kind
  (``"component"``, ``"capability"``, ...).

Subclasses set ``family: int`` and implement ``_project_<kind>(model,
config) -> DiagramSpec`` for each supported kind. Unknown kinds raise
``NotImplementedError`` — the base does not silently degrade.

The concrete family renderers land in Tasks 8-14; this file only ships
the dispatch scaffolding + tests.
"""

from __future__ import annotations

from typing import Any

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import ArchitectureModel


class EntityPageProjector:
    """Callable base implementing the ``ProjectorFn`` contract.

    Subclasses set ``family`` and provide ``_project_<kind>`` methods.
    The instance itself is registered against the
    :class:`~architecture_model.lifecycle.view_projection.ProjectorRegistry`
    under the name ``familyN.entity_page``.
    """

    family: int = 0

    def __call__(
        self,
        model: ArchitectureModel,
        config: dict[str, Any],
    ) -> DiagramSpec:
        kind = str(config.get("__scope_entity_kind", "") or "").lower()
        method = getattr(self, f"_project_{kind}", None)
        if method is None:
            raise NotImplementedError(
                f"family{self.family}.entity_page has no rendering for kind={kind!r}"
            )
        return method(model, config)
