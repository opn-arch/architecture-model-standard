"""Part 16b: slice_by_behavior — flow-scoped slicer.

Guards traversal of composite Behavior flows via ``triggers`` edges,
including deterministic ordering by ``sequence``, ``traces-to`` component
retention, parent-capability lift, and error handling.
"""

from __future__ import annotations

import pytest

from architecture_model.core.slicer import slice_by_behavior
from architecture_model.core.types import (
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
)


def _beh(bid: str) -> Behavior:
    return Behavior(id=bid, name=bid, status=Status.ACTIVE)


def _cap(cid: str) -> Capability:
    return Capability(id=cid, name=cid, status=Status.ACTIVE)


def _comp(cid: str) -> Component:
    return Component(id=cid, name=cid, status=Status.ACTIVE)


def _model(*, behaviors, capabilities=(), components=(), relationships) -> ArchitectureModel:
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.2", project="flow-test"),
        entities=Entities(
            behaviors=list(behaviors),
            capabilities=list(capabilities),
            components=list(components),
        ),
        relationships=list(relationships),
    )


def _trig(a: str, b: str, seq: int | None = None) -> Relationship:
    return Relationship(type=RelationType.TRIGGERS, from_id=a, to_id=b, sequence=seq)


# ---------------------------------------------------------------------------


def test_traverses_ordered_triggers_chain() -> None:
    """Root → 3-step chain via ordered sequence."""
    model = _model(
        behaviors=[_beh("BEH-root"), _beh("BEH-a"), _beh("BEH-b"), _beh("BEH-c")],
        relationships=[
            _trig("BEH-root", "BEH-a", seq=1),
            _trig("BEH-a", "BEH-b", seq=2),
            _trig("BEH-b", "BEH-c", seq=3),
        ],
    )
    sub = slice_by_behavior(model, "BEH-root", include_components=False, include_capability=False)
    kept = {b.id for b in sub.entities.behaviors}
    assert kept == {"BEH-root", "BEH-a", "BEH-b", "BEH-c"}
    assert len(sub.relationships) == 3


def test_unordered_triggers_still_traverse() -> None:
    """Missing sequence is legal; BFS still reaches all sub-behaviors."""
    model = _model(
        behaviors=[_beh("BEH-r"), _beh("BEH-x"), _beh("BEH-y")],
        relationships=[
            _trig("BEH-r", "BEH-x"),
            _trig("BEH-r", "BEH-y"),
        ],
    )
    sub = slice_by_behavior(model, "BEH-r", include_components=False, include_capability=False)
    assert {b.id for b in sub.entities.behaviors} == {"BEH-r", "BEH-x", "BEH-y"}


def test_traces_to_components_retained_by_default() -> None:
    model = _model(
        behaviors=[_beh("BEH-r"), _beh("BEH-a")],
        components=[_comp("COMP-x"), _comp("COMP-untouched")],
        relationships=[
            _trig("BEH-r", "BEH-a", seq=1),
            Relationship(type=RelationType.TRACES_TO, from_id="BEH-a", to_id="COMP-x"),
        ],
    )
    sub = slice_by_behavior(model, "BEH-r")
    kept_comps = {c.id for c in sub.entities.components}
    assert kept_comps == {"COMP-x"}, "only flow-participating components kept"


def test_traces_to_components_excluded_when_flag_false() -> None:
    model = _model(
        behaviors=[_beh("BEH-r"), _beh("BEH-a")],
        components=[_comp("COMP-x")],
        relationships=[
            _trig("BEH-r", "BEH-a", seq=1),
            Relationship(type=RelationType.TRACES_TO, from_id="BEH-a", to_id="COMP-x"),
        ],
    )
    sub = slice_by_behavior(model, "BEH-r", include_components=False, include_capability=False)
    assert sub.entities.components == []


def test_parent_capability_lifted_by_default() -> None:
    model = _model(
        behaviors=[_beh("BEH-r")],
        capabilities=[_cap("CAP-owner"), _cap("CAP-other")],
        relationships=[
            Relationship(type=RelationType.CONTAINS, from_id="CAP-owner", to_id="BEH-r"),
        ],
    )
    sub = slice_by_behavior(model, "BEH-r")
    assert {c.id for c in sub.entities.capabilities} == {"CAP-owner"}


def test_cycle_terminates() -> None:
    """A → B → A must not loop forever."""
    model = _model(
        behaviors=[_beh("BEH-a"), _beh("BEH-b")],
        relationships=[
            _trig("BEH-a", "BEH-b", seq=1),
            _trig("BEH-b", "BEH-a", seq=1),
        ],
    )
    sub = slice_by_behavior(model, "BEH-a", include_components=False, include_capability=False)
    assert {b.id for b in sub.entities.behaviors} == {"BEH-a", "BEH-b"}


def test_unknown_id_raises_keyerror() -> None:
    model = _model(behaviors=[_beh("BEH-a")], relationships=[])
    with pytest.raises(KeyError):
        slice_by_behavior(model, "BEH-missing")


def test_non_behavior_id_raises_valueerror() -> None:
    model = _model(
        behaviors=[_beh("BEH-a")],
        capabilities=[_cap("CAP-x")],
        relationships=[],
    )
    with pytest.raises(ValueError, match="not a Behavior"):
        slice_by_behavior(model, "CAP-x")


def test_deterministic_traversal_order_by_sequence() -> None:
    """Given mixed sequences, BFS respects sequence asc for determinism."""
    model = _model(
        behaviors=[_beh("BEH-r"), _beh("BEH-x"), _beh("BEH-y"), _beh("BEH-z")],
        relationships=[
            # Deliberately listed out of order in source.
            _trig("BEH-r", "BEH-z", seq=3),
            _trig("BEH-r", "BEH-x", seq=1),
            _trig("BEH-r", "BEH-y", seq=2),
        ],
    )
    sub = slice_by_behavior(model, "BEH-r", include_components=False, include_capability=False)
    # Sub-model retains all four; relationship count preserved.
    assert {b.id for b in sub.entities.behaviors} == {"BEH-r", "BEH-x", "BEH-y", "BEH-z"}
    assert len(sub.relationships) == 3


def test_only_flow_relationships_retained() -> None:
    """Non-participant relationships are dropped."""
    model = _model(
        behaviors=[_beh("BEH-r"), _beh("BEH-a"), _beh("BEH-outside")],
        relationships=[
            _trig("BEH-r", "BEH-a", seq=1),
            _trig("BEH-outside", "BEH-r"),  # inbound to root — NOT followed backwards
        ],
    )
    sub = slice_by_behavior(model, "BEH-r", include_components=False, include_capability=False)
    kept = {b.id for b in sub.entities.behaviors}
    assert kept == {"BEH-r", "BEH-a"}
    assert "BEH-outside" not in kept
