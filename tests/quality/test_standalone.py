"""Tests for standalone per-entity quality metrics (Phase 4 of T0.14).

Standalone metrics scored per-entity WITHOUT running chain-closure:

- completeness_pct: fraction of canonical semantic fields represented by a Promise
- provenance_integrity_pct: fraction of Promises with a non-empty provenance
- typed_gap_pct: fraction of Promises with status=TYPED_GAP (named absences)
- relationship_density: count of relationships touching the entity (in|out)

overall_score aggregates the four into a 0..100 rubric feeding INV-DF-REGEN.
"""

from __future__ import annotations

import pytest

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.migration.v2_to_v3 import SEMANTIC_FIELDS
from architecture_model.quality.standalone import (
    StandaloneScore,
    score_entity,
    score_model,
)


def _p(attr, content, owner, **kw) -> Promise:
    return Promise(attribute=attr, content=content, owner_entity=owner, **kw)


# ---------------------------------------------------------------------------
# completeness_pct
# ---------------------------------------------------------------------------

def test_completeness_zero_with_no_promises():
    s = score_entity("E1", [])
    assert s.completeness_pct == 0.0


def test_completeness_full_when_all_fields_have_promises():
    ps = [
        _p(attr, "x" if isinstance(attr, str) else ["x"], "E1",
           provenance="T0.14")
        for attr in SEMANTIC_FIELDS
    ]
    s = score_entity("E1", ps)
    assert s.completeness_pct == 1.0


def test_completeness_partial():
    ps = [_p("intent", "x", "E1"), _p("goals", ["a"], "E1")]
    s = score_entity("E1", ps)
    assert s.completeness_pct == pytest.approx(2 / len(SEMANTIC_FIELDS))


def test_completeness_ignores_promises_for_other_owners():
    """Only Promises owned by entity_id count toward its completeness."""
    ps = [
        _p("intent", "x", "E1"),
        _p("intent", "x", "E2"),
        _p("goals", ["a"], "E2"),
    ]
    s = score_entity("E1", ps)
    assert s.completeness_pct == pytest.approx(1 / len(SEMANTIC_FIELDS))


def test_completeness_duplicate_attribute_counted_once():
    """Two Promises for the same attribute shouldn't inflate the score."""
    ps = [_p("intent", "a", "E1"), _p("intent", "b", "E1")]
    s = score_entity("E1", ps)
    assert s.completeness_pct == pytest.approx(1 / len(SEMANTIC_FIELDS))


# ---------------------------------------------------------------------------
# provenance_integrity_pct
# ---------------------------------------------------------------------------

def test_provenance_integrity_all_stamped():
    ps = [
        _p("intent", "x", "E1", provenance="T0.14"),
        _p("goals", ["a"], "E1", provenance="T0.14"),
    ]
    s = score_entity("E1", ps)
    assert s.provenance_integrity_pct == 1.0


def test_provenance_integrity_none_stamped():
    ps = [_p("intent", "x", "E1"), _p("goals", ["a"], "E1")]
    s = score_entity("E1", ps)
    assert s.provenance_integrity_pct == 0.0


def test_provenance_integrity_mixed():
    ps = [
        _p("intent", "x", "E1", provenance="T0.14"),
        _p("goals", ["a"], "E1"),
    ]
    s = score_entity("E1", ps)
    assert s.provenance_integrity_pct == 0.5


def test_provenance_integrity_vacuous_when_no_promises():
    """No promises → nothing UN-stamped → vacuously 1.0."""
    s = score_entity("E1", [])
    assert s.provenance_integrity_pct == 1.0


# ---------------------------------------------------------------------------
# typed_gap_pct
# ---------------------------------------------------------------------------

def test_typed_gap_pct_zero_with_no_gaps():
    ps = [_p("intent", "x", "E1")]
    s = score_entity("E1", ps)
    assert s.typed_gap_pct == 0.0


def test_typed_gap_pct_all_gaps():
    ps = [
        _p("intent", "", "E1", status=PromiseStatus.TYPED_GAP,
           gap_type="G-DELIVERY"),
        _p("goals", "", "E1", status=PromiseStatus.TYPED_GAP,
           gap_type="G-DELIVERY"),
    ]
    s = score_entity("E1", ps)
    assert s.typed_gap_pct == 1.0


def test_typed_gap_pct_mixed():
    ps = [
        _p("intent", "x", "E1"),
        _p("verification", "", "E1", status=PromiseStatus.TYPED_GAP,
           gap_type="G-VERIFY"),
    ]
    s = score_entity("E1", ps)
    assert s.typed_gap_pct == 0.5


# ---------------------------------------------------------------------------
# relationship_density
# ---------------------------------------------------------------------------

def test_relationship_density_zero_without_relationships_arg():
    s = score_entity("E1", [_p("intent", "x", "E1")])
    assert s.relationship_density == 0


def test_relationship_density_counts_outbound():
    rels = [{"from": "E1", "to": "E2", "type": "depends-on"}]
    s = score_entity("E1", [], relationships=rels)
    assert s.relationship_density == 1


def test_relationship_density_counts_inbound():
    rels = [{"from": "E2", "to": "E1", "type": "realizes"}]
    s = score_entity("E1", [], relationships=rels)
    assert s.relationship_density == 1


def test_relationship_density_ignores_unrelated():
    rels = [
        {"from": "E2", "to": "E3", "type": "depends-on"},
        {"from": "E1", "to": "E2", "type": "depends-on"},
    ]
    s = score_entity("E1", [], relationships=rels)
    assert s.relationship_density == 1


def test_relationship_density_counts_self_loop_once():
    rels = [{"from": "E1", "to": "E1", "type": "realizes"}]
    s = score_entity("E1", [], relationships=rels)
    assert s.relationship_density == 1


# ---------------------------------------------------------------------------
# overall_score
# ---------------------------------------------------------------------------

def test_overall_score_bounded_0_100():
    s = score_entity("E1", [])
    assert 0 <= s.overall_score <= 100


def test_overall_score_is_100_when_fully_populated_and_stamped():
    ps = [
        _p(attr, "x", "E1", provenance="T0.14", verified_by=("V",))
        for attr in SEMANTIC_FIELDS
    ]
    rels = [{"from": "E1", "to": f"E{i}", "type": "depends-on"} for i in range(2, 12)]
    s = score_entity("E1", ps, relationships=rels)
    # completeness 1.0 + provenance 1.0 + relationship_density normalizes to 1.0
    # typed_gap_pct = 0 → not penalized OR rewarded, treated as neutral
    assert s.overall_score == 100


def test_overall_score_minimal_when_nothing_populated():
    s = score_entity("E1", [])
    # completeness 0 + no promises to score provenance/typed_gap on
    # + no relationships
    assert s.overall_score < 50


# ---------------------------------------------------------------------------
# Model-level rollup
# ---------------------------------------------------------------------------

def test_score_model_returns_per_entity_scores():
    ps = [_p("intent", "x", "E1", provenance="T0.14"),
          _p("intent", "y", "E2")]
    result = score_model(["E1", "E2"], ps)
    assert set(result.keys()) == {"E1", "E2"}
    assert isinstance(result["E1"], StandaloneScore)


def test_score_model_isolates_owners():
    ps = [_p("intent", "x", "E1", provenance="T0.14")]
    result = score_model(["E1", "E2"], ps)
    assert result["E1"].completeness_pct > 0
    assert result["E2"].completeness_pct == 0
