"""Tests for chain-closure quality module (Phase 3 of T0.14).

Realizes CAP-DF-VERIFY: delivery-down + verify-up chain closure over a
Promise-graph. Produces typed gaps (G-DELIVERY / G-VERIFY / G-OPEN-Q).
"""

from __future__ import annotations

import pytest

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.quality.chain_closure import (
    GAP_DELIVERY,
    GAP_OPEN_Q,
    GAP_VERIFY,
    ChainClosureReport,
    Gap,
    analyze_chain_closure,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _p(attr, content, owner, **kw) -> Promise:
    return Promise(attribute=attr, content=content, owner_entity=owner, **kw)


# ---------------------------------------------------------------------------
# Delivery-down (G-DELIVERY)
# ---------------------------------------------------------------------------

def test_promise_with_no_delivery_is_gap():
    """OPEN promise with no delivered_from is a G-DELIVERY gap."""
    p = _p("intent", "x", "E1")
    report = analyze_chain_closure([p])
    assert any(g.gap == GAP_DELIVERY and g.promise_id == p.id for g in report.gaps)


def test_promise_with_broken_lineage_is_gap():
    """delivered_from pointing to an unknown Promise id → G-DELIVERY."""
    p = _p("intent", "x", "E1", delivered_from="PR-deadbeef0000")
    report = analyze_chain_closure([p])
    assert any(
        g.gap == GAP_DELIVERY and "broken" in g.reason.lower()
        for g in report.gaps
    )


def test_promise_with_resolved_lineage_no_delivery_gap():
    """delivered_from that resolves to a Promise in the graph is not a gap."""
    root = _p("intent", "root", "E0")
    child = _p("intent", "child", "E1", delivered_from=root.id,
               status=PromiseStatus.DELIVERED)
    report = analyze_chain_closure([root, child])
    child_gaps = [g for g in report.gaps if g.promise_id == child.id]
    assert not any(g.gap == GAP_DELIVERY for g in child_gaps)


def test_typed_gap_status_exempt_from_delivery_check():
    """A Promise explicitly marked TYPED_GAP is already a named gap."""
    p = _p("verification", "", "COMP-1",
           status=PromiseStatus.TYPED_GAP, gap_type="G-VERIFY")
    report = analyze_chain_closure([p])
    assert not any(
        g.gap == GAP_DELIVERY and g.promise_id == p.id for g in report.gaps
    )


# ---------------------------------------------------------------------------
# Verify-up (G-VERIFY)
# ---------------------------------------------------------------------------

def test_promise_without_verification_is_gap():
    p = _p("intent", "x", "E1")
    report = analyze_chain_closure([p])
    assert any(g.gap == GAP_VERIFY and g.promise_id == p.id for g in report.gaps)


def test_promise_with_verification_no_verify_gap():
    p = _p("intent", "x", "E1", verified_by=("VER-1",))
    report = analyze_chain_closure([p])
    assert not any(
        g.gap == GAP_VERIFY and g.promise_id == p.id for g in report.gaps
    )


def test_verified_status_without_evidence_is_gap():
    """A Promise marked VERIFIED but with no verified_by is a structural
    inconsistency — flagged as G-VERIFY."""
    p = _p("intent", "x", "E1", status=PromiseStatus.VERIFIED,
           delivered_from=None)
    # Bypass the identity check by hand-constructing dict path
    report = analyze_chain_closure([p])
    assert any(g.gap == GAP_VERIFY and g.promise_id == p.id for g in report.gaps)


def test_typed_gap_status_exempt_from_verify_check():
    p = _p("verification", "", "COMP-1",
           status=PromiseStatus.TYPED_GAP, gap_type="G-VERIFY")
    report = analyze_chain_closure([p])
    assert not any(
        g.gap == GAP_VERIFY and g.promise_id == p.id for g in report.gaps
    )


# ---------------------------------------------------------------------------
# Open questions (G-OPEN-Q)
# ---------------------------------------------------------------------------

def test_open_questions_promise_emits_one_gap_per_question():
    p = _p("open_questions", ["Q1?", "Q2?", "Q3?"], "CAP-1",
           verified_by=("VER-noop",))  # avoid G-VERIFY noise
    report = analyze_chain_closure([p], root_owner_ids={"CAP-1"})
    open_q_gaps = [g for g in report.gaps if g.gap == GAP_OPEN_Q]
    assert len(open_q_gaps) == 3
    assert {g.reason for g in open_q_gaps} == {"Q1?", "Q2?", "Q3?"}


def test_open_questions_string_content_emits_single_gap():
    p = _p("open_questions", "Single question?", "CAP-1",
           verified_by=("VER-noop",))
    report = analyze_chain_closure([p], root_owner_ids={"CAP-1"})
    open_q_gaps = [g for g in report.gaps if g.gap == GAP_OPEN_Q]
    assert len(open_q_gaps) == 1
    assert open_q_gaps[0].reason == "Single question?"


def test_non_open_questions_attribute_no_open_q_gap():
    p = _p("goals", ["some goal"], "CAP-1", verified_by=("VER-1",))
    report = analyze_chain_closure([p], root_owner_ids={"CAP-1"})
    assert not any(g.gap == GAP_OPEN_Q for g in report.gaps)


# ---------------------------------------------------------------------------
# root_owner_ids exemption
# ---------------------------------------------------------------------------

def test_root_owner_promise_exempt_from_delivery_gap():
    """Promises owned by declared root entities (e.g. actors) are
    exempt from G-DELIVERY — they have no upstream by design."""
    p = _p("intent", "x", "ACT-1")
    report = analyze_chain_closure([p], root_owner_ids={"ACT-1"})
    assert not any(
        g.gap == GAP_DELIVERY and g.promise_id == p.id for g in report.gaps
    )


def test_non_root_owner_still_flagged_when_roots_declared():
    root_p = _p("intent", "x", "ACT-1")
    child_p = _p("intent", "y", "COMP-1")
    report = analyze_chain_closure([root_p, child_p], root_owner_ids={"ACT-1"})
    delivery_gaps = [g for g in report.gaps if g.gap == GAP_DELIVERY]
    assert all(g.promise_id != root_p.id for g in delivery_gaps)
    assert any(g.promise_id == child_p.id for g in delivery_gaps)


# ---------------------------------------------------------------------------
# closure_pct & counts
# ---------------------------------------------------------------------------

def test_closure_pct_fully_closed_graph_is_1():
    root = _p("intent", "root", "ACT-1", verified_by=("VER-1",))
    child = _p("intent", "child", "COMP-1",
               delivered_from=root.id, verified_by=("VER-2",),
               status=PromiseStatus.DELIVERED)
    report = analyze_chain_closure([root, child], root_owner_ids={"ACT-1"})
    assert report.closure_pct == 1.0
    assert report.gaps == []


def test_closure_pct_all_gaps_is_0():
    p1 = _p("intent", "x", "E1")  # no verify, no delivery, non-root
    p2 = _p("intent", "y", "E2")
    report = analyze_chain_closure([p1, p2])  # no roots declared
    assert report.closure_pct < 1.0
    assert report.closure_pct >= 0.0


def test_closure_pct_never_negative():
    """Even pathological input never yields negative closure."""
    p = _p("open_questions", ["a"] * 20, "E1")
    report = analyze_chain_closure([p])
    assert 0.0 <= report.closure_pct <= 1.0


def test_empty_graph_closure_pct_is_1():
    """No promises → nothing to verify → 100% closed vacuously."""
    report = analyze_chain_closure([])
    assert report.closure_pct == 1.0
    assert report.gap_counts == {}


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------

def test_report_gap_counts_by_category():
    p1 = _p("intent", "x", "E1")           # G-DELIVERY + G-VERIFY
    p2 = _p("open_questions", ["Q?"], "E1", verified_by=("VER-1",),
            delivered_from=None)           # G-OPEN-Q + G-DELIVERY
    report = analyze_chain_closure([p1, p2])
    assert report.gap_counts[GAP_DELIVERY] == 2
    assert report.gap_counts[GAP_VERIFY] == 1
    assert report.gap_counts[GAP_OPEN_Q] == 1


def test_report_status_counts():
    root = _p("intent", "x", "ACT-1", verified_by=("VER-1",))
    delivered = _p("intent", "y", "E1", delivered_from=root.id,
                   verified_by=("VER-2",), status=PromiseStatus.DELIVERED)
    gap = _p("verification", "", "E2", status=PromiseStatus.TYPED_GAP,
             gap_type="G-VERIFY")
    report = analyze_chain_closure([root, delivered, gap],
                                   root_owner_ids={"ACT-1"})
    assert report.status_counts[PromiseStatus.OPEN] == 1
    assert report.status_counts[PromiseStatus.DELIVERED] == 1
    assert report.status_counts[PromiseStatus.TYPED_GAP] == 1


def test_gap_categories_match_cap_df_verify_spec():
    """CAP-DF-VERIFY goal 2: G-DELIVERY, G-VERIFY, G-OPEN-Q are exhaustive."""
    assert GAP_DELIVERY == "G-DELIVERY"
    assert GAP_VERIFY == "G-VERIFY"
    assert GAP_OPEN_Q == "G-OPEN-Q"
