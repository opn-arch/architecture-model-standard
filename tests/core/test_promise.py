"""Tests for architecture_model.core.promise (Phase 1 of T0.14).

Promise dataclass per COMP-PB-PROMISE-TYPE spec (plan-b line 1655-1697):

    Promise(id, attribute, content, owner_entity, delivered_from,
            verified_by, status, gap_type, provenance)

- id: PR-<sha1[:12]> deterministic over canonical content
- attribute: str, name of semantic field (intent, goals, ...)
- content: str | list[str], the promised value
- owner_entity: str, entity ID that owns this Promise
- delivered_from: str | None, parent Promise ID
- verified_by: tuple[str, ...], verification IDs / evidence refs
- status: PromiseStatus enum
- gap_type: str | None, only when status=TYPED_GAP
- provenance: str, source of this Promise (turn ref / walk ref / plan ref)
"""

from __future__ import annotations

import json

import pytest

from architecture_model.core.promise import (
    Promise,
    PromiseStatus,
    compute_promise_id,
)


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------

def test_promise_deterministic_id():
    p1 = Promise(
        attribute="intent",
        content="Preserve user framing",
        owner_entity="CAP-DF-INTENT",
    )
    p2 = Promise(
        attribute="intent",
        content="Preserve user framing",
        owner_entity="CAP-DF-INTENT",
    )
    assert p1.id == p2.id
    assert p1.id.startswith("PR-")
    assert len(p1.id) == 3 + 12  # "PR-" + 12 hex chars


def test_promise_id_differs_by_attribute():
    p1 = Promise(attribute="intent", content="x", owner_entity="E1")
    p2 = Promise(attribute="goals", content="x", owner_entity="E1")
    assert p1.id != p2.id


def test_promise_id_differs_by_owner():
    p1 = Promise(attribute="intent", content="x", owner_entity="E1")
    p2 = Promise(attribute="intent", content="x", owner_entity="E2")
    assert p1.id != p2.id


def test_promise_id_differs_by_content():
    p1 = Promise(attribute="intent", content="a", owner_entity="E1")
    p2 = Promise(attribute="intent", content="b", owner_entity="E1")
    assert p1.id != p2.id


def test_promise_id_stable_for_list_content_ordering():
    # Lists in different orders MUST hash differently — ordering carries semantics
    p1 = Promise(attribute="goals", content=["a", "b"], owner_entity="E1")
    p2 = Promise(attribute="goals", content=["b", "a"], owner_entity="E1")
    assert p1.id != p2.id


def test_compute_promise_id_pure_function():
    # Direct helper can be called without constructing a Promise
    pid = compute_promise_id("intent", "x", "E1")
    assert pid.startswith("PR-")
    assert compute_promise_id("intent", "x", "E1") == pid


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

def test_promise_round_trip_minimal():
    p = Promise(
        attribute="intent",
        content="Preserve user framing",
        owner_entity="CAP-DF-INTENT",
    )
    d = p.to_dict()
    assert Promise.from_dict(d) == p


def test_promise_round_trip_full():
    p = Promise(
        attribute="goals",
        content=["a", "b", "c"],
        owner_entity="CAP-PB-MODEL",
        delivered_from="PR-abcdef123456",
        verified_by=("VER-1", "VER-2"),
        status=PromiseStatus.DELIVERED,
        gap_type=None,
        provenance="T0.14 plan doc",
    )
    d = p.to_dict()
    assert Promise.from_dict(d) == p


def test_promise_round_trip_typed_gap():
    p = Promise(
        attribute="verification",
        content="",
        owner_entity="COMP-1",
        status=PromiseStatus.TYPED_GAP,
        gap_type="G-VERIFY",
        provenance="WALK-2026-09-14-001",
    )
    d = p.to_dict()
    assert Promise.from_dict(d) == p


def test_promise_json_round_trip():
    p = Promise(
        attribute="intent",
        content="x",
        owner_entity="E1",
        status=PromiseStatus.OPEN,
    )
    j = json.dumps(p.to_dict())
    assert Promise.from_dict(json.loads(j)) == p


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------

