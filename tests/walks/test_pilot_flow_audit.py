"""Pilot test: WALK-flow-audit declarative meta-walk (Part 17b).

Asserts the flow-audit WalkSpec correctly buckets behaviors by their
`triggers` edge topology:

  - Composite orchestrator (>=3 outbound triggers) → ready-to-code.
    Threshold matches containerize's COMPOSITE_MIN_TRIGGERS=3 constant
    from Part 17a3.
  - Linked participant (1-2 outbound OR >=1 inbound) → ready-to-code.
  - Isolated (no triggers either direction) → needs-enrichment.

Uses a synthetic v3 model (behaviors + trigger relationships only) so
we exercise the classify DSL atoms outbound_count:triggers and
inbound_count:triggers directly. A second test loads the WalkSpec YAML
via load_walk_spec to guarantee it parses under the substrate loader
and declares the correct audit target.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.walks.runner import run_walk
from architecture_model.walks.spec.loader import load_walk_spec

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / ".architecture/model/walks/flow-audit.v3.yaml"


@pytest.fixture(scope="module")
def spec():
    return load_walk_spec(SPEC_PATH)


def _behavior(bid: str, name: str) -> dict:
    return {"id": bid, "name": name, "promises": []}


def _trig(src: str, dst: str) -> dict:
    return {"from": src, "to": dst, "type": "triggers"}


# ---------------------------------------------------------------------------
# Spec loads and declares correct audit target
# ---------------------------------------------------------------------------


def test_spec_loads_and_declares_correct_audit(spec):
    assert spec.id == "WALK-flow-audit"
    assert spec.audits == ("CAP-WK.flow-audit",)
    assert spec.scope.kind == "behavior"
    assert "triggers" in spec.traverse.edges
    assert spec.traverse.direction == "both"
    assert spec.traverse.depth == 1


# ---------------------------------------------------------------------------
# Classification: composite / linked / isolated
# ---------------------------------------------------------------------------


def test_composite_orchestrator_classified_ready(spec):
    # BEH-ORCH has 3 outbound triggers — meets composite threshold.
    model = {
        "entities": {
            "behaviors": [
                _behavior("BEH-ORCH", "orch"),
                _behavior("BEH-A", "step_a"),
                _behavior("BEH-B", "step_b"),
                _behavior("BEH-C", "step_c"),
            ],
        },
        "relationships": [
            _trig("BEH-ORCH", "BEH-A"),
            _trig("BEH-ORCH", "BEH-B"),
            _trig("BEH-ORCH", "BEH-C"),
        ],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["BEH-ORCH"]["verdict"] == "ready-to-code"


def test_linked_participant_with_only_inbound_is_ready(spec):
    # BEH-A has zero outbound but one inbound (from BEH-ORCH).
    # Downstream targets are legitimate flow participants.
    model = {
        "entities": {
            "behaviors": [
                _behavior("BEH-ORCH", "orch"),
                _behavior("BEH-A", "step_a"),
            ],
        },
        "relationships": [_trig("BEH-ORCH", "BEH-A")],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["BEH-A"]["verdict"] == "ready-to-code"


def test_linked_participant_with_one_outbound_is_ready(spec):
    # Below composite threshold (1 outbound) but still linked — ready.
    model = {
        "entities": {
            "behaviors": [
                _behavior("BEH-CALLER", "caller"),
                _behavior("BEH-CALLEE", "callee"),
            ],
        },
        "relationships": [_trig("BEH-CALLER", "BEH-CALLEE")],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["BEH-CALLER"]["verdict"] == "ready-to-code"


def test_isolated_behavior_classified_needs_enrichment(spec):
    # BEH-LONE has zero triggers in either direction — surfaces as gap.
    model = {
        "entities": {
            "behaviors": [
                _behavior("BEH-LONE", "lone"),
                # Include a linked pair to prove only the lone one flags.
                _behavior("BEH-X", "x"),
                _behavior("BEH-Y", "y"),
            ],
        },
        "relationships": [_trig("BEH-X", "BEH-Y")],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["BEH-LONE"]["verdict"] == "needs-enrichment"
    assert cards["BEH-X"]["verdict"] == "ready-to-code"
    assert cards["BEH-Y"]["verdict"] == "ready-to-code"


# ---------------------------------------------------------------------------
# Coverage: walk visits every behavior in the scoped model
# ---------------------------------------------------------------------------


def test_walk_visits_every_behavior(spec):
    model = {
        "entities": {
            "behaviors": [
                _behavior("BEH-1", "one"),
                _behavior("BEH-2", "two"),
                _behavior("BEH-3", "three"),
            ],
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    walked = {c["entity_id"] for c in out["cards"]}
    assert walked == {"BEH-1", "BEH-2", "BEH-3"}


def test_walk_ignores_non_behavior_entities(spec):
    # Components + capabilities in the model must be filtered out by scope.
    model = {
        "entities": {
            "behaviors": [_behavior("BEH-1", "one")],
            "components": [{"id": "COMP-A", "name": "a"}],
            "capabilities": [{"id": "CAP-A", "name": "a"}],
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    walked = {c["entity_id"] for c in out["cards"]}
    assert walked == {"BEH-1"}
