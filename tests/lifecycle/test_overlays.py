"""Tests for :mod:`architecture_model.lifecycle.overlays` (Phase 2 Task 14)."""
from __future__ import annotations

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.types import ArchitectureModel, Entities, ModelMeta
from architecture_model.lifecycle.overlays import (
    RECOGNIZED_OVERLAYS,
    apply_overlays,
)
from architecture_model.lifecycle.model_slice_materializer import MaterializedSlice
from architecture_model.lifecycle.supplementary_loaders import (
    DriftFragment,
    GatesFragment,
    SILEvent,
    SILFragment,
)
from architecture_model.lifecycle.view_projection import ProjectedView


def _empty_model() -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(project="t", schema_version="2.1"),
        entities=Entities(),
    )


def _make_view(**facet_extras) -> ProjectedView:
    spec = DiagramSpec(id="diagram:t", title="t", facets=dict(facet_extras))
    return ProjectedView(
        view_id="v1",
        slice_id="s1",
        model_revision="sha256-v1:abc",
        diagram_spec=spec,
        provenance={"projector": "test"},
    )


def _make_mslice(**supplementary) -> MaterializedSlice:
    return MaterializedSlice(
        slice_id="s1",
        architecture_id="arch",
        model_revision="sha256-v1:abc",
        model_fragment=_empty_model(),
        supplementary_fragments=dict(supplementary),
    )


# ---------------------------------------------------------------------------
# Basic behavior
# ---------------------------------------------------------------------------


def test_empty_declared_returns_base_view_unchanged():
    base = _make_view()
    mslice = _make_mslice()
    out = apply_overlays(base, mslice, [])
    assert out is base


def test_unknown_overlay_silently_ignored():
    base = _make_view()
    mslice = _make_mslice()
    out = apply_overlays(base, mslice, ["not-a-real-overlay"])
    # No overlays applied -> no overlays facet key added.
    assert "overlays" not in out.diagram_spec.facets
    assert "applied_overlays" not in out.diagram_spec.facets


def test_recognized_names_frozen():
    assert RECOGNIZED_OVERLAYS == ("sil", "drift", "gates")


def test_missing_fragment_skips_overlay():
    base = _make_view()
    mslice = _make_mslice()  # no fragments at all
    out = apply_overlays(base, mslice, ["sil", "drift", "gates"])
    assert "overlays" not in out.diagram_spec.facets


def test_empty_fragment_skips_overlay():
    """Fragment present but carrying no rows -> no-op (no empty facet)."""
    base = _make_view()
    mslice = _make_mslice(
        sil=SILFragment(events=(), summary={}),
        drift=DriftFragment(events=()),
        gates=GatesFragment(events=()),
    )
    out = apply_overlays(base, mslice, ["sil", "drift", "gates"])
    assert "overlays" not in out.diagram_spec.facets


# ---------------------------------------------------------------------------
# Purity
# ---------------------------------------------------------------------------


def test_input_view_not_mutated():
    base = _make_view(existing="keep-me")
    mslice = _make_mslice(
        sil=SILFragment(summary={"COMP-1": {"invocations": 3.0}})
    )
    out = apply_overlays(base, mslice, ["sil"])
    # Base facets untouched.
    assert base.diagram_spec.facets == {"existing": "keep-me"}
    # Output is a new view.
    assert out is not base
    assert out.diagram_spec is not base.diagram_spec


def test_projector_native_facets_preserved():
    base = _make_view(content_kind="mermaid", body="graph TD")
    mslice = _make_mslice(sil=SILFragment(summary={"COMP-1": {"invocations": 1.0}}))
    out = apply_overlays(base, mslice, ["sil"])
    assert out.diagram_spec.facets["content_kind"] == "mermaid"
    assert out.diagram_spec.facets["body"] == "graph TD"
    assert "overlays" in out.diagram_spec.facets


# ---------------------------------------------------------------------------
# SIL overlay
# ---------------------------------------------------------------------------


def test_sil_overlay_payload_shape():
    base = _make_view()
    summary = {
        "COMP-1": {"invocations": 5.0, "failures": 1.0, "avg_duration_ms": 12.5},
        "COMP-2": {"invocations": 2.0, "failures": 0.0, "avg_duration_ms": 3.0},
    }
    mslice = _make_mslice(sil=SILFragment(events=(), summary=summary))
    out = apply_overlays(base, mslice, ["sil"])
    ov = out.diagram_spec.facets["overlays"]["sil"]
    assert ov == {"per_component": summary}
    assert out.diagram_spec.facets["applied_overlays"] == ["sil"]


