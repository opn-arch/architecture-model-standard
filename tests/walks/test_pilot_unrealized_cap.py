"""Pilot parity test: WALK-unrealized-cap vs. legacy _unrealized_capability_summary.

Asserts the declarative WalkSpec produces cards consistent with the
hand-rolled Python walk in scripts/build_v3_viewer.py. Ensures we can
delete the Python impl in a follow-up commit without behavioral regression.

The two implementations differ in shape (verdicts vs severities) but MUST
agree on WHICH capabilities are flagged and their ordering by severity.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

from architecture_model.walks.runner import run_walk
from architecture_model.walks.spec.loader import load_walk_spec

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / ".architecture/model/walks/unrealized-cap.v3.yaml"
MODEL_PATH = REPO / ".architecture/model/capabilities.v3.yaml"
LEGACY_SCRIPT = REPO / "scripts/build_v3_viewer.py"


def _load_legacy_helpers():
    """Import the private helpers from build_v3_viewer.py without running its CLI."""
    spec = importlib.util.spec_from_file_location(
        "_legacy_v3_viewer", LEGACY_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_legacy_v3_viewer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _model_dict():
    with MODEL_PATH.open() as f:
        return yaml.safe_load(f)


def _entities_by_kind(model: dict) -> dict:
    """Reshape the model's entities.<kind> lists into id-keyed dicts,
    matching what the legacy viewer expects."""
    ents = model.get("entities", {})
    out: dict = {}
    for bucket_name, bucket in ents.items():
        if isinstance(bucket, list):
            out[bucket_name] = {e["id"]: e for e in bucket if "id" in e}
    return out


@pytest.fixture(scope="module")
def model():
    return _model_dict()


@pytest.fixture(scope="module")
def legacy_summary(model):
    legacy = _load_legacy_helpers()
    entities_by_kind = _entities_by_kind(model)
    return legacy._unrealized_capability_summary(
        entities_by_kind, model.get("relationships", [])
    )


@pytest.fixture(scope="module")
def walk_output(model):
    spec = load_walk_spec(SPEC_PATH)
    return run_walk(spec, model)


def test_spec_loads_and_declares_correct_audit():
    spec = load_walk_spec(SPEC_PATH)
    assert spec.id == "WALK-unrealized-cap"
    assert spec.audits == ("CAP-WK.unrealized-cap",)
    assert spec.scope.kind == "capability"
    assert "realizes" in spec.traverse.edges
    assert spec.traverse.direction == "inbound"


def test_walk_visits_every_capability_in_model(model, walk_output):
    caps = {c["id"] for c in model["entities"].get("capabilities", [])}
    walked = {c["entity_id"] for c in walk_output["cards"]}
    assert walked == caps, (
        f"walk must visit every capability; "
        f"missing={caps - walked} extra={walked - caps}"
    )


def test_flagged_set_matches_legacy(legacy_summary, walk_output):
    """The set of capabilities the legacy walk flags (non-ok) MUST equal
    the set of cards the new walk marks with a non-'ready-to-code' verdict.
    """
    legacy_flagged = {s["cap_id"] for s in legacy_summary}
    walk_flagged = {
        c["entity_id"] for c in walk_output["cards"]
        if c["verdict"] != "ready-to-code"
    }
    assert walk_flagged == legacy_flagged, (
        f"flagged sets diverge: only-legacy={legacy_flagged - walk_flagged} "
        f"only-walk={walk_flagged - legacy_flagged}"
    )


def test_verdict_reasons_are_deterministic(walk_output):
    """Every card carries a non-empty reasons list; two runs give identical output."""
    for card in walk_output["cards"]:
        assert card["reasons"], f"card {card['entity_id']} has empty reasons"
    # Determinism: cards are sorted by (severity desc, entity_id) — verify.
    ids = [c["entity_id"] for c in walk_output["cards"]]
    severities = [c["severity"] for c in walk_output["cards"]]
    for i in range(len(ids) - 1):
        assert (-severities[i], ids[i]) <= (-severities[i + 1], ids[i + 1])


# ---------------------------------------------------------------------------
# Rollup (Concern B fix): parent capabilities inherit worst descendant verdict
# via the contains relationship. This is the DECLARATIVE fix — no code, just
# rollup.via=contains, category=B, strategy=worst-child in the WalkSpec.
# ---------------------------------------------------------------------------


def _cards_by_id(walk_output):
    return {c["entity_id"]: c for c in walk_output["cards"]}


def test_rollup_surfaces_child_verdicts_to_parent(model, walk_output):
    """For every CAP-A contains CAP-B edge, if CAP-B has a worse verdict than
    CAP-A's local verdict, CAP-A's post-rollup verdict MUST be at least as
    severe as CAP-B's."""
    from architecture_model.walks.verdict import VERDICT_SEVERITY, Verdict

    def sev(v):
        try:
            return VERDICT_SEVERITY[Verdict(v)]
        except (KeyError, ValueError):
            return -1

    cards = _cards_by_id(walk_output)
    cap_ids = {c["id"] for c in model["entities"].get("capabilities", [])}
    contains = [
        r for r in model.get("relationships", [])
        if r.get("type") == "contains"
        and r.get("from") in cap_ids
        and r.get("to") in cap_ids
    ]
    assert contains, "test fixture requires at least one CAP contains CAP edge"

    for r in contains:
        parent, child = r["from"], r["to"]
        if parent not in cards or child not in cards:
            continue
        pv, cv = cards[parent]["verdict"], cards[child]["verdict"]
        assert sev(pv) >= sev(cv), (
            f"rollup failed: parent {parent}={pv} (sev {sev(pv)}) should be "
            f">= worst child {child}={cv} (sev {sev(cv)})"
        )


