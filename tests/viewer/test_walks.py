"""Harness for the walk + diagnostic helpers in scripts/build_v3_viewer.py.

The build script is not an importable package, so we load it via
``importlib.util.spec_from_file_location``. Fixtures are the smallest
graphs that exercise each helper's happy path and its skip path.

Shape contracts (see CONTEXT.md 'Discoveries' section):
    entities_by_kind: {kind_plural: {eid: ent_dict}}
    relationships:    list[{from, to, type, note?}]
    out_edges/in_edges: {eid: [(neighbor, rel_type), ...]}  (typed, not deduped)
    entity_records:   {kind_plural: [{id, kind, name, by_attr, ...}]}
    by_attr:          {attr_name: [{id, content, status, ...}]}
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO / "scripts" / "build_v3_viewer.py"


def _load_build_module():
    """Load scripts/build_v3_viewer.py as an importable module object."""
    spec = importlib.util.spec_from_file_location("build_v3_viewer", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bv():
    """Loaded build_v3_viewer module."""
    return _load_build_module()


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------

def _empty_kinds() -> dict:
    return {
        "components": {},
        "capabilities": {},
        "behaviors": {},
        "interfaces": {},
        "actors": {},
        "constraints": {},
        "layers": {},
    }


def _make_fixture():
    """Return (entities_by_kind, relationships, out_edges, in_edges, entity_records).

    Graph shape:

        LAY-1 --contains--> COMP-x --realizes--> CAP-P --contains--> CAP-C
                             |                   |                    |
                             +--exposes--> IF-i  +--contains--> BEH-a,BEH-b
                             +--contains--> COMP-y                  |
                             +--constrained-by--> CONS-1            |
                                                                    CAP-C --contains--> BEH-c
        ACT-1 --triggers--> BEH-a --triggers--> BEH-b --triggers--> BEH-c
        COMP-y --traces-to--> BEH-b
    """
    E = _empty_kinds()
    E["layers"]["LAY-1"] = {"id": "LAY-1", "name": "Layer1"}
    E["components"]["COMP-x"] = {"id": "COMP-x", "name": "CompX"}
    E["components"]["COMP-y"] = {"id": "COMP-y", "name": "CompY"}
    E["capabilities"]["CAP-P"] = {"id": "CAP-P", "name": "ParentCap"}
    E["capabilities"]["CAP-C"] = {"id": "CAP-C", "name": "ChildCap"}
    E["behaviors"]["BEH-a"] = {"id": "BEH-a", "name": "BehA"}
    E["behaviors"]["BEH-b"] = {"id": "BEH-b", "name": "BehB"}
    E["behaviors"]["BEH-c"] = {"id": "BEH-c", "name": "BehC"}
    E["interfaces"]["IF-i"] = {"id": "IF-i", "name": "IfaceI"}
    E["actors"]["ACT-1"] = {"id": "ACT-1", "name": "Actor1"}
    E["constraints"]["CONS-1"] = {"id": "CONS-1", "name": "Cons1"}

    R = [
        {"from": "LAY-1", "to": "COMP-x", "type": "contains"},
        {"from": "COMP-x", "to": "CAP-P", "type": "realizes"},
        {"from": "COMP-x", "to": "COMP-y", "type": "contains"},
        {"from": "COMP-x", "to": "IF-i", "type": "exposes"},
        {"from": "COMP-x", "to": "CONS-1", "type": "constrained-by"},
        {"from": "CAP-P", "to": "CAP-C", "type": "contains"},
        {"from": "CAP-P", "to": "BEH-a", "type": "contains"},
        {"from": "CAP-P", "to": "BEH-b", "type": "contains"},
        {"from": "CAP-C", "to": "BEH-c", "type": "contains"},
        {"from": "ACT-1", "to": "BEH-a", "type": "triggers"},
        {"from": "BEH-a", "to": "BEH-b", "type": "triggers"},
        {"from": "BEH-b", "to": "BEH-c", "type": "triggers"},
        {"from": "COMP-y", "to": "BEH-b", "type": "traces-to"},
    ]

    out_edges: dict = {}
    in_edges: dict = {}
    for r in R:
        out_edges.setdefault(r["from"], []).append((r["to"], r["type"]))
        in_edges.setdefault(r["to"], []).append((r["from"], r["type"]))

    # Minimal entity_records for compliance-gap walker.
    def _rec(eid, kind, name, verified_attrs=()):
        by_attr = {}
        for attr in verified_attrs:
            by_attr[attr] = [{"id": f"{eid}-p1", "content": "x",
                              "status": "verified"}]
        return {"id": eid, "kind": kind, "name": name, "by_attr": by_attr}

    entity_records = {
        "layers": [_rec("LAY-1", "layer", "Layer1")],
        "components": [
            _rec("COMP-x", "component", "CompX"),         # no evidence
            _rec("COMP-y", "component", "CompY",
                 verified_attrs=("verification",)),        # has evidence
        ],
        "capabilities": [
            _rec("CAP-P", "capability", "ParentCap"),
            _rec("CAP-C", "capability", "ChildCap"),
        ],
        "behaviors": [
            _rec("BEH-a", "behavior", "BehA"),
            _rec("BEH-b", "behavior", "BehB"),
            _rec("BEH-c", "behavior", "BehC"),
        ],
        "interfaces": [_rec("IF-i", "interface", "IfaceI")],
        "actors": [_rec("ACT-1", "actor", "Actor1")],
        "constraints": [_rec("CONS-1", "constraint", "Cons1")],
    }

    return E, R, out_edges, in_edges, entity_records


# ---------------------------------------------------------------------------
# _mermaid_pipeline
# ---------------------------------------------------------------------------

def test_pipeline_renders_for_parent_cap(bv):
    E, R, *_ = _make_fixture()
    result = bv._mermaid_pipeline(E, R, cap_id="CAP-P")
    assert result is not None
    body, refs = result
    assert body.startswith("flowchart LR")
    # Entry beh triggered by actor.
    assert "BEH-a" in body
    assert "BEH-b" in body
    assert "ACT-1" in body
    # Actor is a referenced entity in refs.
    assert "ACT-1" in refs


def test_pipeline_returns_none_for_leaf_cap(bv):
    """CAP-C contains only BEH-c; no internal triggers between contained behs."""
    E, R, *_ = _make_fixture()
    assert bv._mermaid_pipeline(E, R, cap_id="CAP-C") is None


def test_pipeline_returns_none_for_unknown_cap(bv):
    E, R, *_ = _make_fixture()
    assert bv._mermaid_pipeline(E, R, cap_id="CAP-NOPE") is None


# ---------------------------------------------------------------------------
# _mermaid_decomposition
# ---------------------------------------------------------------------------

def test_decomposition_renders_for_parent_cap(bv):
    E, R, *_ = _make_fixture()
    result = bv._mermaid_decomposition(E, R, "CAP-P")
    assert result is not None
    body, visited = result
    assert body.startswith("flowchart TD")
    # Depth-1: CAP-C, BEH-a, BEH-b are direct children.
    assert "CAP-C" in visited
    assert "BEH-a" in visited
    assert "BEH-b" in visited
    # Depth-2: BEH-c is contained by CAP-C.
    assert "BEH-c" in visited


def test_decomposition_returns_none_for_leaf(bv):
    E, R, *_ = _make_fixture()
    # BEH-a has no outbound contains edges.
    assert bv._mermaid_decomposition(E, R, "BEH-a") is None


def test_decomposition_returns_none_for_unknown_id(bv):
    E, R, *_ = _make_fixture()
    assert bv._mermaid_decomposition(E, R, "NOPE-1") is None


# ---------------------------------------------------------------------------
# _mermaid_neighbors
# ---------------------------------------------------------------------------

def test_neighbors_renders_typed_edges(bv):
    E, R, oe, ie, _ = _make_fixture()
    result = bv._mermaid_neighbors(E, R, "BEH-b", oe, ie)
    assert result is not None
    body, refs = result
    assert body.startswith("flowchart LR")
    # BEH-b has: outbound triggers->BEH-c; inbound contains<-CAP-P,
    # traces-to<-COMP-y, triggers<-BEH-a.
    assert "BEH-c" in refs
    assert "BEH-a" in refs
    assert "COMP-y" in refs
    assert "CAP-P" in refs
    # Typed edge labels should appear in the body.
    assert "triggers" in body
    assert "traces-to" in body


def test_neighbors_skips_zero(bv):
    """Isolated node → total 1-hop neighbors == 0 → None."""
    E = _empty_kinds()
    E["components"]["COMP-lonely"] = {"id": "COMP-lonely", "name": "Lonely"}
    assert bv._mermaid_neighbors(E, [], "COMP-lonely", {}, {}) is None


def test_neighbors_returns_none_for_unknown(bv):
    E, R, oe, ie, _ = _make_fixture()
    assert bv._mermaid_neighbors(E, R, "NOPE", oe, ie) is None


def test_neighbors_skips_over_threshold(bv):
    E, R, oe, ie, _ = _make_fixture()
    # BEH-b has 4 neighbors; set threshold below that.
    assert bv._mermaid_neighbors(E, R, "BEH-b", oe, ie, threshold=1) is None


# ---------------------------------------------------------------------------
# _mermaid_realization (kind-dispatched)
# ---------------------------------------------------------------------------

def test_realization_capability_kind(bv):
    """cap <-- realizes <-- components --> contains --> sub-comps."""
    E, R, oe, ie, _ = _make_fixture()
    result = bv._mermaid_realization(E, R, "CAP-P", "capability", oe, ie)
    assert result is not None
    body, refs = result
    assert "COMP-x" in refs        # hop 1
    assert "COMP-y" in refs        # hop 2 via COMP-x contains
    assert "realizes" in body
    assert "contains" in body


def test_realization_component_kind(bv):
    """comp --> realizes --> capabilities <-- contains <-- parent caps."""
    E, R, oe, ie, _ = _make_fixture()
    result = bv._mermaid_realization(E, R, "COMP-x", "component", oe, ie)
    assert result is not None
    _, refs = result
    assert "CAP-P" in refs  # hop 1
    # No parent capability contains CAP-P in this fixture, so hop 2 empty.


def test_realization_behavior_kind(bv):
    """beh <-- traces-to <-- components --> realizes --> capabilities."""
    E, R, oe, ie, _ = _make_fixture()
    result = bv._mermaid_realization(E, R, "BEH-b", "behavior", oe, ie)
    assert result is not None
    _, refs = result
    assert "COMP-y" in refs  # hop 1 traces-to
    # COMP-y does not realize any capability in this fixture; hop 2 empty
    # but hop 1 is nonempty so walker returns a diagram.


def test_realization_interface_kind(bv):
    """if <-- exposes <-- components --> realizes --> capabilities."""
    E, R, oe, ie, _ = _make_fixture()
    result = bv._mermaid_realization(E, R, "IF-i", "interface", oe, ie)
    assert result is not None
    _, refs = result
    assert "COMP-x" in refs
    assert "CAP-P" in refs  # via COMP-x realizes


def test_realization_layer_kind(bv):
    """layer --> contains --> components --> realizes --> capabilities."""
    E, R, oe, ie, _ = _make_fixture()
    result = bv._mermaid_realization(E, R, "LAY-1", "layer", oe, ie)
    assert result is not None
    _, refs = result
    assert "COMP-x" in refs
    assert "CAP-P" in refs


def test_realization_actor_kind(bv):
    """actor --> triggers --> behaviors <-- traces-to <-- components."""
    E, R, oe, ie, _ = _make_fixture()
    result = bv._mermaid_realization(E, R, "ACT-1", "actor", oe, ie)
    assert result is not None
    _, refs = result
    assert "BEH-a" in refs


def test_realization_constraint_kind(bv):
    """constraint <-- constrained-by (1-hop only)."""
    E, R, oe, ie, _ = _make_fixture()
    result = bv._mermaid_realization(E, R, "CONS-1", "constraint", oe, ie)
    assert result is not None
    _, refs = result
    assert "COMP-x" in refs


def test_realization_returns_none_when_hop1_empty(bv):
    E, R, oe, ie, _ = _make_fixture()
    # COMP-y has no realizes edges → hop1 empty for component kind.
    assert bv._mermaid_realization(E, R, "COMP-y", "component", oe, ie) is None


def test_realization_returns_none_for_unknown_id(bv):
    E, R, oe, ie, _ = _make_fixture()
    assert bv._mermaid_realization(E, R, "NOPE", "component", oe, ie) is None


def test_realization_returns_none_for_unknown_kind(bv):
    E, R, oe, ie, _ = _make_fixture()
    assert bv._mermaid_realization(E, R, "COMP-x", "gremlin", oe, ie) is None


# ---------------------------------------------------------------------------
# _mermaid_cross_capability_flow
# ---------------------------------------------------------------------------

def test_cross_capability_flow_renders_for_parent(bv):
    """CAP-P transitively contains BEH-a,BEH-b,BEH-c; triggers chain a->b->c."""
    E, R, *_ = _make_fixture()
    result = bv._mermaid_cross_capability_flow(E, R, "CAP-P")
    assert result is not None
    body, refs = result
    assert body.startswith("flowchart LR")
    # All three behaviors are behaviors_in (transitive).
    assert "BEH-a" in body
    assert "BEH-b" in body
    assert "BEH-c" in body


def test_cross_capability_flow_returns_none_for_unknown(bv):
    E, R, *_ = _make_fixture()
    assert bv._mermaid_cross_capability_flow(E, R, "NOPE") is None


def test_cross_capability_flow_returns_none_when_no_triggers(bv):
    E = _empty_kinds()
    E["capabilities"]["CAP-Z"] = {"id": "CAP-Z", "name": "Z"}
    E["behaviors"]["BEH-z"] = {"id": "BEH-z", "name": "Z"}
    R = [{"from": "CAP-Z", "to": "BEH-z", "type": "contains"}]
    assert bv._mermaid_cross_capability_flow(E, R, "CAP-Z") is None


# ---------------------------------------------------------------------------
# _mermaid_constraint_impact
# ---------------------------------------------------------------------------

def test_constraint_impact_renders(bv):
    E, R, *_ = _make_fixture()
    result = bv._mermaid_constraint_impact(E, R, "CONS-1")
    assert result is not None
    body, refs = result
    assert body.startswith("flowchart LR")
    assert "COMP-x" in refs      # hop 1: constrained-by
    assert "COMP-y" in refs      # hop 2: COMP-x contains COMP-y
    # IF-i is reached via `exposes`, not `contains`, so it is NOT in the
    # component-kind hop2 walk. See test_constraint_impact_only_contains_walked_for_components.


def test_constraint_impact_only_contains_walked_for_components(bv):
    E, R, *_ = _make_fixture()
    _, refs = bv._mermaid_constraint_impact(E, R, "CONS-1")
    # Component hop2 uses outbound contains; IF-i is reached via exposes,
    # so it must NOT be in the impact set.
    assert "IF-i" not in refs


def test_constraint_impact_returns_none_for_unknown(bv):
    E, R, *_ = _make_fixture()
    assert bv._mermaid_constraint_impact(E, R, "NOPE") is None


def test_constraint_impact_returns_none_for_non_constraint(bv):
    E, R, *_ = _make_fixture()
    assert bv._mermaid_constraint_impact(E, R, "COMP-x") is None


def test_constraint_impact_returns_none_when_hop2_empty(bv):
    """Constraint with a single constrained leaf (no downstream) → None."""
    E = _empty_kinds()
    E["constraints"]["CONS-Z"] = {"id": "CONS-Z", "name": "Z"}
    E["behaviors"]["BEH-z"] = {"id": "BEH-z", "name": "Z"}
    R = [{"from": "BEH-z", "to": "CONS-Z", "type": "constrained-by"}]
    # BEH-z has no traces-to inbound → hop2 empty → silent skip.
    assert bv._mermaid_constraint_impact(E, R, "CONS-Z") is None


# ---------------------------------------------------------------------------
# _lint_edge_note_directions
# ---------------------------------------------------------------------------

def test_direction_linter_clean_on_wellformed(bv):
    _, R, *_ = _make_fixture()
    # None of the base-fixture relationships carry notes.
    assert bv._lint_edge_note_directions(R) == []


def test_direction_linter_catches_reversed_realizes(bv):
    R = [
        {"from": "XY-DUMMY-A", "to": "XY-DUMMY-B", "type": "realizes",
         "note": "XY-DUMMY-A is realized by XY-DUMMY-B"},
    ]
    warnings = bv._lint_edge_note_directions(R)
    assert len(warnings) == 1
    w = warnings[0]
    assert w["type"] == "realizes"
    assert w["from"] == "XY-DUMMY-A"
    assert w["to"] == "XY-DUMMY-B"
    assert "reversed" in w["warning"]


def test_direction_linter_ignores_correct_note(bv):
    R = [
        {"from": "COMP-x", "to": "CAP-P", "type": "realizes",
         "note": "COMP-x realizes CAP-P"},
    ]
    assert bv._lint_edge_note_directions(R) == []


# ---------------------------------------------------------------------------
# _realization_skip_reasons
# ---------------------------------------------------------------------------

def test_skip_reasons_clean_on_wellformed(bv):
    E, _, oe, ie, _ = _make_fixture()
    # CAP-P has inbound realizes from COMP-x, COMP-x has outbound → no reasons.
    reasons = bv._realization_skip_reasons(E, oe, ie)
    assert reasons == {}


def test_skip_reasons_flags_outbound_realizes_on_capability(bv):
    E = _empty_kinds()
    E["capabilities"]["CAP-BAD"] = {"id": "CAP-BAD", "name": "Bad"}
    E["components"]["COMP-t"] = {"id": "COMP-t", "name": "T"}
    R = [{"from": "CAP-BAD", "to": "COMP-t", "type": "realizes"}]
    oe = {"CAP-BAD": [("COMP-t", "realizes")]}
    ie = {"COMP-t": [("CAP-BAD", "realizes")]}
    reasons = bv._realization_skip_reasons(E, oe, ie)
    assert "CAP-BAD" in reasons
    assert "outbound realizes" in reasons["CAP-BAD"]


def test_skip_reasons_flags_inbound_realizes_on_component(bv):
    E = _empty_kinds()
    E["capabilities"]["CAP-BAD"] = {"id": "CAP-BAD", "name": "Bad"}
    E["components"]["COMP-t"] = {"id": "COMP-t", "name": "T"}
    R = [{"from": "CAP-BAD", "to": "COMP-t", "type": "realizes"}]
    oe = {"CAP-BAD": [("COMP-t", "realizes")]}
    ie = {"COMP-t": [("CAP-BAD", "realizes")]}
    reasons = bv._realization_skip_reasons(E, oe, ie)
    assert "COMP-t" in reasons
    assert "inbound realizes" in reasons["COMP-t"]


# ---------------------------------------------------------------------------
# _entity_has_compliance_evidence + _constraint_compliance_gaps
# ---------------------------------------------------------------------------

def test_entity_has_compliance_evidence_true(bv):
    rec = {"by_attr": {"verification": [{"status": "verified"}]}}
    assert bv._entity_has_compliance_evidence(rec) is True


def test_entity_has_compliance_evidence_false_unverified(bv):
    rec = {"by_attr": {"verification": [{"status": "asserted"}]}}
    assert bv._entity_has_compliance_evidence(rec) is False


def test_entity_has_compliance_evidence_false_wrong_attr(bv):
    rec = {"by_attr": {"intent": [{"status": "verified"}]}}
    assert bv._entity_has_compliance_evidence(rec) is False


def test_entity_has_compliance_evidence_false_empty(bv):
    assert bv._entity_has_compliance_evidence({}) is False


def test_compliance_gaps_reports_missing_evidence(bv):
    E, R, _, _, records = _make_fixture()
    gaps = bv._constraint_compliance_gaps(E, R, records)
    # COMP-x has no evidence and is directly constrained → gap.
    # COMP-y has evidence and is impacted via contains → NOT a gap.
    gap_ids = {g["entity_id"] for g in gaps}
    assert "COMP-x" in gap_ids
    assert "COMP-y" not in gap_ids
    # All gaps refer to CONS-1.
    for g in gaps:
        assert g["constraint_id"] == "CONS-1"


def test_compliance_gaps_deterministic_order(bv):
    E, R, _, _, records = _make_fixture()
    g1 = bv._constraint_compliance_gaps(E, R, records)
    g2 = bv._constraint_compliance_gaps(E, R, records)
    assert g1 == g2


def test_stamp_compliance_gaps_annotates_records(bv):
    E, R, _, _, records = _make_fixture()
    gaps = bv._constraint_compliance_gaps(E, R, records)
    bv._stamp_compliance_gaps_on_entities(gaps, records)
    # Find COMP-x record and confirm compliance_gaps field appears.
    comp_x = next(r for r in records["components"] if r["id"] == "COMP-x")
    assert comp_x.get("compliance_gaps") == ["CONS-1"]


# ---------------------------------------------------------------------------
# Evidence tiers (L15 refinement).
# ---------------------------------------------------------------------------

def test_promise_tier_runtime_on_test_path(bv):
    assert bv._promise_tier({"provenance": "tests/viewer/test_walks.py cites this"}) == "runtime"


def test_promise_tier_runtime_on_line_ref(bv):
    assert bv._promise_tier({"provenance": "cited in publish.py:107"}) == "runtime"


def test_promise_tier_runtime_on_pytest(bv):
    assert bv._promise_tier({"provenance": "pytest harness covers this"}) == "runtime"


def test_promise_tier_inherited(bv):
    assert bv._promise_tier({"provenance": "SLO inherited from realizes-target COMP-x"}) == "inherited"


def test_promise_tier_design(bv):
    assert bv._promise_tier({"provenance": "Design-only (Part 3 deferred) — compatible-by-construction"}) == "design"


def test_promise_tier_design_case_insensitive(bv):
    assert bv._promise_tier({"provenance": "verified BY CONSTRUCTION"}) == "design"


def test_promise_tier_asserted_default(bv):
    assert bv._promise_tier({"provenance": "2026-09-15 SE walk enrichment"}) == "asserted"


def test_promise_tier_asserted_when_empty(bv):
    assert bv._promise_tier({}) == "asserted"
    assert bv._promise_tier({"provenance": ""}) == "asserted"
    assert bv._promise_tier({"provenance": None}) == "asserted"


def test_promise_tier_runtime_priority_over_design(bv):
    """Runtime tokens outrank design tokens (test citation with hedge)."""
    p = {"provenance": "tests/x.py:5 verifies (design-only fallback)"}
    assert bv._promise_tier(p) == "runtime"


# ---------------------------------------------------------------------------
# _entity_has_compliance_evidence(strong_only=...)
# ---------------------------------------------------------------------------

def test_has_evidence_weak_mode_accepts_asserted(bv):
    rec = {"by_attr": {"verification": [
        {"status": "verified", "provenance": "asserted only"}
    ]}}
    assert bv._entity_has_compliance_evidence(rec) is True
    assert bv._entity_has_compliance_evidence(rec, strong_only=False) is True


def test_has_evidence_strong_mode_rejects_asserted(bv):
    rec = {"by_attr": {"verification": [
        {"status": "verified", "provenance": "SE walk (no citation)"}
    ]}}
    assert bv._entity_has_compliance_evidence(rec, strong_only=True) is False


def test_has_evidence_strong_mode_rejects_design(bv):
    rec = {"by_attr": {"slos": [
        {"status": "verified", "provenance": "design-only Part 3 deferred"}
    ]}}
    assert bv._entity_has_compliance_evidence(rec, strong_only=True) is False


def test_has_evidence_strong_mode_accepts_runtime(bv):
    rec = {"by_attr": {"verification": [
        {"status": "verified", "provenance": "tests/foo/test_bar.py::test_baz"}
    ]}}
    assert bv._entity_has_compliance_evidence(rec, strong_only=True) is True


def test_has_evidence_strong_mode_rejects_inherited(bv):
    """Inherited evidence still delegates — strong mode requires runtime."""
    rec = {"by_attr": {"slos": [
        {"status": "verified", "provenance": "inherited from realizes-target"}
    ]}}
    assert bv._entity_has_compliance_evidence(rec, strong_only=True) is False


# ---------------------------------------------------------------------------
# _evidence_tier_summary
# ---------------------------------------------------------------------------

def test_tier_summary_counts_verified_only(bv):
    records = {
        "components": [{
            "id": "COMP-mix", "kind": "component", "name": "Mix",
            "by_attr": {
                "verification": [
                    {"status": "verified", "provenance": "tests/x.py"},
                    {"status": "verified", "provenance": "design-only"},
                    {"status": "asserted", "provenance": "tests/y.py"},  # ignored
                ],
                "slos": [
                    {"status": "verified", "provenance": "inherited from CAP-P"},
                ],
                "intent": [  # not a compliance attr → ignored
                    {"status": "verified", "provenance": "tests/z.py"},
                ],
            },
        }],
    }
    summary = bv._evidence_tier_summary(records)
    assert summary == {"COMP-mix": {"design": 1, "inherited": 1, "runtime": 1}}


def test_tier_summary_omits_entities_without_evidence(bv):
    records = {
        "components": [
            {"id": "COMP-empty", "kind": "component", "name": "E", "by_attr": {}},
            {"id": "COMP-full", "kind": "component", "name": "F", "by_attr": {
                "verification": [{"status": "verified", "provenance": "tests/a.py"}]
            }},
        ]
    }
    summary = bv._evidence_tier_summary(records)
    assert "COMP-empty" not in summary
    assert summary["COMP-full"] == {"runtime": 1}


def test_tier_summary_deterministic(bv):
    _, _, _, _, records = _make_fixture()
    assert bv._evidence_tier_summary(records) == bv._evidence_tier_summary(records)


# ---------------------------------------------------------------------------
# _constraint_compliance_gaps(strong_only=...)
# ---------------------------------------------------------------------------

def test_gaps_strong_mode_flags_design_only_evidence(bv):
    E, R, _, _, records = _make_fixture()
    # Upgrade COMP-y's evidence to design-only (weak).
    comp_y = next(r for r in records["components"] if r["id"] == "COMP-y")
    comp_y["by_attr"]["verification"] = [
        {"status": "verified", "provenance": "design-only Part 3 deferred"}
    ]
    # Weak mode: COMP-y still passes.
    weak = bv._constraint_compliance_gaps(E, R, records, strong_only=False)
    assert "COMP-y" not in {g["entity_id"] for g in weak}
    # Strong mode: COMP-y now flagged.
    strong = bv._constraint_compliance_gaps(E, R, records, strong_only=True)
    strong_ids = {g["entity_id"] for g in strong}
    assert "COMP-y" in strong_ids
    assert "COMP-x" in strong_ids  # still gap in both modes
    # Reason string carries the strong-mode hint.
    strong_y = next(g for g in strong if g["entity_id"] == "COMP-y")
    assert "runtime-tier" in strong_y["reason"]


def test_gaps_strong_mode_accepts_runtime_evidence(bv):
    E, R, _, _, records = _make_fixture()
    # Give COMP-x a runtime-tier promise.
    comp_x = next(r for r in records["components"] if r["id"] == "COMP-x")
    comp_x["by_attr"]["verification"] = [
        {"status": "verified", "provenance": "tests/pipeline_v3/test_x.py::test_it"}
    ]
    strong = bv._constraint_compliance_gaps(E, R, records, strong_only=True)
    assert "COMP-x" not in {g["entity_id"] for g in strong}


def test_gaps_default_matches_weak_mode(bv):
    """strong_only default is False → identical to explicit False."""
    E, R, _, _, records = _make_fixture()
    a = bv._constraint_compliance_gaps(E, R, records)
    b = bv._constraint_compliance_gaps(E, R, records, strong_only=False)
    assert a == b


# ---------------------------------------------------------------------------
# Determinism (byte-equal on repeated invocation).
# ---------------------------------------------------------------------------

def test_walks_deterministic(bv):
    E, R, oe, ie, records = _make_fixture()
    calls = [
        lambda: bv._mermaid_pipeline(E, R, "CAP-P"),
        lambda: bv._mermaid_decomposition(E, R, "CAP-P"),
        lambda: bv._mermaid_neighbors(E, R, "BEH-b", oe, ie),
        lambda: bv._mermaid_realization(E, R, "CAP-P", "capability", oe, ie),
        lambda: bv._mermaid_cross_capability_flow(E, R, "CAP-P"),
        lambda: bv._mermaid_constraint_impact(E, R, "CONS-1"),
        lambda: bv._constraint_compliance_gaps(E, R, records),
    ]
    for c in calls:
        assert c() == c()
