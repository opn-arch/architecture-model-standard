"""Tests for SI&L → Promise evidence binding (Phase 5 of T0.14).

Aggregation layer: SILRecord metrics/events become entries in
Promise.verified_by. Not a rewrite of sil/{record,rollup,decorators}.py.
"""

from __future__ import annotations

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.sil.record import Event, Metrics, SILRecord
from architecture_model.sil.evidence import (
    bind_evidence,
    bind_evidence_bulk,
    derive_evidence_refs,
)


def _p(attr, content, owner, **kw) -> Promise:
    return Promise(attribute=attr, content=content, owner_entity=owner, **kw)


def _record(component_id, **kw) -> SILRecord:
    metrics = kw.pop("metrics", Metrics())
    events = kw.pop("events", [])
    return SILRecord(
        component_id=component_id,
        kind=kw.pop("kind", "architecture-component"),
        name=kw.pop("name", component_id),
        metrics=metrics,
        events=events,
        **kw,
    )


# ---------------------------------------------------------------------------
# derive_evidence_refs
# ---------------------------------------------------------------------------

def test_derive_refs_empty_when_no_signal():
    rec = _record("COMP-1")
    assert derive_evidence_refs(rec) == ()


def test_derive_refs_emits_validation_score():
    rec = _record("COMP-1", metrics=Metrics(validation_score=87))
    refs = derive_evidence_refs(rec)
    assert any(r.startswith("SIL:COMP-1:validation=87") for r in refs)


def test_derive_refs_emits_healthy_signal_when_invoked_and_no_failures():
    rec = _record(
        "COMP-1",
        metrics=Metrics(invocations_7d=100, failure_rate_7d=0.0),
    )
    refs = derive_evidence_refs(rec)
    assert any(r.startswith("SIL:COMP-1:healthy") for r in refs)


def test_derive_refs_no_healthy_when_failures_present():
    rec = _record(
        "COMP-1",
        metrics=Metrics(invocations_7d=100, failure_rate_7d=0.05),
    )
    refs = derive_evidence_refs(rec)
    assert not any("healthy" in r for r in refs)


def test_derive_refs_emits_ok_event_ids():
    rec = _record(
        "COMP-1",
        events=[
            Event(kind="outcome", outcome="ok", event_id="EVT-1", ts="2026-09-14T00:00:00Z"),
            Event(kind="outcome", outcome="error", event_id="EVT-2", ts="2026-09-14T00:00:01Z"),
            Event(kind="invocation", event_id="EVT-3", ts="2026-09-14T00:00:02Z"),
        ],
    )
    refs = derive_evidence_refs(rec)
    ref_str = " ".join(refs)
    assert "EVT-1" in ref_str
    assert "EVT-2" not in ref_str  # error outcome doesn't count
    assert "EVT-3" not in ref_str  # non-outcome doesn't count


def test_derive_refs_deterministic_ordering():
    rec = _record(
        "COMP-1",
        metrics=Metrics(validation_score=87, invocations_7d=10, failure_rate_7d=0.0),
        events=[
            Event(kind="outcome", outcome="ok", event_id="EVT-2", ts="2026-09-14T00:00:02Z"),
            Event(kind="outcome", outcome="ok", event_id="EVT-1", ts="2026-09-14T00:00:01Z"),
        ],
    )
    refs_a = derive_evidence_refs(rec)
    refs_b = derive_evidence_refs(rec)
    assert refs_a == refs_b
    # Metric refs precede event refs (canonical order)
    assert refs_a.index("SIL:COMP-1:validation=87") < refs_a.index("SIL:COMP-1:event=EVT-1")


# ---------------------------------------------------------------------------
# bind_evidence (single promise)
# ---------------------------------------------------------------------------

def test_bind_evidence_appends_to_verified_by():
    p = _p("intent", "x", "COMP-1", provenance="T0.14")
    rec = _record("COMP-1", metrics=Metrics(validation_score=87))
    bound = bind_evidence(p, [rec])
    assert "SIL:COMP-1:validation=87" in bound.verified_by


def test_bind_evidence_preserves_existing_verified_by():
    p = _p("intent", "x", "COMP-1", verified_by=("VER-EXISTING",))
    rec = _record("COMP-1", metrics=Metrics(validation_score=87))
    bound = bind_evidence(p, [rec])
    assert "VER-EXISTING" in bound.verified_by
    assert "SIL:COMP-1:validation=87" in bound.verified_by


def test_bind_evidence_deduplicates():
    """Re-binding the same evidence should not create duplicates."""
    p = _p("intent", "x", "COMP-1")
    rec = _record("COMP-1", metrics=Metrics(validation_score=87))
    once = bind_evidence(p, [rec])
    twice = bind_evidence(once, [rec])
    assert twice.verified_by == once.verified_by


def test_bind_evidence_ignores_records_for_other_owners():
    p = _p("intent", "x", "COMP-1")
    rec = _record("COMP-2", metrics=Metrics(validation_score=87))
    bound = bind_evidence(p, [rec])
    assert bound.verified_by == ()


def test_bind_evidence_preserves_promise_identity():
    """Binding evidence must not change (attribute, content, owner) hash."""
    p = _p("intent", "x", "COMP-1")
    rec = _record("COMP-1", metrics=Metrics(validation_score=87))
    bound = bind_evidence(p, [rec])
    assert bound.id == p.id
    assert bound.attribute == p.attribute
    assert bound.content == p.content
    assert bound.owner_entity == p.owner_entity


def test_bind_evidence_no_op_when_no_matching_record():
    p = _p("intent", "x", "COMP-1", verified_by=("VER-1",))
    bound = bind_evidence(p, [])
    assert bound == p


def test_bind_evidence_typed_gap_promise_unchanged():
    """Evidence should not silently un-gap a TYPED_GAP promise."""
    p = _p("verification", "", "COMP-1", status=PromiseStatus.TYPED_GAP,
           gap_type="G-VERIFY")
    rec = _record("COMP-1", metrics=Metrics(validation_score=87))
    bound = bind_evidence(p, [rec])
    assert bound.status == PromiseStatus.TYPED_GAP
    # Evidence STILL attaches — a gap can be evidenced without being closed;
    # the gap is a design decision, not an absence of data.
    assert "SIL:COMP-1:validation=87" in bound.verified_by


# ---------------------------------------------------------------------------
# bind_evidence_bulk
# ---------------------------------------------------------------------------

def test_bind_evidence_bulk_processes_all_promises():
    p1 = _p("intent", "a", "COMP-1")
    p2 = _p("goals", ["g"], "COMP-2")
    r1 = _record("COMP-1", metrics=Metrics(validation_score=87))
    r2 = _record("COMP-2", metrics=Metrics(validation_score=42))
    bound = bind_evidence_bulk([p1, p2], [r1, r2])
    assert len(bound) == 2
    verified_by_owner = {b.owner_entity: b.verified_by for b in bound}
    assert "SIL:COMP-1:validation=87" in verified_by_owner["COMP-1"]
    assert "SIL:COMP-2:validation=42" in verified_by_owner["COMP-2"]


def test_bind_evidence_bulk_preserves_order():
    p1 = _p("intent", "a", "COMP-1")
    p2 = _p("intent", "b", "COMP-2")
    bound = bind_evidence_bulk([p1, p2], [])
    assert [b.owner_entity for b in bound] == ["COMP-1", "COMP-2"]


def test_bind_evidence_bulk_empty_records_is_no_op():
    ps = [_p("intent", "x", "COMP-1", verified_by=("VER-A",))]
    bound = bind_evidence_bulk(ps, [])
    assert bound == ps
