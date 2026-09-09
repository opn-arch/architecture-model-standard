"""Overlay-aware projector helper (Phase 2 Task 14).

An *overlay* is a named supplementary decoration folded onto a
:class:`~architecture_model.lifecycle.view_projection.ProjectedView` in
declared order. Overlays let a single projector emit a base diagram (from
the architecture model alone) and then be augmented with runtime signals
(SI&L rollups, drift flags, gate outcomes) sourced from the
:class:`~architecture_model.lifecycle.model_slice_materializer.MaterializedSlice`
supplementary fragments.

Design contract
---------------
* Order-preserving: overlays are applied in the exact order declared on
  :attr:`ViewCuration.overlays`. Later overlays may see facets written by
  earlier ones but MUST NOT clobber unrelated keys.
* Silent skip for unknown names: this keeps the pipeline deterministic
  when overlays are declared but not yet implemented (Task 15-17 land the
  gates/drift/test_results backing journals).
* Silent skip for missing fragments: if a fragment is ``None`` or absent
  from ``supplementary_fragments`` the overlay is a no-op.
* Purity: returns a NEW :class:`ProjectedView`; the input view is not
  mutated. The wrapped :class:`DiagramSpec`'s ``facets`` dict is
  copied and augmented; ``nodes`` / ``edges`` / other structural fields
  are shared by reference (safe — DiagramSpec is treated as immutable at
  this layer).

Facet layout
------------
All overlay output is written under the reserved facet key
``"overlays"`` as a mapping ``{overlay_name: overlay_payload}``. This
keeps overlays namespaced away from projector-native facet keys and
makes the applied overlay set trivially inspectable.

Additionally, the ordered list of *applied* overlay names (recognized
overlays whose fragment was available) is written to
``facets["applied_overlays"]``. Declared-but-unrecognized or
declared-but-empty overlays are NOT listed there.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.lifecycle.model_slice_materializer import MaterializedSlice
from architecture_model.lifecycle.supplementary_loaders import (
    DriftFragment,
    GatesFragment,
    SILFragment,
)
from architecture_model.lifecycle.view_projection import ProjectedView


RECOGNIZED_OVERLAYS: tuple[str, ...] = ("sil", "drift", "gates")


def _overlay_sil(fragment: SILFragment) -> dict[str, Any] | None:
    """Build the ``sil`` overlay payload from an :class:`SILFragment`.

    Payload shape::

        {"per_component": {component_id: {invocations, failures, avg_duration_ms}}}

    Returns ``None`` if the fragment carries no summary rows (nothing to
    show).
    """
    if not fragment.summary:
        return None
    return {"per_component": dict(fragment.summary)}


def _overlay_drift(fragment: DriftFragment) -> dict[str, Any] | None:
    """Build the ``drift`` overlay payload from a :class:`DriftFragment`.

    Groups drift events by ``entity_id`` when present. Events lacking an
    ``entity_id`` land in an ``"_unattributed"`` bucket so nothing is
    silently dropped.

    Returns ``None`` if the fragment carries no events.
    """
    if not fragment.events:
        return None
    per_entity: dict[str, list[dict[str, Any]]] = {}
    for ev in fragment.events:
        eid = ev.get("entity_id") if isinstance(ev, dict) else None
        key = eid if isinstance(eid, str) and eid else "_unattributed"
        per_entity.setdefault(key, []).append(dict(ev) if isinstance(ev, dict) else {"raw": ev})
    return {"per_entity": per_entity}


def _overlay_gates(fragment: GatesFragment) -> dict[str, Any] | None:
    """Build the ``gates`` overlay payload from a :class:`GatesFragment`.

    Returns the *last* recorded gate event (append-only journal semantics
    from Task 15 mean ``events[-1]`` is the freshest outcome).

    Returns ``None`` if the fragment is empty.
    """
    if not fragment.events:
        return None
    last = fragment.events[-1]
    payload: dict[str, Any] = {"last": dict(last) if isinstance(last, dict) else {"raw": last}}
    return payload


# Dispatch table: overlay_name -> (fragment_type, builder). Kept as a
# module-level constant so tests can inspect / monkeypatch.
_OVERLAY_BUILDERS: dict[str, tuple[type, Any]] = {
    "sil": (SILFragment, _overlay_sil),
    "drift": (DriftFragment, _overlay_drift),
    "gates": (GatesFragment, _overlay_gates),
}


def apply_overlays(
    base_view: ProjectedView,
    mslice: MaterializedSlice,
    declared: Sequence[str],
) -> ProjectedView:
    """Fold recognized overlays into ``base_view.diagram_spec`` in declared order.

    Recognized overlay names: ``"sil"``, ``"drift"``, ``"gates"``.
    Unknown names are silently ignored (deterministic — see module docstring).

    Parameters
    ----------
    base_view:
        The :class:`ProjectedView` produced by
        :func:`architecture_model.lifecycle.view_projection.project`.
    mslice:
        The materialized slice whose ``supplementary_fragments`` are the
        source of overlay data.
    declared:
        Overlay names to apply, in order. Typically
        ``view_spec.curation.overlays``.

    Returns
    -------
    ProjectedView
        A NEW view with an augmented :class:`DiagramSpec`. If ``declared``
        is empty or nothing was applied, the returned view is
        structurally identical to ``base_view`` (new dataclass instance,
        same field values).
    """
    if not declared:
        return base_view

    fragments = mslice.supplementary_fragments or {}
    overlays_payload: dict[str, Any] = {}
    applied: list[str] = []

    for name in declared:
        entry = _OVERLAY_BUILDERS.get(name)
        if entry is None:
            # Unknown overlay — silently skip.
            continue
        fragment_type, builder = entry
        frag = fragments.get(name)
        if frag is None or not isinstance(frag, fragment_type):
            # Missing / wrong-typed fragment — silently skip.
            continue
        payload = builder(frag)
        if payload is None:
            # Fragment present but empty — nothing to fold in.
            continue
        overlays_payload[name] = payload
        applied.append(name)

    # Build the augmented DiagramSpec. Copy facets so the input spec is
    # untouched; share other fields by reference.
    src_spec = base_view.diagram_spec
    new_facets = dict(src_spec.facets)
    if overlays_payload:
        # Merge into an existing "overlays" facet if present (respect any
        # projector that pre-populated the slot); declared-order wins on
        # key conflicts.
        existing = new_facets.get("overlays")
        merged: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
        merged.update(overlays_payload)
        new_facets["overlays"] = merged
        new_facets["applied_overlays"] = list(applied)

    new_spec = replace(src_spec, facets=new_facets)
    return ProjectedView(
        view_id=base_view.view_id,
        slice_id=base_view.slice_id,
        model_revision=base_view.model_revision,
        diagram_spec=new_spec,
        provenance=base_view.provenance,
        warnings=base_view.warnings,
    )


__all__ = ["apply_overlays", "RECOGNIZED_OVERLAYS"]