# ---------------------------------------------------------------------------
# Drift overlay
# ---------------------------------------------------------------------------


def test_drift_overlay_groups_by_entity_id():
    ev1 = {"entity_id": "COMP-1", "kind": "orphan", "detail": "no realizer"}
    ev2 = {"entity_id": "COMP-1", "kind": "broken_ref", "detail": "dangling"}
    ev3 = {"entity_id": "COMP-2", "kind": "missing_impl", "detail": "no code"}
    base = _make_view()
    mslice = _make_mslice(drift=DriftFragment(events=(ev1, ev2, ev3)))
    out = apply_overlays(base, mslice, ["drift"])
    per_entity = out.diagram_spec.facets["overlays"]["drift"]["per_entity"]
    assert set(per_entity.keys()) == {"COMP-1", "COMP-2"}
    assert len(per_entity["COMP-1"]) == 2
    assert per_entity["COMP-2"][0]["kind"] == "missing_impl"


def test_drift_overlay_unattributed_bucket():
    ev = {"kind": "orphan", "detail": "no owner"}
    base = _make_view()
    mslice = _make_mslice(drift=DriftFragment(events=(ev,)))
    out = apply_overlays(base, mslice, ["drift"])
    per_entity = out.diagram_spec.facets["overlays"]["drift"]["per_entity"]
    assert "_unattributed" in per_entity


# ---------------------------------------------------------------------------
# Gates overlay
# ---------------------------------------------------------------------------


def test_gates_overlay_reports_last_event():
    older = {"gate_id": "g1", "outcome": "pass", "timestamp": "t0"}
    newer = {"gate_id": "g2", "outcome": "fail", "timestamp": "t1"}
    base = _make_view()
    mslice = _make_mslice(gates=GatesFragment(events=(older, newer)))
    out = apply_overlays(base, mslice, ["gates"])
    assert out.diagram_spec.facets["overlays"]["gates"]["last"] == newer


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_applied_overlays_reflect_declared_order():
    base = _make_view()
    mslice = _make_mslice(
        sil=SILFragment(summary={"COMP-1": {"invocations": 1.0}}),
        gates=GatesFragment(events=({"outcome": "pass"},)),
    )
    out = apply_overlays(base, mslice, ["gates", "sil"])
    assert out.diagram_spec.facets["applied_overlays"] == ["gates", "sil"]


def test_declared_order_reversed_yields_different_applied_order():
    base = _make_view()
    mslice = _make_mslice(
        sil=SILFragment(summary={"COMP-1": {"invocations": 1.0}}),
        gates=GatesFragment(events=({"outcome": "pass"},)),
    )
    a = apply_overlays(base, mslice, ["sil", "gates"])
    b = apply_overlays(base, mslice, ["gates", "sil"])
    assert a.diagram_spec.facets["applied_overlays"] == ["sil", "gates"]
    assert b.diagram_spec.facets["applied_overlays"] == ["gates", "sil"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_missing_and_present_overlays_mixed():
    base = _make_view()
    mslice = _make_mslice(sil=SILFragment(summary={"COMP-1": {"invocations": 2.0}}))
    # 'drift' declared but no fragment -> skipped; 'sil' applied; unknown 'zzz' skipped.
    out = apply_overlays(base, mslice, ["drift", "sil", "zzz"])
    assert out.diagram_spec.facets["applied_overlays"] == ["sil"]
    assert set(out.diagram_spec.facets["overlays"].keys()) == {"sil"}


def test_wrong_typed_fragment_ignored():
    """If a caller injects the wrong type under the name, silently skip."""
    base = _make_view()
    mslice = _make_mslice(sil={"not": "a SILFragment"})  # bogus
    out = apply_overlays(base, mslice, ["sil"])
    assert "overlays" not in out.diagram_spec.facets


def test_preexisting_overlays_facet_merged():
    """If projector already wrote facets['overlays'], merge rather than clobber."""
    base = _make_view(overlays={"custom": {"note": "preexisting"}})
    mslice = _make_mslice(sil=SILFragment(summary={"COMP-1": {"invocations": 1.0}}))
    out = apply_overlays(base, mslice, ["sil"])
    merged = out.diagram_spec.facets["overlays"]
    assert "custom" in merged
    assert "sil" in merged
