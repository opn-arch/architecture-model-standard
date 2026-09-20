"""Pilot test: WALK-promotion — ceremony readiness meta-walk.

Verifies the declarative WalkSpec parses, runs, and produces sensible
buckets on both synthetic entities and the real repo model. Purely a
WalkSpec (no legacy hand-rolled counterpart) — exercises the classify
DSL's promise_status_count atoms to identify Category B -> C promotion
candidates for the Q6=c ceremony.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from architecture_model.walks.runner import run_walk
from architecture_model.walks.spec.loader import load_walk_spec

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / ".architecture/model/walks/promotion.v3.yaml"
MODEL_PATH = REPO / ".architecture/model/capabilities.v3.yaml"


@pytest.fixture(scope="module")
def real_model() -> dict:
    with MODEL_PATH.open() as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def spec():
    return load_walk_spec(SPEC_PATH)


# ---------- spec parses correctly ------------------------------------------


def test_spec_id_and_audits(spec):
    assert spec.id == "WALK-promotion"
    assert spec.audits == ("CAP-WK.promotion",)


def test_scope_is_any_kind(spec):
    assert spec.scope.kind == "any"


def test_classify_uses_promise_status_atoms(spec):
    predicates = " ".join(v.when for v in spec.classify.verdicts)
    assert "promise_status_count:proposed" in predicates
    assert "promise_status_count:verified" in predicates
    assert "promise_status_count:open" in predicates


def test_rollup_is_worst_child_via_contains(spec):
    assert spec.rollup is not None
    assert spec.rollup.via == "contains"
    assert spec.rollup.strategy == "worst-child"


# ---------- synthetic bucketing --------------------------------------------


def _entity(id: str, promises: list[dict]) -> dict:
    return {"id": id, "name": id, "promises": promises}


def _promise(status: str, attribute: str = "intent") -> dict:
    return {"id": f"PR-{status}-{attribute}", "attribute": attribute, "status": status}


def test_bare_entity_needs_enrichment(spec):
    model = {
        "entities": {"capabilities": [_entity("CAP-empty", [])]},
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-empty"]["verdict"] == "needs-enrichment"


def test_all_verified_ready_to_code(spec):
    model = {
        "entities": {
            "capabilities": [
                _entity("CAP-done", [_promise("verified"), _promise("verified", "goals")])
            ]
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-done"]["verdict"] == "ready-to-code"


def test_proposed_only_is_promotion_candidate(spec):
    """Clean promotion case: proposed promises, no open gaps."""
    model = {
        "entities": {
            "capabilities": [
                _entity(
                    "CAP-pending",
                    [_promise("proposed", "goals"), _promise("proposed", "requirements")],
                )
            ]
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-pending"]["verdict"] == "promotion-candidate"


def test_proposed_plus_verified_baseline_still_candidate(spec):
    """Mixed proposed+verified (no open) still ceremony-eligible."""
    model = {
        "entities": {
            "capabilities": [
                _entity(
                    "CAP-mixed",
                    [_promise("verified"), _promise("proposed", "goals")],
                )
            ]
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-mixed"]["verdict"] == "promotion-candidate"


def test_open_gap_blocks_promotion(spec):
    """Open gaps must be validated before promotion runs."""
    model = {
        "entities": {
            "capabilities": [
                _entity(
                    "CAP-blocked",
                    [_promise("open", "goals"), _promise("proposed", "requirements")],
                )
            ]
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-blocked"]["verdict"] == "needs-validation"


# ---------- integration against real repo model ----------------------------


def test_real_model_produces_cards(spec, real_model):
    out = run_walk(spec, real_model)
    assert out["walk_id"] == "WALK-promotion"
    assert len(out["cards"]) > 0


def test_real_model_verdicts_are_known(spec, real_model):
    out = run_walk(spec, real_model)
    known = {"ready-to-code", "promotion-candidate", "needs-validation", "needs-enrichment"}
    for card in out["cards"]:
        assert card["verdict"] in known, (
            f"unexpected verdict {card['verdict']!r} on {card['entity_id']!r}"
        )


def test_real_model_flags_at_least_one_candidate(spec, real_model):
    """The real model should surface actionable promotion work."""
    out = run_walk(spec, real_model)
    candidates = [c for c in out["cards"] if c["verdict"] == "promotion-candidate"]
    assert len(candidates) >= 1, "expected at least one promotion candidate on real model"


def test_real_model_ready_to_code_have_only_verified(spec, real_model):
    """Any entity flagged ready-to-code must have all promises verified."""
    out = run_walk(spec, real_model)
    for card in out["cards"]:
        if card["verdict"] != "ready-to-code":
            continue
        promises = card["entity"].get("promises") or []
        statuses = {p.get("status") for p in promises}
        assert statuses == {"verified"}, (
            f"{card['entity_id']} tagged ready-to-code but has statuses={statuses}"
        )
