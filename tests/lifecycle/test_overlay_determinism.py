"""Phase 2 Task 23 — determinism guard for overlay application.

Two invariants:

1. **Byte identity under repetition.** For any fixed overlay order,
   ``apply_overlays`` must return byte-identical facets on repeated
   calls (given the same base view + materialized slice).

2. **Order sensitivity.** Overlays are applied in declared order and
   the ``applied_overlays`` list preserves that order. Reordering
   overlays produces a visibly different result.

We guard both by comparing the JSON-serialized facets of the projected
view, using ``json.dumps(sort_keys=True)`` on the facets dict. Sorting
keys eliminates dict-iteration flakiness while still catching real
ordering (list) differences inside overlays / applied_overlays.
"""
from __future__ import annotations

import json

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.types import ArchitectureModel, Entities, ModelMeta
from architecture_model.lifecycle.model_slice_materializer import MaterializedSlice
from architecture_model.lifecycle.overlays import apply_overlays
from architecture_model.lifecycle.supplementary_loaders import (
    DriftFragment,
    GatesFragment,
    SILEvent,
    SILFragment,
)
from architecture_model.lifecycle.view_projection import ProjectedView

import pytest


def _empty_model() -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(),
    )


def _make_view() -> ProjectedView:
    return ProjectedView(
        view_id="v1",
        slice_id="s1",
        model_revision="sha256-v1:abc",
        diagram_spec=DiagramSpec(id="diagram:t", title="t", facets={}),
        provenance={"projector": "test"},
    )


def _make_mslice() -> MaterializedSlice:
    sil = SILFragment(
        events=(
            SILEvent(
                component_id="COMP-1",
                ts="2026-01-01T00:00:00Z",
                kind="invoke",
                outcome="ok",
                duration_ms=1.0,
            ),
        ),
        summary={"COMP-1": {"invocations": 1, "failure_rate": 0.0, "avg_duration_ms": 1.0}},
    )
    drift = DriftFragment(
        events=(
            {"entity_id": "COMP-1", "kind": "orphan", "detail": "no files"},
            {"entity_id": "CAP-1", "kind": "unrealized_capability", "detail": "no realizer"},
        )
    )
    gates = GatesFragment(
        events=(
            {"gate_id": "gate:extract", "outcome": "pass", "timestamp": "2026-01-01T00:00:00Z"},
        )
    )
    return MaterializedSlice(
        slice_id="s1",
        architecture_id="arch",
        model_revision="sha256-v1:abc",
        model_fragment=_empty_model(),
        supplementary_fragments={"sil": sil, "drift": drift, "gates": gates},
    )


def _facets_json(view: ProjectedView) -> str:
    return json.dumps(view.diagram_spec.facets, sort_keys=True, default=str)


@pytest.mark.parametrize(
    "order",
    [
        ("sil",),
        ("drift",),
        ("gates",),
        ("sil", "drift"),
        ("sil", "drift", "gates"),
        ("gates", "drift", "sil"),
    ],
)
def test_byte_identical_under_repetition(order):
    """Repeated calls with the same order must yield byte-identical facets."""
    mslice = _make_mslice()
    a = apply_overlays(_make_view(), mslice, list(order))
    b = apply_overlays(_make_view(), mslice, list(order))
    assert _facets_json(a) == _facets_json(b)
    # And applied_overlays reflects order exactly.
    assert a.diagram_spec.facets["applied_overlays"] == list(order)


def test_order_recorded_in_applied_overlays():
    """(sil, drift) vs (drift, sil) → different applied_overlays lists."""
    mslice = _make_mslice()
    ab = apply_overlays(_make_view(), mslice, ["sil", "drift"])
    ba = apply_overlays(_make_view(), mslice, ["drift", "sil"])
    assert ab.diagram_spec.facets["applied_overlays"] == ["sil", "drift"]
    assert ba.diagram_spec.facets["applied_overlays"] == ["drift", "sil"]
    # And the two facets JSONs must differ (order-sensitive).
    assert _facets_json(ab) != _facets_json(ba)


def test_all_recognized_together_deterministic():
    """(sil, drift, gates) → three repeats yield identical facets."""
    mslice = _make_mslice()
    outs = [
        apply_overlays(_make_view(), mslice, ["sil", "drift", "gates"])
        for _ in range(3)
    ]
    ref = _facets_json(outs[0])
    for o in outs[1:]:
        assert _facets_json(o) == ref


def test_partial_overlays_do_not_leak_state():
    """Applying (sil,) then (drift,) to fresh views does not carry state."""
    mslice = _make_mslice()
    sil_only = apply_overlays(_make_view(), mslice, ["sil"])
    drift_only = apply_overlays(_make_view(), mslice, ["drift"])
    assert "sil" in sil_only.diagram_spec.facets["overlays"]
    assert "drift" not in sil_only.diagram_spec.facets["overlays"]
    assert "drift" in drift_only.diagram_spec.facets["overlays"]
    assert "sil" not in drift_only.diagram_spec.facets["overlays"]
