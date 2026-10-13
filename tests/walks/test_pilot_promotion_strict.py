"""Pilot test: WALK-promotion-strict — strict Category B promotion audit.

Complementary to test_pilot_promotion.py: where the loose WALK-promotion
buckets by promise STATUS, this walk buckets by ATTRIBUTE COVERAGE across
the Category B specification set (goals, requirements, success_criteria,
failure_modes, constraints). Enabled by the L22 `promise_attribute_count`
DSL atom (Part 9).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from architecture_model.walks.runner import run_walk
from architecture_model.walks.spec.loader import load_walk_spec

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO / ".architecture/model/walks/promotion-strict.v3.yaml"
MODEL_PATH = REPO / ".architecture/model/capabilities.v3.yaml"

CATEGORY_B = ("goals", "requirements", "success_criteria", "failure_modes", "constraints")


@pytest.fixture(scope="module")
def real_model() -> dict:
    with MODEL_PATH.open() as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def spec():
    return load_walk_spec(SPEC_PATH)


# ---------- spec parses correctly ------------------------------------------


def test_spec_id_and_audits(spec):
    assert spec.id == "WALK-promotion-strict"
    assert spec.audits == ("CAP-WK.promotion-strict",)


def test_scope_is_any_kind(spec):
    assert spec.scope.kind == "any"


def test_classify_uses_promise_attribute_atoms(spec):
    predicates = " ".join(v.when for v in spec.classify.verdicts)
    for attr in CATEGORY_B:
        assert f"promise_attribute_count:{attr}" in predicates, (
            f"expected Category B attr {attr!r} referenced in classify predicates"
        )


def test_rollup_is_worst_child_via_contains(spec):
    assert spec.rollup is not None
    assert spec.rollup.via == "contains"
    assert spec.rollup.strategy == "worst-child"


def test_fallback_is_insufficient_strict(spec):
    assert spec.classify.on_missing_attributes == "insufficient-strict"


# ---------- synthetic bucketing --------------------------------------------


def _entity(id: str, promises: list[dict]) -> dict:
    return {"id": id, "name": id, "promises": promises}


def _p(attribute: str, status: str = "verified") -> dict:
    return {"id": f"PR-{attribute}-{status}", "attribute": attribute, "status": status}


def test_bare_entity_is_insufficient_strict(spec):
    model = {"entities": {"capabilities": [_entity("CAP-empty", [])]}, "relationships": []}
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-empty"]["verdict"] == "insufficient-strict"


def test_all_five_category_b_attrs_ready_strict(spec):
    """All 5 Category B attrs present → ready-to-code-strict."""
    model = {
        "entities": {
            "capabilities": [_entity("CAP-full", [_p(a) for a in CATEGORY_B])]
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-full"]["verdict"] == "ready-to-code-strict"


def test_missing_one_category_b_attr_degrades_to_partial(spec):
    """4 of 5 → partial-strict (not ready-strict)."""
    model = {
        "entities": {
            "capabilities": [
                _entity(
                    "CAP-partial",
                    # constraints intentionally omitted
                    [_p(a) for a in CATEGORY_B if a != "constraints"],
                )
            ]
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-partial"]["verdict"] == "partial-strict"


def test_single_category_b_attr_is_partial(spec):
    """1 of 5 → partial-strict."""
    model = {
        "entities": {"capabilities": [_entity("CAP-one", [_p("goals")])]},
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-one"]["verdict"] == "partial-strict"


def test_non_category_b_attrs_do_not_count(spec):
    """Category A attrs (intent, rationale) do not satisfy the strict gate."""
    model = {
        "entities": {
            "capabilities": [
                _entity(
                    "CAP-cat-a",
                    [_p("intent"), _p("rationale"), _p("assumptions")],
                )
            ]
        },
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c for c in out["cards"]}
    assert cards["CAP-cat-a"]["verdict"] == "insufficient-strict"


def test_status_does_not_affect_strict_verdict(spec):
    """The strict gate ignores status — it only counts attribute coverage."""
    proposed_all = _entity("CAP-proposed", [_p(a, "proposed") for a in CATEGORY_B])
    open_all = _entity("CAP-open", [_p(a, "open") for a in CATEGORY_B])
    model = {
        "entities": {"capabilities": [proposed_all, open_all]},
        "relationships": [],
    }
    out = run_walk(spec, model)
    cards = {c["entity_id"]: c["verdict"] for c in out["cards"]}
    assert cards["CAP-proposed"] == "ready-to-code-strict"
    assert cards["CAP-open"] == "ready-to-code-strict"


# ---------- integration against real repo model ----------------------------


def test_real_model_produces_cards(spec, real_model):
    out = run_walk(spec, real_model)
    assert out["walk_id"] == "WALK-promotion-strict"
    assert len(out["cards"]) > 0


def test_real_model_verdicts_are_known(spec, real_model):
    out = run_walk(spec, real_model)
    known = {"ready-to-code-strict", "partial-strict", "insufficient-strict"}
    for card in out["cards"]:
        assert card["verdict"] in known, (
            f"unexpected verdict {card['verdict']!r} on {card['entity_id']!r}"
        )


def test_real_model_ready_to_code_strict_covers_all_category_b(spec, real_model):
    """Any entity flagged ready-to-code-strict must have all 5 Category B attrs."""
    out = run_walk(spec, real_model)
    for card in out["cards"]:
        if card["verdict"] != "ready-to-code-strict":
            continue
        promises = card["entity"].get("promises") or []
        attrs_present = {
            p.get("attribute") for p in promises if isinstance(p, dict)
        }
        missing = set(CATEGORY_B) - attrs_present
        assert not missing, (
            f"{card['entity_id']} tagged ready-to-code-strict but missing "
            f"Category B attrs: {missing}"
        )


def test_real_model_signals_specification_gap(spec, real_model):
    """The strict gate should surface a meaningful specification gap on the real model.

    Snapshot the aggregate distribution: at time of Part 9, no entity has
    all 5 Category B attrs, so ready-to-code-strict == 0 and the majority
    is insufficient-strict. This test guards against a future silent
    regression to loose semantics; it does NOT pin an exact count (the
    model evolves).
    """
    out = run_walk(spec, real_model)
    from collections import Counter
    verdicts = Counter(c["verdict"] for c in out["cards"])
    # The strict gate must be strictly harder than the loose gate: on the
    # real repo, at least one entity is bucketed as insufficient-strict.
    assert verdicts["insufficient-strict"] >= 1, (
        f"expected at least one insufficient-strict entity on real model, got {verdicts}"
    )