def test_promise_default_status_is_open():
    p = Promise(attribute="intent", content="x", owner_entity="E1")
    assert p.status == PromiseStatus.OPEN


def test_promise_status_values():
    # Locked enum values per plan-b design + walk-instance #1 finding.
    # Extended 2026-09-20 with "proposed" for R7 LLM attribute inference.
    assert {s.value for s in PromiseStatus} == {
        "open", "delivered", "verified", "typed-gap", "proposed"
    }


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def test_promise_typed_gap_requires_gap_type():
    with pytest.raises(ValueError, match="gap_type"):
        Promise(
            attribute="intent",
            content="",
            owner_entity="E1",
            status=PromiseStatus.TYPED_GAP,
            gap_type=None,
        )


def test_promise_non_gap_forbids_gap_type():
    with pytest.raises(ValueError, match="gap_type"):
        Promise(
            attribute="intent",
            content="x",
            owner_entity="E1",
            status=PromiseStatus.OPEN,
            gap_type="G-DELIVERY",
        )


def test_promise_empty_owner_rejected():
    with pytest.raises(ValueError, match="owner_entity"):
        Promise(attribute="intent", content="x", owner_entity="")


def test_promise_empty_attribute_rejected():
    with pytest.raises(ValueError, match="attribute"):
        Promise(attribute="", content="x", owner_entity="E1")


def test_promise_verified_by_is_tuple():
    p = Promise(
        attribute="intent",
        content="x",
        owner_entity="E1",
        verified_by=["VER-1"],  # list at construction
    )
    assert p.verified_by == ("VER-1",)  # normalized to tuple
    assert isinstance(p.verified_by, tuple)


# ---------------------------------------------------------------------------
# from_dict resilience
# ---------------------------------------------------------------------------

def test_from_dict_omits_optional_fields():
    # No id supplied → recomputed. Optional fields omitted → defaults applied.
    d = {
        "attribute": "intent",
        "content": "x",
        "owner_entity": "E1",
        "status": "open",
    }
    p = Promise.from_dict(d)
    assert p.attribute == "intent"
    assert p.verified_by == ()
    assert p.delivered_from is None
    assert p.gap_type is None
    assert p.provenance == ""


def test_from_dict_rejects_unknown_status():
    with pytest.raises(ValueError):
        Promise.from_dict({
            "attribute": "intent",
            "content": "x",
            "owner_entity": "E1",
            "status": "unknown-state",
        })


def test_from_dict_accepts_missing_id_and_recomputes():
    # A dict without id gets id recomputed from canonical form
    d = {
        "attribute": "intent",
        "content": "x",
        "owner_entity": "E1",
        "status": "open",
    }
    p = Promise.from_dict(d)
    expected = compute_promise_id("intent", "x", "E1")
    assert p.id == expected


def test_from_dict_verifies_provided_id():
    # Providing a wrong id explicitly should raise (integrity check)
    d = {
        "id": "PR-deadbeef1234",
        "attribute": "intent",
        "content": "x",
        "owner_entity": "E1",
        "status": "open",
    }
    with pytest.raises(ValueError, match="id"):
        Promise.from_dict(d)


# ---------------------------------------------------------------------------
# to_dict shape
# ---------------------------------------------------------------------------

def test_to_dict_contains_all_fields():
    p = Promise(
        attribute="intent",
        content="x",
        owner_entity="E1",
        provenance="T0.14",
    )
    d = p.to_dict()
    for key in (
        "id", "attribute", "content", "owner_entity",
        "delivered_from", "verified_by", "status",
        "gap_type", "provenance",
    ):
        assert key in d, f"missing key: {key}"


def test_to_dict_status_serialized_as_string():
    p = Promise(
        attribute="intent",
        content="x",
        owner_entity="E1",
        status=PromiseStatus.DELIVERED,
    )
    assert p.to_dict()["status"] == "delivered"
