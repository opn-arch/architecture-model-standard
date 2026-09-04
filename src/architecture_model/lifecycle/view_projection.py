"""ViewSpec projector registry and pure projection (T16).

Purpose
-------
This module turns a :class:`~architecture_model.lifecycle.view_spec.ViewSpec`
plus a matching :class:`~architecture_model.lifecycle.model_slice_materializer.MaterializedSlice`
into a :class:`ProjectedView` carrying a
:class:`~architecture_model.core.diagram_spec.DiagramSpec`.

A **projector** is a pure callable ``(model_fragment, projector_config) ->
DiagramSpec``. Projectors are registered by name in a
:class:`ProjectorRegistry`; the module-level :data:`DEFAULT_REGISTRY` is
seeded with adapters for the four canonical Systems-Engineering views
(``se.conops``, ``se.functional``, ``se.logical``, ``se.use_cases``) that
delegate to :mod:`architecture_model.core.se_view_projectors` without
modifying it.

Contract for projector implementations
--------------------------------------
* MUST be a pure function of ``(model_fragment, projector_config)``. It
  MUST NOT read the filesystem, network, environment variables, or any
  model outside the provided fragment. This is a documented contract; it
  is not (and cannot be) enforced by the runtime.
* MUST return a :class:`DiagramSpec` instance. Any other return value
  causes :func:`project` to raise :class:`TypeError`.
* SHOULD be deterministic: given equal ``(model_fragment,
  projector_config)`` it MUST produce equal DiagramSpecs.

Invariants
----------
* :func:`project` verifies that
  ``view.slice_ref.slice_id == materialized_slice.slice_id`` and
  ``view.slice_ref.model_revision == materialized_slice.model_revision``
  before invoking the projector. Mismatches raise :class:`SliceMismatch`,
  enforcing the "ViewSpec bound to immutable slice revision" invariant
  established by T15.
* :func:`project` passes a shallow copy of ``view.projector_config`` to
  the projector so any mutation performed inside the projector cannot
  leak back into the frozen ViewSpec.
* The ``provenance`` dict on the returned :class:`ProjectedView` records
  ``projector``, ``projector_version``, ``produced_at`` (RFC3339 UTC with
  ``Z`` suffix), and ``slice_digest`` (currently the materialized
  slice's ``model_revision``). Everything except ``produced_at`` is
  deterministic across repeated calls.
* Warnings from the :class:`MaterializedSlice` are surfaced as strings of
  the form ``"<code>: <message>"`` on ``ProjectedView.warnings`` so
  downstream renderers can present them without importing lifecycle
  types.

Thread safety
-------------
:class:`ProjectorRegistry` mutations (``register``/``unregister``) are
NOT thread-safe in this phase. The intended usage is: seed
:data:`DEFAULT_REGISTRY` at import time (single-threaded) and treat it
as read-only afterwards. :func:`project` itself is a pure function and
safe for concurrent use once the registry is quiescent.

Error taxonomy
--------------
* :class:`ProjectorNotFound` (subclass of :class:`KeyError`) — unknown
  projector name in :func:`ProjectorRegistry.get` or :func:`project`.
* :class:`SliceMismatch` (subclass of :class:`ValueError`) — the ViewSpec
  references a slice_id / model_revision that does not match the
  materialized slice supplied to :func:`project`.
* :class:`TypeError` — the registered projector returned a value that is
  not a :class:`DiagramSpec`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import ArchitectureModel
from architecture_model.lifecycle.model_slice_materializer import MaterializedSlice
from architecture_model.lifecycle.view_spec import ViewSpec


ProjectorFn = Callable[[ArchitectureModel, dict[str, Any]], DiagramSpec]


class ProjectorNotFound(KeyError):
    """Raised when a projector name is not registered."""


class SliceMismatch(ValueError):
    """Raised when ViewSpec.slice_ref does not match the materialized slice."""


@dataclass(frozen=True)
class ProjectedView:
    """A DiagramSpec produced by a projector, bound to its slice revision."""

    view_id: str
    slice_id: str
    model_revision: str
    diagram_spec: DiagramSpec
    provenance: dict[str, Any]
    warnings: tuple[str, ...] = ()


class ProjectorRegistry:
    """Name-indexed registry of projector callables with version tags.

    Not thread-safe for mutation; see module docstring.
    """

    def __init__(self) -> None:
        self._entries: dict[str, tuple[ProjectorFn, str]] = {}

    def register(self, name: str, fn: ProjectorFn, *, version: str = "1.0.0") -> None:
        if not name:
            raise ValueError("projector name must be non-empty")
        self._entries[name] = (fn, version)

    def unregister(self, name: str) -> None:
        self._entries.pop(name, None)

    def get(self, name: str) -> tuple[ProjectorFn, str]:
        try:
            return self._entries[name]
        except KeyError as exc:
            raise ProjectorNotFound(name) from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))

    def __contains__(self, name: object) -> bool:
        return name in self._entries


def _rfc3339_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def project(
    view: ViewSpec,
    materialized_slice: MaterializedSlice,
    *,
    registry: ProjectorRegistry | None = None,
) -> ProjectedView:
    """Project ``view`` over ``materialized_slice`` via the named projector.

    Raises
    ------
    ProjectorNotFound
        If ``view.projector`` is not registered.
    SliceMismatch
        If ``view.slice_ref`` disagrees with the materialized slice.
    TypeError
        If the projector returns a value that is not a
        :class:`DiagramSpec`.
    """
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if view.slice_ref.slice_id != materialized_slice.slice_id:
        raise SliceMismatch(
            f"ViewSpec {view.id!r} slice_id {view.slice_ref.slice_id!r} does not "
            f"match materialized slice_id {materialized_slice.slice_id!r}"
        )
    if view.slice_ref.model_revision != materialized_slice.model_revision:
        raise SliceMismatch(
            f"ViewSpec {view.id!r} model_revision {view.slice_ref.model_revision!r} "
            f"does not match materialized model_revision "
            f"{materialized_slice.model_revision!r}"
        )
    fn, version = reg.get(view.projector)
    config_copy = dict(view.projector_config)
    result = fn(materialized_slice.model_fragment, config_copy)
    if not isinstance(result, DiagramSpec):
        raise TypeError(
            f"projector {view.projector!r} returned {type(result).__name__}, "
            f"expected DiagramSpec"
        )
    provenance = {
        "projector": view.projector,
        "projector_version": version,
        "produced_at": _rfc3339_now(),
        "slice_digest": materialized_slice.model_revision,
    }
    warnings = tuple(
        f"{w.code}: {w.message}" for w in materialized_slice.warnings
    )
    return ProjectedView(
        view_id=view.id,
        slice_id=materialized_slice.slice_id,
        model_revision=materialized_slice.model_revision,
        diagram_spec=result,
        provenance=provenance,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# DEFAULT_REGISTRY — seeded with adapters for the four SE projectors.
#
# The existing projectors in ``architecture_model.core.se_view_projectors``
# accept ``(ArchitectureViewContext, ViewCuration | None, *, max_overview_nodes)``.
# We bridge by constructing a minimal ``ArchitectureViewContext`` from the
# provided model fragment — no filesystem, no hierarchy load. ``config``
# may carry ``max_overview_nodes``; other curation is left at defaults for
# phase 1. If the fragment lacks entities required for a rich view the
# projector returns a minimal DiagramSpec — that's acceptable per spec.
# ---------------------------------------------------------------------------


def _adapt_se(project_fn: Callable[..., DiagramSpec]) -> ProjectorFn:
    from architecture_model.core.view_context import ArchitectureViewContext

    def adapter(fragment: ArchitectureModel, config: dict[str, Any]) -> DiagramSpec:
        # Minimal in-memory context: single-namespace, no filesystem.
        context = ArchitectureViewContext(Path("/"), {"root": fragment}, [])
        kwargs: dict[str, Any] = {}
        if "max_overview_nodes" in config:
            try:
                kwargs["max_overview_nodes"] = int(config["max_overview_nodes"])
            except (TypeError, ValueError):
                pass
        return project_fn(context, **kwargs)

    return adapter


DEFAULT_REGISTRY: ProjectorRegistry = ProjectorRegistry()


def _seed_default_registry() -> None:
    from architecture_model.core.se_view_projectors import (
        project_conops,
        project_functional_architecture,
        project_logical_architecture,
        project_use_cases,
    )

    DEFAULT_REGISTRY.register("se.conops", _adapt_se(project_conops), version="1.0.0")
    DEFAULT_REGISTRY.register(
        "se.functional", _adapt_se(project_functional_architecture), version="1.0.0"
    )
    DEFAULT_REGISTRY.register(
        "se.logical", _adapt_se(project_logical_architecture), version="1.0.0"
    )
    DEFAULT_REGISTRY.register(
        "se.use_cases", _adapt_se(project_use_cases), version="1.0.0"
    )


_seed_default_registry()


__all__ = [
    "ProjectedView",
    "ProjectorFn",
    "ProjectorNotFound",
    "ProjectorRegistry",
    "SliceMismatch",
    "DEFAULT_REGISTRY",
    "project",
]