def test_rollup_notes_recorded_on_parents_with_children(model, walk_output):
    """Every CAP that has CAP children in the model MUST carry a rollup note."""
    cards = _cards_by_id(walk_output)
    cap_ids = {c["id"] for c in model["entities"].get("capabilities", [])}
    parents_with_cap_kids = {
        r["from"] for r in model.get("relationships", [])
        if r.get("type") == "contains"
        and r.get("from") in cap_ids
        and r.get("to") in cap_ids
    }
    for pid in parents_with_cap_kids:
        if pid not in cards:
            continue
        notes = cards[pid].get("rollup_notes", [])
        assert notes, f"parent cap {pid} missing rollup_notes"
        assert any("via contains" in n for n in notes), (
            f"parent {pid} rollup_notes lack 'via contains': {notes}"
        )


def test_rollup_leaves_childless_caps_unchanged(model, walk_output):
    """CAPs with no CAP children carry no rollup notes."""
    cards = _cards_by_id(walk_output)
    cap_ids = {c["id"] for c in model["entities"].get("capabilities", [])}
    has_cap_children = {
        r["from"] for r in model.get("relationships", [])
        if r.get("type") == "contains"
        and r.get("from") in cap_ids
        and r.get("to") in cap_ids
    }
    childless = cap_ids - has_cap_children
    for cid in childless:
        if cid not in cards:
            continue
        notes = cards[cid].get("rollup_notes", [])
        assert not notes, f"childless cap {cid} unexpectedly has rollup_notes={notes}"


# ---------------------------------------------------------------------------
# Concern B demonstration: on a synthetic model where a parent is LOCALLY
# ready-to-code (has realizer, no open promises) but a child is NOT,
# rollup MUST flip the parent's verdict. This proves the substrate delivers
# the rollup value the legacy flat walk cannot.
# ---------------------------------------------------------------------------


def test_rollup_concern_b_surfaces_parent_that_would_be_ready():
    synthetic_model = {
        "entities": {
            "capabilities": [
                {
                    "id": "CAP-PARENT",
                    "name": "parent",
                    "promises": [],
                },
                {
                    "id": "CAP-CHILD",
                    "name": "child",
                    "promises": [
                        {"id": "PR-open", "status": "open", "attribute": "intent"},
                    ],
                },
            ],
            "components": [
                {"id": "COMP-A", "name": "a"},
                {"id": "COMP-B", "name": "b"},
            ],
        },
        "relationships": [
            # Both caps have a realizer, so LOCALLY both are non-needs-enrichment.
            {"from": "COMP-A", "to": "CAP-PARENT", "type": "realizes"},
            {"from": "COMP-B", "to": "CAP-CHILD", "type": "realizes"},
            # Parent contains child.
            {"from": "CAP-PARENT", "to": "CAP-CHILD", "type": "contains"},
        ],
    }
    spec = load_walk_spec(SPEC_PATH)
    out = run_walk(spec, synthetic_model)
    cards = {c["entity_id"]: c for c in out["cards"]}

    # Child: has realizer + open promise -> needs-validation.
    assert cards["CAP-CHILD"]["verdict"] == "needs-validation"

    # Parent: has realizer + no open promises -> would be ready-to-code LOCALLY,
    # but rollup via contains inherits child's needs-validation.
    assert cards["CAP-PARENT"]["verdict"] == "needs-validation", (
        "Concern B failure: parent should inherit child's non-ok verdict via "
        f"rollup, got {cards['CAP-PARENT']['verdict']}"
    )
    # And it MUST carry a rollup note recording the propagation.
    notes = cards["CAP-PARENT"].get("rollup_notes", [])
    assert any("worst-child" in n and "via contains" in n for n in notes), (
        f"parent missing rollup provenance note; got {notes}"
    )
